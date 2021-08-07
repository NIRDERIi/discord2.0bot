from bot import CustomContext
import typing
import discord
from discord.ext import commands
import more_itertools
from . import buttons
import datetime
import os
import difflib
from bot import CustomContext, Bot

BIN_LINK = 'https://hastebin.com/documents'
BIN_LINK_FORMAT = 'https://hastebin.com/{}'


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
        embed = discord.Embed(
            title=f"{cog_name} commands!", color=discord.Colour.blurple()
        )
        for command in outer_lst:

            embed.add_field(
                name=f"{command.qualified_name} {command.signature}",
                value=command.description or "None provided.",
                inline=False,
            )
        embeds.append(embed)
    paginator = buttons.Paginator(ctx=ctx, embeds=embeds, timeout=20.0, check=check)
    await paginator.run()


def build_embed(
    title: typing.Optional[str] = None,
    description: typing.Optional[str] = None,
    timestamp: typing.Optional[datetime.datetime] = None,
):
    embed = discord.Embed(
        title=title or "",
        description=description or "",
        color=discord.Colour.blurple(),
        timestamp=timestamp,
    )
    return embed


async def basic_check(ctx: CustomContext, interaction: discord.Interaction):
    return ctx.author.id == interaction.user.id


async def basic_guild_check(ctx: CustomContext, interaction: discord.Interaction):
    return ctx.author.guild_permissions.administrator


def find_path(file: str):
    if os.path.isdir(file):
        return None
    invalid = [
        "discord.log",
        "__init__.py",
        ".env",
    ]
    invalid2 = ["discord", "__init__", ".env"]
    if (
        file in invalid
        or file[:-3] in invalid
        or file in invalid2
        or file[:-3] in invalid2
    ):
        raise ProcessError("These files are restricted.")
    final_path = None
    if file in [i[:-3] for i in os.listdir()] or file in os.listdir():
        final_path = file is file.endswith(".py") or f"{file}.py"

    if file in [i[:-3] for i in os.listdir("utility")]:
        final_path = file if file.endswith(".py") else f"utility/{file}.py"

    if file in [i[:-3] for i in os.listdir("exts")]:
        final_path = file if file.endswith(".py") else f"exts/{file}.py"
    return final_path



def get_divmod(seconds: int):
    days, hours = divmod(seconds, 86400)
    hours, minutes = divmod(hours, 3600)
    minutes, seconds = divmod(minutes, 60)
    days, hours, minutes, seconds = round(days), round(hours), round(minutes), round(seconds)
    return days, hours, minutes, seconds


async def error_pastebin(bot: Bot, text: str):

    data = bytes(str(text), encoding='utf-8')
    async with bot._session.post(url=BIN_LINK, data=data) as raw_response:
        response = await raw_response.json(content_type=None)
        key = response['key']
        return BIN_LINK_FORMAT.format(key)