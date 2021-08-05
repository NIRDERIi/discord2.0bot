import functools
from . import functions
from . import constants
from bot import CustomContext


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
