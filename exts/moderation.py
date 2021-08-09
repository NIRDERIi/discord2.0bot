import discord
from discord.ext import commands
from bot import Bot, CustomContext
from utility.constants import Time
from utility.functions import ProcessError
import typing
from utility.decorators import mod_check
from utility.converters import CharLimit
import contextlib


class Moderation(commands.Cog):
    
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    def build_embed(self, user: typing.Union[discord.Member, discord.User], **kwargs):
        embed = discord.Embed(**kwargs, color=discord.Colour.green())
        text = f'Today at {discord.utils.utcnow().strftime("%H:%M %p")}'
        embed.set_footer(text=text, icon_url=user.avatar.url)
        return embed

        
        

    async def get_muted_role(self, guild: discord.Guild):

        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:

            data = await conn.fetch('''SELECT muted_role FROM guilds_config WHERE guild_id = ($1)''', guild.id)
            if not data:
                raise ProcessError('This guild didn\'t set muted role.')
            muted_role_id = data[0]['muted_role']
            role = guild.get_role(muted_role_id)
            if not role:
                raise ProcessError('This guild set muted role, but it was deleted.')
            return role

    @commands.command(name='kick', description='Kicks a member from a guild.')
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    @mod_check('kick')
    async def _kick(self, ctx: CustomContext, member: discord.Member, *, reason: CharLimit(char_limit=200) = 'None.'):
        await member.kick(reason=reason)
        embed = self.build_embed(title='Member kicked.', description=f'{ctx.author.mention} kicked {member.name}.\n\n**Reason:** {reason}', user=ctx.author)
        await ctx.send(embed=embed)
        embed = self.build_embed(user=member, description=f'You were kicked out from {ctx.guild.name} by {ctx.author.name}\n\n**Reason:** {reason}')
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await member.send(embed=embed)

    @commands.command(name='ban', description='bans a member from a guild.')
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


def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
