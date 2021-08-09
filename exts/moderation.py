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
        embed = discord.Embed(**kwargs, timestamp=discord.utils.utcnow(), color=discord.Colour.green())
        embed.set_footer(icon_url=user.avatar.url)
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
        embed = self.build_embed(user=member, description=f'You were kicked out from {ctx.guild.name} by {ctx.author.name}\n\n*8Reason:** {reason}')
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await member.send(embed=embed)

def setup(bot: Bot):
    bot.add_cog(Moderation(bot))
