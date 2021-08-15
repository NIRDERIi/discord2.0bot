import asyncio
import datetime
from time import time
import typing
import discord
from discord.ext import commands
from bot import Bot, CustomContext
from utility.functions import ProcessError, build_embed, basic_guild_check
from utility.constants import Time
import functools
from utility.converters import CharLimit
import asyncio
import contextlib


class configuration(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        self.created_guild_rows = []

    async def create_guild_row(self, ctx: CustomContext):
        if ctx.guild.id in self.created_guild_rows:
            return
        async with self.bot.pool.acquire() as conn:
            data = await conn.fetch(
                """SELECT guild_id FROM guilds_config WHERE guild_id = ($1)""",
                ctx.guild.id,
            )
            if not data:
                await conn.execute(
                    """INSERT INTO guilds_config VALUES($1, $2, $3, $4, $5, $6)""",
                    ctx.guild.id,
                    0,
                    "m!",
                    0,
                    0,
                    None,
                )
                await conn.close()
            self.created_guild_rows.append(ctx.guild.id)

    @commands.command(
        name="set-muted",
        description=f"Sets guild muted role.",
        aliases=["set-muted-role"],
    )
    @commands.has_guild_permissions(administrator=True)
    async def set_muted(self, ctx: CustomContext, *, role: discord.Role):
        if ctx.guild.me.top_role <= role:
            raise ProcessError("You can't set muted role higher than my top role.")
        check = functools.partial(basic_guild_check, ctx)
        await self.create_guild_row(ctx)
        embed = build_embed(
            title="Confirm.",
            description=f"Are you sure you'd like to set {role.mention} as the new muted role?",
        )
        view, message = await ctx.send_confirm(embed=embed, check=check)
        if view.value:
            async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
                await conn.execute(
                    """UPDATE guilds_config SET muted_role = ($1) WHERE guild_id = ($2)""",
                    role.id,
                    ctx.guild.id,
                )
            await ctx.send(
                embed=build_embed(
                    title="Confirmed.",
                    description=f"Setted {role.mention} as the new muted role!",
                )
            )
            self.bot.mute_roles[ctx.guild.id] = role.id
        else:
            await ctx.send(embed=build_embed(title="Process aborted."))

    @commands.command(
        name="remove-muted",
        description="Removes guild muted role.",
        aliases=["remove-muted-role"],
    )
    @commands.has_guild_permissions(administrator=True)
    async def remove_muted(self, ctx: CustomContext):
        check = functools.partial(basic_guild_check, ctx)
        await self.create_guild_row(ctx)
        embed = build_embed(
            title="Confirm.",
            description=f"Are you sure you'd like to remove the guild muted role?",
        )
        view, message = await ctx.send_confirm(embed=embed, check=check)
        if view.value:
            async with self.bot.pool.acquire(time=Time.BASIC_DBS_TIMEOUT()) as conn:
                await conn.execute(
                    """UPDATE guilds_config SET muted_role = ($1) WHERE guild_id = ($2)""",
                    None,
                    ctx.guild.id,
                )
            await ctx.send(
                embed=build_embed(
                    title="Confirmed.", description=f"Removed the muted role!"
                )
            )
            with contextlib.suppress(KeyError):
                self.bot.mute_roles.pop(ctx.guild.id)
        else:
            await ctx.send(embed=build_embed(title="Process aborted."))

    @commands.command(
        name="set-prefix", description="Sets guild prefix", aliases=["prefix"]
    )
    @commands.has_guild_permissions(administrator=True)
    async def set_prefix(self, ctx: CustomContext, *, prefix: CharLimit(10)):
        await self.create_guild_row(ctx)
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            await conn.execute(
                """UPDATE guilds_config SET prefix = ($1) WHERE guild_id = ($2)""",
                prefix,
                ctx.guild.id,
            )
        embed = build_embed(
            title="Changed prefix.",
            description=f"{prefix} is now this guild new prefix.",
        )
        self.bot.prefixes[ctx.guild.id] = prefix
        await ctx.send(embed=embed)

    @commands.command(
        name="set-economy",
        description="Sets guild economy role",
        aliases=["set-economy-role"],
    )
    @commands.has_guild_permissions(administrator=True)
    async def set_economy(self, ctx: CustomContext, *, role: discord.Role):
        check = functools.partial(basic_guild_check, ctx)
        await self.create_guild_row(ctx)
        embed = build_embed(
            title="Confirm.",
            description=f"Are you sure you'd like to set {role.mention} as the new economy role?",
        )
        view, message = await ctx.send_confirm(embed=embed, check=check)
        if view.value:
            async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
                await conn.execute(
                    """UPDATE guilds_config SET economy_role = ($1) WHERE guild_id = ($2)""",
                    role.id,
                    ctx.guild.id,
                )
            await ctx.send(
                embed=build_embed(
                    title="Confirmed.",
                    description=f"Setted {role.mention} as the new economy role!",
                )
            )
        else:
            await ctx.send(embed=build_embed(title="Process aborted."))

    @commands.command(
        name="remove-economy",
        description="Removes guild economy role.",
        aliases=["remove-economy-role"],
    )
    @commands.has_guild_permissions(administrator=True)
    async def remove_economy(self, ctx: CustomContext):
        check = functools.partial(basic_guild_check, ctx)
        await self.create_guild_row(ctx)
        embed = build_embed(
            title="Confirm.",
            description=f"Are you sure you'd like to remove the guild economy role?",
        )
        view, message = await ctx.send_confirm(embed=embed, check=check)
        if view.value:
            async with self.bot.pool.acquire(time=Time.BASIC_DBS_TIMEOUT()) as conn:
                await conn.execute(
                    """UPDATE guilds_config SET economy_role = ($1) WHERE guild_id = ($2)""",
                    None,
                    ctx.guild.id,
                )
            await ctx.send(
                embed=build_embed(
                    title="Confirmed.", description=f"Removed the economy role!"
                )
            )
        else:
            await ctx.send(embed=build_embed(title="Process aborted."))

    @commands.command(
        name="set-logs", description="Sets logs channel.", aliases=["set-logs-channel"]
    )
    @commands.has_guild_permissions(administrator=True)
    async def set_logs(
        self, ctx: CustomContext, *, channel: typing.Optional[discord.TextChannel]
    ):
        await self.create_guild_row(ctx)
        channel = channel or ctx.channel
        if len(await ctx.guild.webhooks()) == 10:
            raise ProcessError(
                "This process is not available. You must delete one webhook, as this process relies on webhooks."
            )

        await ctx.send(
            embed=build_embed(
                title="Select avatar.",
                description="Send an image to be your webhook avatar, or don't respond for basic avatar. Type cancel at any point to cancel the process.",
            )
        )

        def check_avatar(message: discord.Message):
            return (
                message.author.guild_permissions.administrator
                and message.attachments
                and message.channel == ctx.channel
            )

        def check_name(message: discord.Message):
            return (
                message.author.guild_permissions.administrator
                and message.content
                and message.channel == ctx.channel
            )

        try:
            message: discord.Message = await self.bot.wait_for(
                event="message", check=check_avatar, timeout=Time.BASIC_TIMEOUT()
            )
            if message.content and message.content.lower() in ["cancel", "abort"]:
                return await ctx.send(
                    embed=build_embed(
                        title="Process aborted.", timestamp=datetime.datetime.utcnow()
                    )
                )
            webhook_avatar = await message.attachments[0].read()
        except asyncio.TimeoutError:
            await ctx.send(
                embed=build_embed(title="Timed out!", description="Basic avatar set.")
            )
            webhook_avatar = await self.bot.user.avatar.read()

        await ctx.send(
            embed=build_embed(
                title="Select nickname.",
                description="Send a string to be your webhook nickname, or don't respond for basic avatar. Type cancel to abort process.",
            )
        )
        try:
            message: discord.Message = await self.bot.wait_for(
                event="message", check=check_name, timeout=Time.BASIC_TIMEOUT()
            )
            if message.content and message.content.lower() in ["cancel", "abort"]:
                return await ctx.send(
                    embed=build_embed(
                        title="Process aborted.", timestamp=datetime.datetime.utcnow()
                    )
                )
            webhook_name = message.content
        except asyncio.TimeoutError:
            webhook_name = ctx.guild.me.display_name
        webhook = await channel.create_webhook(
            name=webhook_name, avatar=webhook_avatar, reason="Logs channel webhook."
        )
        webhook_url = webhook.url

        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            check_webhook = await conn.fetch(
                """SELECT webhook_url, logs_channel FROM guilds_config WHERE guild_id = ($1)""",
                ctx.guild.id,
            )
            if check_webhook[0]["webhook_url"] and check_webhook[0]["logs_channel"]:
                try:
                    webhook_existed = discord.Webhook.from_url(
                        url=check_webhook[0]["webhook_url"], session=self.bot._session
                    )
                    await webhook_existed.delete()
                except discord.InvalidArgument:
                    pass

            await conn.execute(
                """UPDATE guilds_config SET logs_channel = ($1), webhook_url = ($2) WHERE guild_id = ($3)""",
                channel.id,
                webhook_url,
                ctx.guild.id,
            )
            self.bot.logs_webhooks[ctx.guild.id] = webhook_url
        await ctx.send(
            embed=build_embed(title="Process finished.", description="Created webhook.")
        )

    @commands.command(
        name="remove-logs",
        description="Removes guild logs-channel.",
        aliases=["remove-logs-channel"],
    )
    @commands.has_guild_permissions(administrator=True)
    async def remove_logs(self, ctx: CustomContext):
        check = functools.partial(basic_guild_check, ctx)
        await self.create_guild_row(ctx)
        embed = build_embed(
            title="Confirm.",
            description="Are you sure you'd like to disable this guild logs?",
        )
        view, message = await ctx.send_confirm(embed=embed, check=check)
        if view.value:
            async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
                check_webhook = await conn.fetch(
                    """SELECT webhook_url, logs_channel FROM guilds_config WHERE guild_id = ($1)""",
                    ctx.guild.id,
                )
                if check_webhook[0]["webhook_url"] and check_webhook[0]["logs_channel"]:
                    try:
                        webhook_existed = discord.Webhook.from_url(
                            url=check_webhook[0]["webhook_url"],
                            session=self.bot._session,
                        )
                        await webhook_existed.delete()
                        self.bot.logs_webhooks.pop(ctx.guild.id)
                    except discord.InvalidArgument:
                        pass
                    except TypeError:
                        pass
                    except KeyError:
                        pass

                await conn.execute(
                    """UPDATE guilds_config SET webhook_url = ($1), logs_channel = ($2) WHERE guild_id = ($3)""",
                    None,
                    None,
                    ctx.guild.id,
                )
                await ctx.send(
                    embed=build_embed(
                        title="Confirmed.", description="Removed this guild logs."
                    )
                )
        else:
            await ctx.send(embed=build_embed(title="Process aborted."))


def setup(bot: Bot):
    bot.add_cog(configuration(bot))
