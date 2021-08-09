import discord
import functools
import typing
from . import functions
from utility.functions import ProcessError
from . import constants
from bot import CustomContext, Bot


def restrict():
    def wrapper(func):
        @functools.wraps(func)
        async def restricter(*args, **kwargs):
            self = args[0]
            ctx: CustomContext = args[1]
            if ctx.author.id not in self.bot.allowed_users:
                raise functions.ProcessError(
                    constants.Messages.BASIC_UNAUTHORIZED_MESSAGE()
                )
            return await func(*args, **kwargs)

        return restricter

    return wrapper


def events():
    def wrapper(func):
        @functools.wraps(func)
        async def event_accept_check(*args, **kwargs):
            self = args[0]
            if self.bot.accept_events:
                return await func(*args, **kwargs)

        return event_accept_check

    return wrapper


def mod_check(action):
    def wrapper(func):
        @functools.wraps(func)
        async def checker(*args, **kwargs):
            print(f'mod check {action}')
            self = args[0]
            ctx: CustomContext = args[1]
            member: typing.Union[discord.Member, discord.User] = args[2]
            if ctx.author.id == ctx.guild.owner.id:
                return await func(*args, **kwargs)
            elif isinstance(member, discord.User):
                return await func(*args, **kwargs)
            elif ctx.author.top_role < member.top_role:
                raise ProcessError('You must be in higher role than member to perform this action.')
            elif member.guild_permissions.administrator:
                raise ProcessError(f'I can\'t {action} an admin.')
            elif member.top_role >= ctx.guild.me.top_role:
                raise ProcessError(f'I can\'t {action} a member with higher/equal role as me.')
            elif member.id == ctx.author.id:
                raise ProcessError(f'You can\'t {action} yourself.')
            return await func(*args, **kwargs)
        return checker
    return wrapper