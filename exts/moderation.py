import asyncio
from utility.buttons import Paginator
import asyncpg
import discord
from discord.ext import commands, tasks
from discord.ext.commands.core import command
import more_itertools
from bot import Bot, CustomContext
from utility.constants import Time
from utility.functions import ProcessError, build_embed
import typing
from utility.decorators import mod_check
from utility.converters import CharLimit, TimeConvert
import contextlib
import datetime
from utility.logger import Log

log = Log("logs.log").get_logger(__name__)


class Moderation(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.mutes.start()
        log.info("Moderation cog initialized, starting mutes loop.")
        self.channel_spam_cooldown = commands.CooldownMapping.from_cooldown(
            rate=3, per=3, type=commands.BucketType.channel
        )

    def build_embed(self, user: typing.Union[discord.Member, discord.User], **kwargs):
        embed = discord.Embed(**kwargs, color=discord.Colour.green())
        text = f'Today at {discord.utils.utcnow().strftime("%H:%M %p")}'
        embed.set_footer(text=text, icon_url=user.avatar.url)
        return embed

    async def get_muted_role(
        self, conn: asyncpg.connection.Connection, guild: discord.Guild
    ) -> typing.Optional[discord.Role]:
        if self.bot.mute_roles.get(guild.id):
            role_id = self.bot.mute_roles.get(guild.id)
            role = guild.get_role(role_id)
            if not role:
                raise ProcessError("This guild set muted role, but it was deleted.")
            return role

        data = await conn.fetch(
            """SELECT muted_role FROM guilds_config WHERE guild_id = ($1)""", guild.id
        )
        if not data:
            raise ProcessError("This guild didn't set muted role.")
        muted_role_id = data[0]["muted_role"]
        role = guild.get_role(muted_role_id)
        if not role:
            raise ProcessError("This guild set muted role, but it was deleted.")
        return role

    async def insert_mute(
        self,
        conn: asyncpg.connection.Connection,
        member: discord.Member,
        moderator: discord.Member,
        seconds: int,
        reason: str,
    ):
        ends_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=seconds)
        mute_id = await conn.fetch(
            """INSERT INTO mutes (guild_id, member_id, muted_by, reason, muted_at, ends_at) VALUES($1, $2, $3, $4, $5, $6) RETURNING mute_id""",
            member.guild.id,
            member.id,
            moderator.id,
            reason,
            datetime.datetime.utcnow(),
            ends_at,
        )
        mute_id = mute_id[0]["mute_id"]
        return mute_id

    async def remove_mute(
        self, conn: asyncpg.connection.Connection, member: discord.Member
    ):
        await conn.execute(
            """DELETE FROM mutes WHERE member_id = ($1) AND guild_id = ($2)""",
            member.id,
            member.guild.id,
        )

    async def is_muted(
        self, conn: asyncpg.connection.Connection, member: discord.Member
    ):
        data = await conn.fetch(
            """SELECT * FROM mutes WHERE member_id = ($1) AND guild_id = ($2)""",
            member.id,
            member.guild.id,
        )
        if data:
            return True
        return False

    async def insert_warn(
        self,
        conn: asyncpg.connection.Connection,
        member: discord.Member,
        moderator: discord.Member,
        reason: str,
    ):
        warn_id = await conn.fetch(
            """INSERT INTO warnings (guild_id, member_id, warned_by, reason, warned_at) VALUES($1, $2, $3, $4, $5) RETURNING warn_id""",
            member.guild.id,
            member.id,
            moderator.id,
            reason,
            datetime.datetime.utcnow(),
        )
        warn_id = warn_id[0]["warn_id"]
        return warn_id

    @commands.command(name="kick", description="Kicks a member from a guild.")
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.has_guild_permissions(kick_members=True)
    @mod_check("kick")
    async def _kick(
        self,
        ctx: CustomContext,
        member: discord.Member,
        *,
        reason: CharLimit(char_limit=200) = "None.",
    ):
        await member.kick(reason=reason)
        embed = self.build_embed(
            title="Member kicked.",
            description=f"{ctx.author.mention} kicked {member.name}.\n\n**Reason:** {reason}",
            user=ctx.author,
        )
        await ctx.send(embed=embed)
        embed = self.build_embed(
            user=member,
            description=f"You were kicked out from {ctx.guild.name} by {ctx.author.name}\n\n**Reason:** {reason}",
        )
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await member.send(embed=embed)

    @commands.command(name="ban", description="bans a member or user from a guild.")
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @mod_check("ban")
    async def _ban(
        self,
        ctx: CustomContext,
        user: typing.Union[discord.Member, discord.User],
        delete_message_days: typing.Optional[int],
        *,
        reason: CharLimit(char_limit=200) = "None.",
    ):
        delete_message_days = delete_message_days or 0
        await ctx.guild.ban(
            user=user, reason=reason, delete_message_days=delete_message_days
        )
        embed = self.build_embed(
            user=ctx.author,
            title="User banned.",
            description=f"{ctx.author.mention} banned {user.name}.\n\n**Reason:** {reason}",
        )
        await ctx.send(embed=embed)
        embed = self.build_embed(
            user=user,
            description=f"You were banned from {ctx.guild.name} by {ctx.author.name}\n\n**Reason:** {reason}",
        )
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await user.send(embed=embed)

    @commands.command(
        name="unban", description="Unbans a user from a guild.", aliases=["un-ban"]
    )
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @mod_check("unban")
    async def _unban(
        self,
        ctx: CustomContext,
        user: discord.User,
        *,
        reason: CharLimit(char_limit=250) = "None.",
    ):
        await ctx.guild.unban(user=user, reason=reason)
        embed = self.build_embed(
            user=ctx.author,
            title="User un-banned.",
            description=f"{ctx.author.mention} un-banned {user.name}.\n\n**Reason:** {reason}",
        )
        await ctx.send(embed=embed)
        embed = self.build_embed(
            user=user,
            description=f"You were banned from {ctx.guild.name} by {ctx.author.name}\n\n**Reason:** {reason}",
        )
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await user.send(embed=embed)

    @commands.command(name="add-roles", description="Add roles to given members.")
    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def add_roles(
        self,
        ctx: CustomContext,
        role: discord.Role,
        members: commands.Greedy[discord.Member],
        *,
        reason: CharLimit(char_limit=100),
    ):
        if len(members) > 10:
            raise ProcessError("I can't add roles to more than 10 members at one time.")
        embed = self.build_embed(
            user=ctx.author,
            description=f"This process may take {len(members) * 2} seconds.",
        )
        full = ""
        await ctx.send(embed=embed)
        for member in members:
            try:
                await member.add_roles(role, reason=reason)
                full += f"{member.name} - Success\n"
            except Exception as e:
                full += f"{member.name} - Failure. Reason: `{e}`"
            await asyncio.sleep(2)
        embed = self.build_embed(
            user=ctx.author, title="Process finished.", description=f"```{full}```"
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="mute", description="Mutes the selected member for selected time."
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @mod_check("mute")
    async def _mute(
        self,
        ctx: CustomContext,
        member: discord.Member,
        time: TimeConvert,
        *,
        reason: CharLimit(char_limit=200),
    ):
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            role = await self.get_muted_role(conn, ctx.guild)
            is_muted = await self.is_muted(conn, member)
            if is_muted or role in member.roles:
                raise ProcessError(
                    "This member is already muted, or already have the muted role."
                )
            await member.add_roles(role, reason=reason)
            mute_id = await self.insert_mute(conn, member, ctx.author, time, reason)
        ends_at = discord.utils.format_dt(
            discord.utils.utcnow() + datetime.timedelta(seconds=time), style="F"
        )
        embed = self.build_embed(
            user=ctx.author,
            title="Member muted.",
            description=f"{member.mention} was muted by {ctx.author}\n\n**Reason:** {reason}\n\n**Mute id:** {mute_id}\n\n**Ends at:** {ends_at}",
        )
        await ctx.send(embed=embed)

        if time < 3600:
            await asyncio.sleep(time)
            async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
                await member.remove_roles(role, reason=f"Mute end.")
                await self.remove_mute(conn, member)
                await conn.close()

    @commands.command(
        name="unmute", description="Unmuted the selected member.", aliases=["un-mute"]
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @mod_check("unmute")
    async def unmute(self, ctx: CustomContext, member: discord.Member):
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            role = await self.get_muted_role(ctx.guild)
            await self.remove_mute(conn, member)
        if role not in member.roles:
            raise ProcessError(f"{member} does not have the muted role.")
        await member.remove_roles(role, reason="Unmuted command.")
        embed = self.build_embed(
            user=ctx.author,
            title="Member unmuted.",
            description=f"{ctx.author.mention} removed the mute for {member.mention}",
        )
        await ctx.send(embed=embed)

    @commands.command(name="warn", description="Warns the selected member.")
    @commands.has_guild_permissions(manage_messages=True)
    @mod_check("warn")
    async def warn(
        self,
        ctx: CustomContext,
        member: discord.Member,
        *,
        reason: CharLimit(char_limit=150) = "None.",
    ):
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            warn_id = await self.insert_warn(conn, member, ctx.author, reason)
        embed = self.build_embed(
            user=ctx.author,
            title="Member warned.",
            description=f"{member.mention} was warned by {ctx.author}\n\n**Warn id:** `{warn_id}`\n\n**Reason:** {reason}",
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="unwarn",
        description="Removes a warning for the selected member.",
        aliases=["un-warn", "remove-warn"],
    )
    @commands.has_guild_permissions(manage_messages=True)
    @mod_check("unwarn")
    async def unwarn(self, ctx: CustomContext, member: discord.Member, warn_id: int):
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            data = await conn.fetch(
                """SELECT * FROM warnings WHERE guild_id = ($1) AND member_id = ($2) AND warn_id = ($3)""",
                ctx.guild.id,
                member.id,
                warn_id,
            )
            if not data:
                raise ProcessError(f"Could not find any warn with these credentials.")
            record = data[0]
            warned_by_id = record["warned_by"]
            warned_by = (
                ctx.guild.get_member(warned_by_id)
                or self.bot.get_user(warned_by_id)
                or f"Not found. ID: {warned_by_id}"
            )
            reason = record["reason"]
            warned_at = record["warned_at"]
            timestamp_warned_at = discord.utils.format_dt(warned_at, style="F")
            description = f"Are you sure you'd like to delete this warning?\n\n\n*\"*Warn id:** {warn_id}\n\n**Warned by:** {warned_by}\n\n**Reason:** {reason}\n\n**Warned at:** {timestamp_warned_at}"
            embed = self.build_embed(
                user=ctx.author, title="Delete warn.", description=description
            )

            async def check(interaction: discord.Interaction):
                return interaction.user.id == ctx.author.id

            view, message = await ctx.send_confirm(embed=embed, check=check)
            if not view.value:
                return await ctx.send(
                    embed=self.build_embed(user=ctx.author, title="Process aborted.")
                )
            await conn.execute(
                """DELETE FROM warnings WHERE guild_id = ($1) AND member_id = ($2) AND warn_id = ($3)""",
                ctx.guild.id,
                member.id,
                warn_id,
            )
        await ctx.send(
            embed=self.build_embed(
                user=ctx.author,
                title="Warne deleted.",
                description=f"The warning for {member} was deleted.",
            )
        )

    @commands.command(
        name="infractions",
        description="Shows all current infractions for a member. Mute and warn.",
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def infractions(self, ctx: CustomContext, member: discord.Member):
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT() + 10) as conn:
            mutes = await conn.fetch(
                """SELECT * FROM mutes WHERE guild_id = ($1) AND member_id = ($2)""",
                ctx.guild.id,
                member.id,
            )
            warnings = await conn.fetch(
                """SELECT * FROM warnings WHERE guild_id = ($1) AND member_id = ($2)""",
                ctx.guild.id,
                member.id,
            )
        embeds = []
        if mutes:
            for record in mutes:
                embed = discord.Embed(
                    title="Mute infraction.",
                    description="",
                    color=discord.Colour.blurple(),
                )
                mute_id = record["mute_id"]
                muted_by_id = record["muted_by"]
                muted_by = (
                    ctx.guild.get_member(muted_by_id)
                    or self.bot.get_user(muted_by_id)
                    or f"Couldn't fetch. ID ({muted_by_id})"
                )
                reason = record["reason"]
                muted_at_timestamp = discord.utils.format_dt(
                    record["muted_at"], style="F"
                )
                ends_at_timestamp = discord.utils.format_dt(
                    record["ends_at"], style="F"
                )
                embed.description += f"**Mute id:** {mute_id}\n\n**Muted by:** {muted_by}\n\n**Reason:** {reason}\n\n**Muted at:** {muted_at_timestamp}\n\n**Ends at:** {ends_at_timestamp}"
                embeds.append(embed)
        if warnings:
            for record in warnings:
                embed = discord.Embed(
                    title="Warning infraction.",
                    description="",
                    color=discord.Colour.blurple(),
                )
                warn_id = record["warn_id"]
                warned_by_id = record["warned_by"]
                warned_by = (
                    ctx.guild.get_member(warned_by_id)
                    or self.bot.get_user(warned_by_id)
                    or f"Couldn't fetch. ID ({muted_by_id})"
                )
                reason = record["reason"]
                warned_at_timestamp = discord.utils.format_dt(
                    record["warned_at"], style="F"
                )
                embed.description += f"**Warn id:** {warn_id}\n\n**Warned by:** {warned_by}\n\n**Reason:** {reason}\n\n**Warned at:** {warned_at_timestamp}"
                embeds.append(embed)

        if not embeds:
            return await ctx.send(
                embed=self.build_embed(
                    user=ctx.author,
                    description=f"{member.mention} does not have any infractions in this guild.",
                )
            )

        async def check(interaction: discord.Interaction):
            return interaction.user.id == ctx.author.id

        paginator = Paginator(
            ctx=ctx, embeds=embeds, timeout=Time.BASIC_TIMEOUT(), check=check
        )
        await paginator.run()

    @tasks.loop(minutes=1)
    async def mutes(self):
        async with self.bot.pool.acquire(timeout=20) as conn:
            data = await conn.fetch(
                """SELECT * FROM mutes WHERE ends_at < ($1)""",
                datetime.datetime.utcnow(),
            )
            if not data:
                return
            for record in data:
                guild = self.bot.get_guild(record["guild_id"])
                if not guild:
                    log.info(f'Guild {record["guild_id"]} fetch failed.')
                    return
                try:
                    role = await self.get_muted_role(conn, guild)
                except ProcessError as e:
                    log.info(f"Getting role for {guild} failed. {e}")
                member = guild.get_member(record["member_id"])
                if not member:
                    log.info(f'Getting member {record["member_id"]} failed.')
                await member.remove_roles(role, reason="Mute end.")
                await self.remove_mute(conn, member)
                await asyncio.sleep(1)
            await asyncio.sleep(1)
        pass

    @mutes.before_loop
    async def wait_until_ready_loop(self):
        await self.bot.wait_until_ready()
        log.info(f"Before mute loop. Waited for internal cache.")


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
