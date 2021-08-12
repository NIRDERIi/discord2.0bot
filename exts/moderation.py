import asyncio
import asyncpg
import discord
from discord.ext import commands
from discord.ext.commands.core import command
from bot import Bot, CustomContext
from utility.constants import Time
from utility.functions import ProcessError, build_embed
import typing
from utility.decorators import mod_check
from utility.converters import CharLimit, TimeConvert
import contextlib
import datetime


class Moderation(commands.Cog):
    
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    def build_embed(self, user: typing.Union[discord.Member, discord.User], **kwargs):
        embed = discord.Embed(**kwargs, color=discord.Colour.green())
        text = f'Today at {discord.utils.utcnow().strftime("%H:%M %p")}'
        embed.set_footer(text=text, icon_url=user.avatar.url)
        return embed

        
        

    async def get_muted_role(self, guild: discord.Guild) -> typing.Optional[discord.Role]:
        if self.bot.mute_roles.get(guild.id):
            role_id = self.bot.mute_role.get(guild.id)
            role = guild.get_role(role_id)
            if not role:
                raise ProcessError('This guild set muted role, but it was deleted.')
            return role

        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:

            data = await conn.fetch('''SELECT muted_role FROM guilds_config WHERE guild_id = ($1)''', guild.id)
            if not data:
                raise ProcessError('This guild didn\'t set muted role.')
            muted_role_id = data[0]['muted_role']
            role = guild.get_role(muted_role_id)
            if not role:
                raise ProcessError('This guild set muted role, but it was deleted.')
            return role
    
    async def insert_mute(self, conn: asyncpg.connection.Connection, member: discord.Member, moderator: discord.Member, seconds: int):
        ends_at = discord.utils.utcnow() + datetime.timedelta(seconds=seconds)
        mute_id = await conn.execute('''INSERT INTO mutes (guild_id, member_id, muted_by, muted_at, ends_at) VALUES($1, $2, $3, $4, $5) RETURNING mute_id''', member.guild.id, member.id, moderator.id, discord.utils.utcnow(), ends_at)
        mute_id = mute_id[0]['mute_id']
        return mute_id
    
    async def remove_mute(self, conn: asyncpg.connection.Connection, mute_id: int, guild_id: int):
        await conn.execute('''DELETE FROM mutes WHERE guild_id = ($1) AND mute_id = ($2)''', guild_id, mute_id)




    @commands.command(name='kick', description='Kicks a member from a guild.')
    @commands.bot_has_guild_permissions(kick_members=True)
    @commands.has_guild_permissions(kick_members=True)
    @mod_check('kick')
    async def _kick(self, ctx: CustomContext, member: discord.Member, *, reason: CharLimit(char_limit=200) = 'None.'):
        await member.kick(reason=reason)
        embed = self.build_embed(title='Member kicked.', description=f'{ctx.author.mention} kicked {member.name}.\n\n**Reason:** {reason}', user=ctx.author)
        await ctx.send(embed=embed)
        embed = self.build_embed(user=member, description=f'You were kicked out from {ctx.guild.name} by {ctx.author.name}\n\n**Reason:** {reason}')
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await member.send(embed=embed)

    @commands.command(name='ban', description='bans a member or user from a guild.')
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @mod_check('ban')
    async def _ban(self, ctx: CustomContext, user: typing.Union[discord.Member, discord.User], delete_message_days: typing.Optional[int], *, reason: CharLimit(char_limit=200)='None.'):
        delete_message_days = delete_message_days or 0
        await ctx.guild.ban(user=user, reason=reason, delete_message_days=delete_message_days)
        embed = self.build_embed(user=ctx.author, title='User banned.', description=f'{ctx.author.mention} banned {user.name}.\n\n**Reason:** {reason}')
        await ctx.send(embed=embed)
        embed = self.build_embed(user=user, description=f'You were banned from {ctx.guild.name} by {ctx.author.name}\n\n**Reason:** {reason}')
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await user.send(embed=embed)

    @commands.command(name='unban', description='Unbans a user from a guild.', aliases=['un-ban'])
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    @mod_check('unban')
    async def _unban(self, ctx: CustomContext, user: discord.User, *, reason: CharLimit(char_limit=250)='None.'):
        await ctx.guild.unban(user=user, reason=reason)
        embed = self.build_embed(user=ctx.author, title='User un-banned.', description=f'{ctx.author.mention} un-banned {user.name}.\n\n**Reason:** {reason}')
        await ctx.send(embed=embed)
        embed = self.build_embed(user=user, description=f'You were banned from {ctx.guild.name} by {ctx.author.name}\n\n**Reason:** {reason}')
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await user.send(embed=embed)

    @commands.command(name='add-roles', description='Add roles to given members.')
    @commands.has_guild_permissions(administrator=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    async def add_roles(self, ctx: CustomContext, role: discord.Role, members: commands.Greedy[discord.Member], *, reason: CharLimit(char_limit=100)):
        if len(members) > 10:
            raise ProcessError('I can\'t add roles to more than 10 members at one time.')
        embed = self.build_embed(user=ctx.author, description=f'This process may take {len(members) * 2} seconds.')
        full = ''
        await ctx.send(embed=embed)
        for member in members:
            try:
                await member.add_roles(role, reason=reason)
                full += f'{member.name} - Success\n'
            except Exception as e:
                full += f'{member.name} - Failure. Reason: `{e}`'
            await asyncio.sleep(2)
        embed = self.build_embed(user=ctx.author, title='Process finished.', description=f'```{full}```')
        await ctx.send(embed=embed)

    @commands.command(name='mute', description='Mutes the selected member for selected time.')
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @mod_check('mute')
    async def _mute(self, ctx: CustomContext, member: discord.Member, time: TimeConvert, *, reason: CharLimit(char_limit=200)):
        role = await self.get_muted_role(ctx.guild)
        await member.add_roles(role, reason=reason)
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            mute_id = await self.insert_mute(conn, member, ctx.author, time)
        ends_at = discord.utils.format_dt(discord.utils.utcnow() + datetime.timedelta(seconds=time), style='F')
        embed = self.build_embed(user=ctx.author, title='Member muted.', description=f'{member.mention} was muted by {ctx.author}\n\n**Reason:** {reason}\n\n**Mute id:** {mute_id}\n\n**Ends at:** {ends_at}')
        await ctx.send(embed=embed)

        if time < 3600:
            await asyncio.sleep(time)
            async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
                await member.remove_roles(role, reason=f'Mute end.')
                await self.remove_mute(conn, mute_id, ctx.guild.id)
                await conn.close()

    @commands.command(name='unmute', description='Unmuted the selected member.', aliases=['un-mute'])
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_roles=True)
    @mod_check('unmute')
    async def unmute(self, ctx: CustomContext, member: discord.Member):
        pass

        
        

def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
