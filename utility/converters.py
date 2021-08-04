from utility.functions import ProcessError
import discord
from discord.ext import commands
from . import constants
import os
from bot import CustomContext
import typing


class CodeCleanUp(commands.Converter):

    async def convert(self, ctX: CustomContext, arg: str) -> str:

        if arg.startswith('```py') and arg.endswith('```'):

            arg = arg[5:-3]

        return arg


class ExtensionPath(commands.Converter):

    async def convert(self, ctx: CustomContext, argument: str):

        argument = argument.lower()
        if argument == '~':
            return argument
        for key, value in ctx.bot.extensions.items():
            key = key.lower()
            name = key.split('.')[-1]
            if name.lower() == argument:
                full_path = key
                return full_path

        raise ProcessError(constants.Messages.UNKNOWN_EXTENSION())


class SelfLib(commands.Converter):

    def __init__(self, directory='utility'):
        self.directory = directory

    async def convert(self, ctx: CustomContext, argument: str):
        if argument == '~':
            return argument
        argument = argument.lower()
        if argument.lower() not in [file.lower() for file in os.listdir(self.directory)]:
            raise ProcessError(constants.Messages.UNKNOWN_SELFLIB().format(argument))
        return f'{self.directory}.{argument}'



class CommandInfo(commands.Converter):

    async def convert(self, ctx: CustomContext, argument: str):
        
        command = ctx.bot.get_command(argument.lower())
        if not command:
            raise ProcessError(f'Command {argument} was nt found.')
        if command.hidden and ctx.author.id not in ctx.bot.allowed_users:
            raise ProcessError(f'You are not authorize to see this command help.')
        aliases, cog_name, description, qualified_name, signature = command.aliases, command.cog_name, command.description, command.qualified_name, command.signature
        return aliases, cog_name, description, qualified_name, signature


class CharLimit(commands.Converter):

    def __init__(self, char_limit: typing.Optional[int]):
        self.char_limit = char_limit

    async def convert(self, ctx: CustomContext, argument: str):

        if not self.char_limit:
            return argument
        if len(argument) > self.char_limit:

            raise ProcessError(f'You exceeded the char limit `{self.char_limit}`')


class SourceConvert(commands.Converter):

    async def convert(self, ctx: CustomContext, argument: str):
        command = ctx.bot.get_command(argument)
        if command:
            return command
        cog = ctx.bot.get_cog(argument)
        if cog:
            return cog
        raise ProcessError(f'Could not convert {argument} to a valid cog or command.')