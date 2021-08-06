from utility.functions import ProcessError, find_path
import discord
from discord.ext import commands
from . import constants
import os
from bot import CustomContext
import typing
import inspect
import pathlib
import importlib


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


class SourceConvert(commands.Converter):
    async def convert(self, ctx: CustomContext, argument: str):
        options = {}
        if ctx.bot.get_command(argument):
            source_item: commands.Command = ctx.bot.get_command(argument)
            callback = source_item.callback
            lines = inspect.getsourcelines(callback)
            starting_line = lines[1]
            ending_line = len(lines[0]) + starting_line - 1
            file = inspect.getsourcefile(callback)
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



        raise ProcessError(f"Could not convert {argument} to a valid cog, class or command.")
