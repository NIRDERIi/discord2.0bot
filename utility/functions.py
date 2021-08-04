from bot import CustomContext
import typing
import discord
from discord.ext import commands
import more_itertools
from . import buttons
import datetime
#from bot import CustomContext

class ProcessError(commands.CommandInvokeError):
    pass

async def start_cog_help(ctx, cog_name: str):
    async def check(interaction):
        return interaction.user.id == ctx.author.id
    cog = ctx.bot.get_cog(cog_name)
    cog_commands_iterable = cog.walk_commands()
    cog_commands = [command for command in cog_commands_iterable]
    lst = more_itertools.sliced(cog_commands, 4)
    embeds = []
    for outer_lst in lst:
        embed = discord.Embed(title=f'{cog_name} commands!', color=discord.Colour.blurple())
        for command in outer_lst:
            
            embed.add_field(name=f'{command.qualified_name} {command.signature}', value=command.description or 'None provided.', inline=False)
        embeds.append(embed)
    paginator = buttons.Paginator(ctx=ctx, embeds=embeds, timeout=20.0, check=check)
    await paginator.run()


def build_embed(title: typing.Optional[str]=None, description: typing.Optional[str]=None, timestamp: typing.Optional[datetime.datetime]=None):
    embed = discord.Embed(title=title or '', description=description or '', color=discord.Colour.blurple(), timestamp=timestamp)
    return embed

async def basic_check(ctx: CustomContext, interaction: discord.Interaction):
    return ctx.author.id == interaction.user.id

async def basic_guild_check(ctx: CustomContext, interaction: discord.Interaction):
    return ctx.author.guild_permissions.administrator