import datetime
from discord import guild
from utility.functions import ProcessError, build_embed, find_path, error_pastebin, get_divmod
import discord
from discord.ext import commands
from . import constants
import os
from bot import Bot, CustomContext
import typing
import inspect
import pathlib
import importlib
from . import constants

class CodeCleanUp(commands.Converter):
    async def convert(self, ctx: CustomContext, arg: str) -> str:

        if arg.startswith("```py") and arg.endswith("```"):

            arg = arg[5:-3]

        return arg


class ExtensionPath(commands.Converter):
    async def convert(self, ctx: CustomContext, argument: str):

        argument = argument.lower()
        if argument == "~":
            return argument
        for key, value in ctx.bot.extensions.items():
            key = key.lower()
            name = key.split(".")[-1]
            if name.lower() == argument:
                full_path = key
                return full_path

        raise ProcessError(constants.Messages.UNKNOWN_EXTENSION())


class SelfLib(commands.Converter):
    def __init__(self, directory="utility"):
        self.directory = directory

    async def convert(self, ctx: CustomContext, argument: str):
        if argument == "~":
            return argument
        argument = argument.lower()
        if argument.lower() not in [
            file.lower() for file in os.listdir(self.directory)
        ]:
            raise ProcessError(constants.Messages.UNKNOWN_SELFLIB().format(argument))
        return f"{self.directory}.{argument}"


class CommandInfo(commands.Converter):
    async def convert(self, ctx: CustomContext, argument: str):

        command = ctx.bot.get_command(argument.lower())
        if not command:
            raise ProcessError(f"Command {argument} was nt found.")
        if command.hidden and ctx.author.id not in ctx.bot.allowed_users:
            raise ProcessError(f"You are not authorize to see this command help.")
        aliases, cog_name, description, qualified_name, signature = (
            command.aliases,
            command.cog_name,
            command.description,
            command.qualified_name,
            command.signature,
        )
        return aliases, cog_name, description, qualified_name, signature


class CharLimit(commands.Converter):
    def __init__(self, char_limit: typing.Optional[int]):
        self.char_limit = char_limit

    async def convert(self, ctx: CustomContext, argument: str):

        if not self.char_limit:
            return argument
        if len(argument) > self.char_limit:

            raise ProcessError(f"You exceeded the char limit `{self.char_limit}`")
        return argument


class SourceConvert(commands.Converter):
    async def convert(self, ctx: CustomContext, argument: str):
        options = {}
        if ctx.bot.get_command(argument):
            source_item: commands.Command = ctx.bot.get_command(argument)
            print(source_item.name)
            print(source_item.cog_name)
            callback = source_item.callback
            lines = inspect.getsourcelines(callback)
            starting_line = lines[1]
            ending_line = len(lines[0]) + starting_line - 1
            file = inspect.getsourcefile(inspect.unwrap(callback))
            print(file)
            file_path_lst = file.split("\\")
            if "exts" in file_path_lst:
                source_path = "/".join(file_path_lst[file_path_lst.index("exts") :])
            elif "utility" in file_path_lst:
                source_path = "/".join(file_path_lst[file_path_lst.index("utility") :])
            full_link = f"{constants.General.REPO_LINK()}/blob/master/{source_path}#L{starting_line}-L{ending_line}"
            options[source_item.qualified_name] = full_link
        elif find_path(argument):
            source_item = find_path(argument)
            lst = source_item.split(".")
            last_data = ".".join(lst[-2:])
            first_data = "/".join(lst[:-2])
            source_item = f"{first_data}/{last_data}"
            full_link = f"<{constants.General.REPO_LINK()}/blob/master/{source_item}>"
            options[source_item] = full_link
        else:
            modules = []
            all_classes = []
            for module in pathlib.Path().glob('**/*.py'):
                if module.name != pathlib.Path(__file__).name:
                    modules.append(importlib.import_module('.'.join(module.parts)[:-3]))
            for module in modules:
                for name, _class in inspect.getmembers(module, inspect.isclass):
                    if name == argument:
                        all_classes.append(_class)
                for name, _functions in inspect.getmembers(module, inspect.isfunction):
                    if name == argument:
                        all_classes.append(_functions)
            if not all_classes:
                raise ProcessError(f"Could not convert {argument} to a valid cog, class or command.")
            all_classes = list(set(all_classes))
            for _class in all_classes:
                file_path = inspect.getsourcefile(_class)
                file_path = file_path.replace('\\', '/')
                file_path_lst = file_path.split("/")
                if file_path_lst[-1] in os.listdir():
                    source_path = file_path_lst[-1]
                elif file_path_lst[-1] in os.listdir('exts'):
                    source_path = f'exts/{file_path_lst[-1]}'
                elif file_path_lst[-1] in os.listdir("utility"):
                    source_path = f'utility/{file_path_lst[-1]}'
                else:
                    raise ProcessError('Unkown error while fetching the correct place.')
                lines = inspect.getsourcelines(_class)
                starting_line = lines[1]
                ending_line = len(lines[0]) + starting_line - 1
                full_link = f'{constants.General.REPO_LINK()}/blob/master/{source_path}#L{starting_line}-L{ending_line}'
                options[argument] = full_link

        if not options:
            raise ProcessError('Unkown error while fetching the correct place.')
        else:
            return options



class BugInfo(commands.Converter):

    async def convert(self, ctx: CustomContext, argument: str) -> typing.List[str]:
        bot: Bot = ctx.bot
        if not argument.isdigit():
            raise ProcessError('Bug id must be an integer.')
        argument = int(argument)
        async with bot.pool.acquire(timeout=constants.Time.BASIC_DBS_TIMEOUT()) as conn:
            data = await conn.fetch('''SELECT * FROM bugs WHERE bug_id = ($1)''', argument)
        if not data:
            raise ProcessError(f'Bug with the id of {argument} was not found.')
        record = data[0]
        bug_id = argument
        guild_name = bot.get_guild(record['guild_id']) or 'Couldn\'t fetch.'
        user_name = bot.get_user(record['user_id']) or 'Couldn\'t fetch.'
        short_error = record['short_error'] or 'Couldn\'t fetch.'
        full_traceback_link = await error_pastebin(bot, record['full_traceback'])
        days, hours, minutes, seconds = get_divmod((datetime.datetime.utcnow() - record['error_time']).total_seconds())
        time_string = f'{days}d, {hours}h, {minutes}m, {seconds}s'
        return bug_id, guild_name, user_name, short_error, full_traceback_link, time_string



'''
        formatted_text = '-\n'.join([i for i in [i for i in more_itertools.sliced(text, 158)]])
        data = bytes(formatted_text, 'utf-8')
        async with self.bot._session.post(self.bin_link, data=data) as raw_response:
            response = await raw_response.json()
            key = response['key']
            return self.bin_link_format.format(key)
'''