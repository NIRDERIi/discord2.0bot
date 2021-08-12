import pathlib
from utility import constants
from utility.functions import ProcessError, build_embed, basic_check
import discord
from discord.ext import commands
from bot import Bot
from utility.converters import CodeCleanUp, ExtensionPath, SourceConvert, BugInfo
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
from utility.constants import Emojis, Time
from utility.converters import SelfLib
import importlib
import contextlib
import utility
from bot import CustomContext
import git
from utility.constants import General
import inspect
import more_itertools
from utility.logger import Log

log = Log('logs.log').get_logger(__name__)




class restrict(commands.Cog):
    """Test"""

    def __init__(self, bot: Bot) -> None:

        self.bot: Bot = bot
        self.eval_outputs: dict = {}


    async def cog_check(self, ctx: CustomContext):
        return ctx.author.id in self.bot.allowed_users


    @commands.command(name="libs-reload")
    async def libs_reload(self, ctx: CustomContext, *, lib_path: SelfLib()):
        embed = discord.Embed(description="", color=discord.Colour.blurple())
        if lib_path == "~":
            for file in os.listdir("utility"):
                if "__init__" in file or not file.endswith(".py"):
                    continue
                full_path_valid = f"utility.{file[:-3]}"
                embed.description += f"`{full_path_valid}` {Emojis.recycle()}\n"
                importlib.reload(eval(full_path_valid))
        else:
            importlib.reload(eval(lib_path))
            embed.description = f"{lib_path} {Emojis.recycle()}"
        await ctx.send(embed=embed)

    @commands.command(
        name="eval", description="Evaluates a python code.", usage="eval <code>"
    )
    @restrict()
    async def eval(self, ctx: CustomContext, *, code: CodeCleanUp):
        async with self.bot.pool.acquire() as conn:
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
                "importlib": importlib,
                "__file__": __file__,
                'inspect': inspect,
                'pathlib': pathlib,
                'ProcessError': ProcessError,
                'constants': constants,
                'conn': conn
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
                log.error(str(e))
                result = traceback.format_exception(type(e), e, e.__traceback__)
                result = "".join(result)
                embed = discord.Embed(description=f"```\n{result}\n```")
                message_eval = await ctx.reply(embed=embed)
                self.eval_outputs[ctx.message.id] = message_eval
            pass


    @commands.command()
    async def reload(self, ctx: CustomContext, *, extension: ExtensionPath):
        embed = discord.Embed(description="", color=discord.Colour.blurple())
        if extension == "~":
            to_reload = [key[0] for key in self.bot.extensions.items()]
            for path in to_reload:
                embed.description += f"`{path}` {Emojis.recycle()}\n"
                self.bot.reload_extension(path)
        else:
            embed.description = f"`{extension}` {Emojis.recycle()}"
            self.bot.reload_extension(extension)
        await ctx.send(embed=embed)

    @commands.command()
    async def unload(self, ctx: CustomContext, *, extension: ExtensionPath):
        embed = discord.Embed(description="", color=discord.Colour.blurple())
        if extension == "~":
            to_unload = [key[0] for key in self.bot.extensions.items()]
            for path in to_unload:
                embed.description += f"`{path}` {Emojis.lock()}"
                self.bot.unload_extension(path)
        else:
            embed.description = f"`{extension}` {Emojis.lock()}"
            self.bot.unload_extension(extension)
        await ctx.send(embed=embed)

    @commands.command()
    async def paste(self, ctx: CustomContext, *, text):
        data = bytes(text, "utf-8")
        async with self.bot._session.post(
            "https://hastebin.com/documents", data=data
        ) as r:
            res = await r.json()
            key = res["key"]
            await ctx.send(f"https://hastebin.com/{key}")

    @commands.Cog.listener("on_message_edit")
    async def re_eval(self, before, after):
        if (
            after.content.startswith("m!eval")
            and before.author.id in self.bot.allowed_users
        ):
            with contextlib.suppress(KeyError, discord.HTTPException):
                await self.eval_outputs[after.id].delete()
            await self.bot.process_commands(after)

    @commands.group(name="git", invoke_without_command=True)
    async def git(self, ctx):
        await ctx.send("Specify correct command.")

    @git.command(name="pull")
    async def pull(self, ctx):
        is_up_to_date = False
        embed = discord.Embed(title="Git pull.", description="")
        git_commands = [["git", "pull", General.GIT_REPO_LINK()]]

        for git_command in git_commands:
            process = await asyncio.create_subprocess_exec(
                git_command[0],
                *git_command[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            output, error = await process.communicate()
            embed.description += f'[{" ".join(git_command)!r} exited with return code {process.returncode}\n'

            if output:
                embed.description += f"[stdout]\n{output.decode()}\n"

                if (
                    output.decode().lower().lstrip().replace("\n", "")
                    == "already up to date."
                ):
                    is_up_to_date = True
            if error:
                embed.description += f"[stderr]\n{error.decode()}\n"
        await ctx.send(embed=embed)
        if is_up_to_date:
            return
        await ctx.invoke(self.bot.get_command("libs-reload"), lib_path="~")
        await ctx.invoke(self.bot.get_command("reload"), extension="~")

    @git.command()
    async def push(self, ctx, *, reason="Code update."):
        embed = discord.Embed(title="Git push.", description="")
        git_commands = [
            ["git", "add", "."],
            ["git", "commit", "-m", reason],
            ["git", "push", "origin", "master"],
        ]

        for git_command in git_commands:
            process = await asyncio.create_subprocess_exec(
                git_command[0],
                *git_command[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            output, error = await process.communicate()
            embed.description += f'[{" ".join(git_command)!r} exited with return code {process.returncode}\n'

            if output:
                embed.description += f"[stdout]\n{output.decode()}\n"
            if error:
                embed.description += f"[stderr]\n{error.decode()}\n"
        await ctx.send(embed=embed)

    @commands.command(
        name="source",
        aliases=["src"],
    )
    async def source(self, ctx: CustomContext, *, source_item: SourceConvert=None):
        if not source_item:
            source_item = {'Repository': General.REPO_LINK()}
        embed = discord.Embed(description='')
        for key, value in source_item.items():
            embed.description += f'[{key}]({value})\n'
        await ctx.send(embed=embed)


    @commands.command()
    async def bugs(self, ctx: CustomContext):
        async def check(interaction: discord.Interaction):
            return interaction.user.id == ctx.author.id
        paginator = Paginator(ctx=ctx, embeds=[], timeout=Time.BASIC_TIMEOUT(), check=check)
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:

            data = await conn.fetch('''SELECT * FROM bugs''')
        if not data:
            return await ctx.send(embed=build_embed(title='No bugs.', description='There are no system bugs.'))
        iterable = more_itertools.sliced(seq=data, n=4)
        lst = [i for i in iterable]
        for outer_lst in lst:
            embed = discord.Embed(title='System bugs.', color=discord.Colour.blurple())
            for record in outer_lst:
                bug_id = record.get('bug_id') or 'None'
                short_error = record.get('short_error') or 'None fetched properly.'
                embed.add_field(name=f'ID {bug_id}', value=short_error, inline=False)
            paginator.add_embed(embed=embed)
        await paginator.run()

    @commands.command()
    async def bug(self, ctx: CustomContext, bug_id: BugInfo):
        bugid, guild_name, user_name, short_error, full_traceback_link, time_string = bug_id
        embed = discord.Embed(title=f'Bug info.', color=discord.Colour.blurple())
        embed.add_field(name='Bug ID', value=f'`{bugid}`', inline=False)
        embed.add_field(name='Guild name.', value=f'{guild_name}', inline=False)
        embed.add_field(name='User name.', value=f'{user_name}', inline=False)
        embed.add_field(name='Short error.', value=short_error, inline=False)
        embed.add_field(name='Error.', value=f'[FULL TRACEBACK]({full_traceback_link})', inline=False)
        embed.add_field(name='Errored.', value=f'`{time_string} ago.`')
        await ctx.send(embed=embed)


    @commands.command()
    async def fix(self, ctx: CustomContext, bug_id: int):
        async def check(interaction: discord.Interaction):
            return ctx.author.id in self.bot.allowed_users
        async with self.bot.pool.acquire() as conn:
            data = await conn.fetch('''SELECT * FROM bugs WHERE bug_id = ($1)''', bug_id)
            if not data:
                raise ProcessError(f'Bug with the id of {bug_id} was not found.')
            
            embed = discord.Embed(title='Confirm.', description=f'Are you sure you want to fix bug {bug_id}', color=discord.Colour.blurple())
            view, message = await ctx.send_confirm(embed=embed, check=check)
            if not view.value:
                return await ctx.send(embed=build_embed(title='Process aborted.'))
            await conn.execute('''DELETE FROM bugs WHERE bug_id = ($1)''', bug_id)
        await ctx.send(embed=build_embed(title='Bug deleted.', description=f'Bug with the id of {bug_id} was deleted.'))
        user = ctx.guild.get_member(data[0]['user_id']) or self.bot.get_user(data[0]['user_id']) or None
        if not user:
            return
        with contextlib.suppress(discord.HTTPException, discord.Forbidden):
            await user.send(embed=build_embed(title='Bug solved.', description=f'The bug you reported with the id of {bug_id} was solved!\nThank you for helping us make the bot better!'))





def setup(bot: Bot):
    bot.add_cog(restrict(bot=bot))
