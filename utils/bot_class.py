import asyncio
import collections
import datetime
import re
from multiprocessing.context import Process
from multiprocessing.queues import Queue
from typing import Optional, List
import concurrent.futures
import aiohttp
import discord
from discord.ext.commands.bot import AutoShardedBot
from discord.ext import commands
import statcord
from utils import config as config, news
from utils.ctx_class import MyContext
from utils.custom_updaters import CustomUpdater
from utils.logger import FakeLogger
from utils.models import get_from_db
from utils import api as covid19api
from utils.maps import MapGetter
from utils.async_helpers import wrap_in_async
from copy import deepcopy
try:
    from blackfire import probe
except (ImportError, ModuleNotFoundError):
    blackfire = False
else:
    blackfire = True


_runtime_error = RuntimeError("The bot hasn't been set up yet! Ensure bot.async_setup is called ASAP!")


class BotStats:
    def __init__(self):
        self.total_members: int = 0
        self.total_guilds: int = 0
        self.days_since_creation: int = 0


class MyBot(AutoShardedBot):
    def __init__(self, *args, **kwargs):
        self.logger = FakeLogger()
        self.config: dict = {}
        self.reload_config()
        activity = discord.Game(self.config["bot"]["playing"])
        super().__init__(*args,
                         command_prefix=get_prefix,
                         activity=activity,
                         case_insensitive=self.config["bot"]["commands_are_case_insensitive"],
                         **kwargs)
        self.commands_used = collections.Counter()
        self.uptime = datetime.datetime.utcnow()
        self.shards_ready = set()
        self._worldometers_api = covid19api.Covid19StatsWorldometers()
        self._vaccine_api = covid19api.VaccineStats()
        self._jhucsse_api = covid19api.Covid19JHUCSSEStats()
        self.news_api = news.NewsAPI(self.config["auth"]["news_api"]["token"])
        self._owid_api = covid19api.OWIDData()
        self.custom_updater_helper: Optional[CustomUpdater] = None
        self._client_session: Optional[aiohttp.ClientSession] = None
        self.basic_process_pool = concurrent.futures.ProcessPoolExecutor(2)
        self.premium_process_pool = concurrent.futures.ProcessPoolExecutor(4)
        self.statcord: Optional[statcord.Client] = None
        self.maps_api: Optional[MapGetter] = None
        self.support_server_invite = "https://discord.gg/myJh5hkjpS"
        self.autoupdater_dump: asyncio.Queue = asyncio.Queue(maxsize=1)
        self.blackfire: bool = blackfire
        self.sync_queue: Optional[Queue] = None
        self.task_processors: Optional[List[Process]] = None
        asyncio.ensure_future(self.async_setup())

    @property
    def client_session(self):
        if self._client_session:
            return self._client_session
        else:
            raise _runtime_error

    @property
    def worldometers_api(self):
        if self._worldometers_api.data_is_valid:
            return self._worldometers_api
        else:
            raise _runtime_error

    @property
    def vaccine_api(self):
        if self._vaccine_api.data_is_valid:
            return self._vaccine_api
        else:
            raise _runtime_error

    @property
    def jhucsse_api(self):
        if self._jhucsse_api.data_is_valid:
            return self._jhucsse_api
        else:
            raise _runtime_error

    @property
    def owid_api(self):
        if self._owid_api.data_is_valid:
            return self._owid_api
        else:
            raise _runtime_error

    def reload_config(self):
        self.config = config.load_config()

    async def async_setup(self):
        """
        This funtcion is run once, and is used to setup the bot async features, like the ClientSession from aiohttp.
        """
        if self._client_session is None:
            self._client_session = aiohttp.ClientSession()  # There is no need to call __aenter__, since that does
            # nothing in this case
        try:
            await self._worldometers_api.update_covid_19_virus_stats()
            await self._vaccine_api.update_covid_19_vaccine_stats()
            await self._jhucsse_api.update_covid_19_virus_stats()
            await self._owid_api.update_covid_19_owid_data()
        except RuntimeError as e:
            self.logger.exception("Fatal RuntimeError while running initial update!", exc_info=e)
        except Exception as e:
            self.logger.exception("Fatal general error while running initial update!", exc_info=e)
        try:
            if not self.maps_api:
                self.maps_api = MapGetter("/home/pi/covid_bot_beta/maps")
                await wrap_in_async(self.maps_api.initalize_firefox, thread_pool=True)
        except Exception as e:
            self.logger.exception("Fatal error while initializing Firefox!", exc_info=e)
        try:
            self.custom_updater_helper = CustomUpdater(self)
            await self.custom_updater_helper.setup()
        except Exception as e:
            self.logger.exception("Fatal error while initializing the custom updater!", exc_info=e)

    async def on_message(self, message: discord.Message):
        if not self.is_ready():
            return  # Ignoring messages when not ready

        if message.author.bot:
            return  # ignore messages from other bots

        ctx: MyContext = await self.get_context(message, cls=MyContext)
        if self.user.mentioned_in(message) and ctx.prefix is None and str(self.user.id) in message.content:
            _ = await ctx.get_translate_function()
            await ctx.send(_("Hi there! I'm a bot for giving live stats on the COVID-19 pandemic. My default prefix is "
                             "`c!`. This can be changed with `c!settings prefix <new prefix>`, replacing <new prefix> "
                             "with the prefix you want. For a list of my commands, run `c!help`."))
        elif ctx.valid:
            try:
                async with ctx.typing():
                    await self.invoke(ctx)
            except discord.Forbidden:
                await self.invoke(ctx)

    async def on_command(self, ctx: MyContext):
        if self.blackfire:
            probe.add_marker(f"Command {ctx.command} {ctx.invoked_subcommand}")
        self.commands_used[ctx.command.name] += 1
        self.statcord.command_run(ctx)
        ctx.logger.info(f"{ctx.message.clean_content}")

    async def on_shard_ready(self, shard_id):
        self.shards_ready.add(shard_id)

    async def on_disconnect(self):
        self.shards_ready = set()

    async def on_ready(self):
        messages = ["-----------", f"The bot is ready.", f"Logged in as {self.user.name} ({self.user.id})."]
        total_members = len(self.users)
        messages.append(f"I see {len(self.guilds)} guilds, and {total_members} members.")
        messages.append(f"To invite your bot to your server, use the following link: "
                        f"https://discord.com/api/oauth2/authorize?client_id={self.user.id}&scope=bot&permissions=0")
        cogs_count = len(self.cogs)
        messages.append(f"{cogs_count} cogs are loaded")
        messages.append("-----------")
        for message in messages:
            self.logger.info(message)

        for message in messages:
            print(message)


async def get_prefix(bot: MyBot, message: discord.Message):
    forced_prefixes = deepcopy(bot.config["bot"]["prefixes"])

    if not message.guild:
        # Need no prefix when in DMs
        return commands.when_mentioned_or(*forced_prefixes, "")(bot, message)
    else:
        if bot.config["database"]["enable"]:
            db_guild = await get_from_db(message.guild)
            guild_prefix = db_guild.prefix
            if guild_prefix:
                forced_prefixes.append(guild_prefix)

        return commands.when_mentioned_or(*forced_prefixes)(bot, message)
