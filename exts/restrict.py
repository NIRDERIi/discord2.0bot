from asyncio.tasks import wait
import subprocess
import discord
from discord import embeds
from discord.ext import commands
from discord.utils import PY_310
from bot import Bot
from utility.converters import CodeCleanUp, ExtensionPath, SourceConvert
import asyncio
import aiohttp
import os
import datetime
import io
import textwrap
import contextlib
import traceback
from utility.buttons import ConfirmButtonBuild, Paginator
from utility.decorators import restrict
from utility.constants import Emojis
from utility.converters import SelfLib
import importlib
import contextlib
import utility
from bot import CustomContext
import git
from utility.constants import General
import inspect





class restrict(commands.Cog):
    """Test"""
    
    def __init__(self, bot: Bot) -> None:

        self.bot: Bot = bot
        self.eval_outputs: dict = {}

    async def cog_check(self, ctx: CustomContext):
        return ctx.author.id in self.bot.allowed_users

    @commands.command(name='libs-reload')
    async def libs_reload(self, ctx: CustomContext, *, lib_path: SelfLib()):
        embed = discord.Embed(description='', color=discord.Colour.blurple())
        if lib_path == '~':
            for file in os.listdir('utility'):
                if '__init__' in file or not file.endswith('.py'):
                    continue
                full_path_valid = f'utility.{file[:-3]}'
                embed.description += f'`{full_path_valid}` {Emojis.recycle()}\n'
                importlib.reload(eval(full_path_valid))
        else:
            importlib.reload(eval(lib_path))
            embed.description = f'{lib_path} {Emojis.recycle()}'
        await ctx.send(embed=embed)
                
        


    @commands.command(
        name="eval", description="Evaluates a python code.", usage="eval <code>"
    )
    @restrict()
    async def eval(self, ctx: CustomContext, *, code: CodeCleanUp):
        eval_env = {
            "bot": self.bot,
            "self": self,
            "ctx": ctx,
            "discord": discord,
            "commands": commands,
            "asyncio": asyncio,
            "aiohttp": aiohttp,
            "__name__": __name__,
            "os": os,
            "datetime": datetime,
            'importlib': importlib
        }
        stdout = io.StringIO()
        to_process = f"async def func():\n{textwrap.indent(code, '    ')}"
        try:
            with contextlib.redirect_stdout(stdout):
                exec(to_process, eval_env)
                obj = await eval_env["func"]()
                if not obj:
                    result = f"{stdout.getvalue()}"
                else:
                    result = f"{stdout.getvalue()}\n{obj}\n"
                if not result:
                    message_eval = await ctx.reply("None")
                    self.eval_outputs[ctx.message.id] = message_eval
                    return
                if not result and not obj:
                    message_eval = await ctx.reply("None")
                    self.eval_outputs[ctx.message.id] = message_eval
                    return
                if len(result) < 1900:
                    message_eval = await ctx.reply(result)
                    self.eval_outputs[ctx.message.id] = message_eval
                else:
                    f = open("NIR.txt", mode="w", encoding="utf-8")
                    f.write(result)
                    f.close()
                    message_eval = await ctx.reply(file=discord.File("NIR.txt"))
                    self.eval_outputs[ctx.message.id] = message_eval
                    os.remove("NIR.txt")
        except Exception as e:
            result = traceback.format_exception(type(e), e, e.__traceback__)
            result = "".join(result)
            embed = discord.Embed(description=f"```\n{result}\n```")
            message_eval = await ctx.reply(embed=embed)
            self.eval_outputs[ctx.message.id] = message_eval
        pass

    
    @commands.command()
    async def test(self, ctx: CustomContext):
        async def check(interaction: discord.Interaction):
            return interaction.user.id == ctx.author.id

        embeds = [discord.Embed(title='a'), discord.Embed(title='b'), discord.Embed(title='c')]
        paginator = Paginator(ctx=ctx, embeds=embeds, timeout=20.0, check=check)
        await paginator.run()

    @commands.command()
    async def reload(self, ctx: CustomContext, *, extension: ExtensionPath):
        embed = discord.Embed(description='', color=discord.Colour.blurple())
        if extension == '~':
            to_reload = [key[0] for key in self.bot.extensions.items()]
            for path in to_reload:
                embed.description += f'`{path}` {Emojis.recycle()}\n'
                self.bot.reload_extension(path)
        else:
            embed.description = f'`{extension}` {Emojis.recycle()}'
            self.bot.reload_extension(extension)
        await ctx.send(embed=embed)

    @commands.command()
    async def unload(self, ctx: CustomContext, *, extension: ExtensionPath):
        embed = discord.Embed(description='', color=discord.Colour.blurple())
        if extension == '~':
            to_unload = [key[0] for key in self.bot.extensions.items()]
            for path in to_unload:
                embed.description += f'`{path}` {Emojis.lock()}'
                self.bot.unload_extension(path)
        else:
            embed.description = f'`{extension}` {Emojis.lock()}'
            self.bot.unload_extension(extension)
        await ctx.send(embed=embed)

    @commands.command()
    async def paste(self, ctx: CustomContext, *, text):
        data = bytes(text, 'utf-8')
        async with self.bot._session.post('https://hastebin.com/documents', data=data) as r:
            res = await r.json()
            key = res['key']
            await ctx.send(f'https://hastebin.com/{key}')

    @commands.Cog.listener('on_message_edit')
    async def re_eval(self, before, after):
        if after.content.startswith('m!eval') and before.author.id in self.bot.allowed_users:
            with contextlib.suppress(KeyError, discord.HTTPException):
                await self.eval_outputs[after.id].delete()
            await self.bot.process_commands(after)

    
    @commands.group(name='git', invoke_without_command=True)
    async def git(self, ctx):
        await ctx.send('Specify correct command.')
    
    @git.command(name='pull')
    async def pull(self, ctx):
        is_up_to_date = False
        embed = discord.Embed(title='Git pull.', description='')
        git_commands = [['git', 'pull', General.GIT_REPO_LINK()]]
            
        for git_command in git_commands:
            process = await asyncio.create_subprocess_exec(
                git_command[0],
                *git_command[1: ],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            output, error = await process.communicate()
            embed.description += f'[{" ".join(git_command)!r} exited with return code {process.returncode}\n'

            if output:
                embed.description += f'[stdout]\n{output.decode()}\n'

                if output.decode().lower().lstrip().replace('\n', '') == 'already up to date.':
                    is_up_to_date = True
            if error:
                embed.description += f'[stderr]\n{error.decode()}\n'
        await ctx.send(embed=embed)
        if is_up_to_date:
            return
        await ctx.invoke(self.bot.get_command('libs-reload'), lib_path='~')
        await ctx.invoke(self.bot.get_command('reload'), extension='~')
    @git.command()
    async def push(self, ctx, *, reason='Code update.'):
        embed = discord.Embed(title='Git push.', description='')
        git_commands = [
            ['git', 'add', '.'],
            ['git', 'commit', '-m', reason],
            ['git', 'push', 'origin', 'master'],
        ]

        for git_command in git_commands:
            process = await asyncio.create_subprocess_exec(
                git_command[0],
                *git_command[1: ],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            output, error = await process.communicate()
            embed.description += f'[{" ".join(git_command)!r} exited with return code {process.returncode}\n'

            if output:
                embed.description += f'[stdout]\n{output.decode()}\n'
            if error:
                embed.description += f'[stderr]\n{error.decode()}\n'
        await ctx.send(embed=embed)


    @commands.command(name='source', aliases=['src'])
    async def source(self, ctx, *, source_item: SourceConvert):
        if isinstance(source_item, commands.Command):
            callback = source_item.callback
            lines = inspect.getsourcelines(callback)
            starting_line = lines[1]
            ending_line = len(lines[0]) - 1
            file = inspect.getsourcefile(callback)
            await ctx.send(file)
            await ctx.send(starting_line)
            await ctx.send(ending_line)
        pass

def setup(bot: Bot):
    bot.add_cog(restrict(bot=bot))
