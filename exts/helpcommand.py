import discord
from discord.ext import commands
from discord.role import RoleTags
from utility.selects import HelpCommandView
from utility.functions import start_cog_help
import typing
from utility.converters import CommandInfo
from bot import Bot, CustomContext


class HelpCommand(commands.Cog):

    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        

    @commands.group(name='help', invoke_without_command=True)
    async def help(self, ctx: CustomContext, *, command_name: typing.Optional[CommandInfo]):

        if command_name:
            aliases, cog_name, description, qualified_name, signature = command_name
            embed = discord.Embed(description=f'**Description: ** `{description or "None"}`\n\n**Category\extension:** `{cog_name}`\n\n**Usage: ** `{qualified_name} {signature}`\n\n**Aliases: **{", ".join([f"`{alias}`" for alias in aliases]) or "No aliases"}')
            await ctx.send(embed=embed)
            return
        embed = discord.Embed(title='Select the category/extension to get help for!', color=discord.Colour.blurple())
        try:
            await ctx.send(embed=embed, view=HelpCommandView(timeout=20.0, ctx=ctx))
        except discord.NotFound as e:
            print('errorr')
            print(e)
            pass
        return



def setup(bot: Bot):
    bot.add_cog(HelpCommand(bot))