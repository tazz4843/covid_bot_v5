# coding=utf-8
import discord
from discord.ext import commands
import time
from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import get_from_db
import json
import datetime


class UtilsCommands(Cog):
    @commands.command(name="credits", aliases=["info"])
    async def credits(self, ctx: MyContext):
        """
        A simple credits screen
        """
        credits_embed = discord.Embed(color=discord.Color.dark_green(), title="Credits")
        symphonic: discord.User = await self.bot.fetch_user(263128260009787392)
        zeroslashzero: discord.User = await self.bot.fetch_user(661660243033456652)
        eyes: discord.User = await self.bot.fetch_user(138751484517941259)
        stalin: discord.User = await self.bot.fetch_user(628291559158448129)
        symphonic_mention: str = symphonic.mention
        zeroslashzero_mention: str = zeroslashzero.mention
        eyes_mention: str = eyes.mention
        stalin_mention: str = stalin.mention
        credits_embed.set_footer(text="current bot version: v5.0.0-alpha9")
        credits_embed.add_field(name="v3+ Creator", value=zeroslashzero_mention)
        credits_embed.add_field(name="Original Creator", value=symphonic_mention)
        credits_embed.add_field(name="Bot Framework", value=eyes_mention)
        credits_embed.add_field(name="Moral Support", value=stalin_mention)
        credits_embed.add_field(name='API Providers', value="https://corona.lmao.ninja", inline=False)
        credits_embed.add_field(name="discord.py Devs", value="https://github.com/Rapptz/discord.py", inline=False)
        await ctx.send(embed=credits_embed)

    @commands.command()
    async def invite(self, ctx: MyContext):
        invite_embed = discord.Embed(color=discord.Color.purple(), title="Invite Links")
        oauth_url = discord.utils.oauth_url(client_id=str(self.bot.user.id),
                                            permissions=discord.Permissions(read_messages=True, send_messages=True,
                                                                            embed_links=True, manage_messages=True))
        invite_embed.add_field(name="Bot Invite Link", value=oauth_url)
        invite_embed.add_field(name="Discord Server Invite Link", value="https://discord.gg/v8qDQDc")
        await ctx.send(embed=invite_embed)

    @commands.command()
    async def stats(self, ctx: MyContext):
        await ctx.send("https://statcord.com/bot/{self.bot.user.id}")

    @commands.command(name="is_premium_guild")
    async def is_premium(self, ctx: MyContext):
        db_guild = await get_from_db(ctx.guild)
        premium = db_guild.is_premium
        msg = "This guild ({ctx.guild.name}, ID `{ctx.guild.id}`) is "
        if premium:
            msg += " a "
        else:
            msg += " not a "
        msg += "premium guild. "
        if premium:
            msg += "<3 from 0/0#0001!"
        else:
            msg += "To get a few perks and 0/0#0001's unconditional love, check out the `/donate` command!"
        await ctx.send(msg)

    @commands.command()
    async def ping(self, ctx: MyContext):
        """
        Check that the bot is online, and give the latency between the bot and discord servers.
        """
        _ = await ctx.get_translate_function()

        t_1 = time.perf_counter()
        try:
            await ctx.channel.trigger_typing()  # tell Discord that the bot is "typing", which is a very simple request
        except discord.NotFound:
            await ctx.send("I seem to be having issues, apparently I can't find the channel you ran that command in! "
                           "Please try again.")
            return
        t_2 = time.perf_counter()
        time_delta = round((t_2 - t_1) * 1000)  # calculate the time needed to trigger typing
        await ctx.send(_("Pong. — Time taken: {milliseconds}ms", milliseconds=time_delta))  # send a message telling the
        # user the calculated ping time

    @commands.is_owner()
    @commands.command(name="async_setup")
    async def async_setup(self, ctx: MyContext):
        msg = await ctx.send("Calling `self.bot.async_setup()`...")
        await self.bot.async_setup()
        await msg.edit(content="Bot has been setup!")

    @commands.command()
    async def vote(self, ctx: MyContext):
        vote_embed = discord.Embed(title="Vote Sites",
                                   description="Voting for the bot gives it more visibility, which means it ends up in "
                                               "more servers, giving me (the dev) more incentive to add more "
                                               "features!\n"
                                               "If you want a specific feature, let me know with the `/suggest` "
                                               "command!")
        vote_embed.add_field(name="discord.boats",
                             value="https://discord.boats/bot/675390513020403731/vote")
        vote_embed.add_field(name="bots.discordlabs.org",
                             value="https://bots.discordlabs.org/bot/675390513020403731?vote")
        vote_embed.add_field(name="top.gg",
                             value="https://top.gg/bot/675390513020403731/vote")
        vote_embed.set_footer(text="**DO NOT disable adblockers!**")
        await ctx.send(embed=vote_embed)

    @commands.command()
    @commands.is_owner()
    async def migrate_to_db(self, ctx: MyContext):
        msg = await ctx.send("Loading old database...")
        with open("autoupdates.json", "r") as f:
            autoupdater_data = json.load(f)
        await msg.edit(content="Now parsing {len(autoupdater_data)} autoupdaters...")
        for chnl in autoupdater_data:
            channel = self.bot.get_channel(chnl["ChannelID"])
            db_channel = await get_from_db(channel)
            if db_channel is None:
                continue
            db_channel.autoupdater.already_set = True
            db_channel.autoupdater.delay = chnl["UpdateTime"]
            db_channel.autoupdater.country_name = chnl["Country"]
            db_channel.autoupdater.last_updated = datetime.datetime.utcfromtimestamp(chnl["LastUpdateTime"])
            await db_channel.autoupdater.save()
            await db_channel.save()
        await msg.edit(content="Success!")


setup = UtilsCommands.setup


'''
@commands.command()
@commands.has_guild_permissions(administrator=True)
async def claim(ctx):
    if ctx.message.guild is None:
        await ctx.send(
            'We\'re in a private DM channel: head to a server where you\'re a admin with this bot and try again!')
        return
    for member in ctx.message.guild.members:
        if member.id == 675390513020403731:
            await ctx.send('I\'ve detected the non-beta version of the bot in this server! Remove that bot to be able '
                           'to claim your beta tester role.')
            return
    botGuild = bot.get_guild(675390855716274216)
    betaRole = botGuild.get_role(723645816245452880)
    for member in botGuild.members:
        if member.id == ctx.author.id:
            member.add_roles(betaRole)
            await ctx.send("You are now a beta tester!")
            return
    await ctx.send("You don't seem to be part of the bot's support server. Try joining it and trying again: `/invite`")
'''
