"""
Some example of commands that can be used to interact with the database.
"""
import secrets
import uuid
from typing import Optional

import discord
from discord.ext import commands
from discord.utils import escape_markdown, escape_mentions

from utils.cog_class import Cog
from utils.ctx_class import MyContext
from utils.models import get_from_db


class DatabaseCommands(Cog):
    @commands.group()
    @commands.has_permissions(manage_guild=True)
    async def settings(self, ctx: MyContext):
        """
        Commands to view and edit settings
        You must have the manage guild permission.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @settings.command()
    async def prefix(self, ctx: MyContext, new_prefix: Optional[str] = None):
        """
        Change/view the server prefix.

        Note that some prefixes are global and can't be edited.
        Those include `covid` and `c!`.
        """
        _ = await ctx.get_translate_function()
        db_guild = await get_from_db(ctx.guild)
        if new_prefix:
            db_guild.prefix = new_prefix
        await db_guild.save()
        if db_guild.prefix:
            await ctx.send(_("The server prefix is set to `{0}`.",
                             escape_mentions(escape_markdown(db_guild.prefix))))
        else:
            await ctx.send(_("There is no specific prefix set for this guild."))

    @settings.command()
    async def language(self, ctx: MyContext, language_code: Optional[str] = None):
        """
        Change/view the server language.

        Specify the server language as a 2/5 letters code. For example, if you live in France, you'd use fr or fr_FR.
        In Québec, you could use fr_QC.
        """
        db_guild = await get_from_db(ctx.guild)
        if language_code:
            db_guild.language = language_code
        await db_guild.save()

        _ = await ctx.get_translate_function()
        if db_guild.language:
            await ctx.send(_("The server language is now set to `{0}`.",
                             escape_mentions(escape_markdown(db_guild.language))))

            # Do not translate
            await ctx.send(f"If you wish to go back to the default, english language, use "
                           f"`{ctx.prefix}{ctx.command.qualified_name} en`")
        else:
            await ctx.send(_("There is no specific language set for this guild."))

    @settings.command()
    async def api_key(self, ctx: MyContext, action: str):
        """
        Manage your channel's API key.
        Pass one of the following arguments to manage the key.
        "view": DMs you your API key.
        "revoke": Revokes the API key. **DOES NOT generate a new one!** Use "new" for that.
        "new": Revokes the API key, if one exists, generates a new one, and DMs it to you.
        """
        db_channel = await get_from_db(ctx.channel)
        _ = await ctx.get_translate_function()
        if db_channel.disabled_api:
            await ctx.reply(_("The API has been disabled for this channel. To restore your permissions, contact "
                              "0/0#0001 on the official support server."))
            return
        if action.lower() in ("view", "see"):
            await ctx.author.send(str(db_channel.api_key))
            await ctx.reply(_("DMed your API key to you."))
        elif action.lower() in ("revoke", "delete"):
            db_channel.api_key = None
            await ctx.reply(_("Revoked/deleted API key."))
        elif action.lower() in ("regenerate", "new", "generate"):
            api_key = uuid.uuid4()
            db_channel.api_key = api_key
            await ctx.author.send(api_key)
            await ctx.reply(_("DMed your new API key to you."))
        else:
            await ctx.reply(_("Invalid action. It must be one of {0}.", f"`{'` `'.join(['view', 'revoke', 'new'])}`"))
        await db_channel.save()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def disable_api(self, ctx: MyContext, channel: discord.TextChannel):
        _ = await ctx.get_translate_function()
        db_channel = await get_from_db(channel)
        db_channel.disabled_api = True
        await db_channel.save()
        await ctx.reply(_("Disabled the API for {0}.", channel.name))

    @settings.command()
    async def minigame(self, ctx: MyContext, enabled: bool, log_channel: Optional[discord.TextChannel],
                       infected_role: Optional[discord.Role], cured_role: Optional[discord.Role],
                       dead_role: Optional[discord.Role]):
        _ = await ctx.get_translate_function()
        db_guild = await get_from_db(ctx.guild)
        if enabled:
            if not log_channel and not db_guild.log_channel:
                await ctx.reply(_("You must mention a channel to log to if one is not already set."))
            elif not infected_role and not db_guild.infected_role:
                await ctx.reply(_("You must mention a role to use as the infected role if one is not already set."))
            elif not cured_role and not db_guild.cured_role:
                await ctx.reply(_("You must mention a role to use as the cured role if one is not already set."))
            elif not dead_role and not db_guild.dead_role:
                await ctx.reply(_("You must mention a role to use as the dead role if one is not already set."))
            else:
                if log_channel:
                    db_guild.log_channel = log_channel.id
                if infected_role:
                    db_guild.infected_role = infected_role.id
                if cured_role:
                    db_guild.cured_role = cured_role.id
                if dead_role:
                    db_guild.dead_role = dead_role.id
                db_guild.minigame_enabled = True
                await ctx.reply(_("The minigame has now been enabled for your server! Have fun!"))
        else:
            db_guild.minigame_enabled = False
            await ctx.reply(_("The minigame has now been disabled for your server."))
        await db_guild.save()


setup = DatabaseCommands.setup
