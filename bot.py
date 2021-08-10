import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from utility.constants import Time
import typing
import importlib
import utility
import aiohttp
import asyncpg
import logging
from utility.logger import Log


BASIC_FORMAT = "%(asctime)s:%(levelname)s:%(name)s: %(message)s"
log = Log('logs.log').get_logger(__name__)


class LoggerHandler:
    def __init__(
        self,
        name="discord",
        filename="discord.log",
        encoding="utf-8",
        mode="w",
        format=BASIC_FORMAT,
    ):
        self.name = name
        self.filename = filename
        self.encoding = encoding
        self.mode = mode
        self.format = format

    def _start_handler(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(
            filename=self.filename, encoding=self.encoding, mode=self.mode
        )
        handler.setFormatter(logging.Formatter(self.format))
        logger.addHandler(hdlr=handler)


class CustomContext(commands.Context):
    async def send_confirm(
        self, *args, check: typing.Callable[..., bool] = None, **kwargs
    ):
        if not kwargs.get("view"):
            view = utility.buttons.ConfirmButtonBuild(
                timeout=Time.BASIC_TIMEOUT(), ctx=self, check=check
            )
            message = await self.send(*args, **kwargs, view=view)
            await view.wait()
            if view.value is None:
                raise utility.functions.ProcessError("Timed out!")

            return view, message
        else:
            return super().send(*args, **kwargs)


class Bot(commands.Bot):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.allowed_users = [480404983372709908]
        self.prefixes = {}
        self._session: typing.Optional[aiohttp.ClientSession] = None
        self.pool = self.loop.run_until_complete(
            asyncpg.create_pool(dsn=self.retrieve_dsn, min_size=1, max_size=5)
        )
        self.accept_events = True
        self.logs_webhooks = {}
        self.invalid_exts = []
        self.hidden_help_cogs = [
            "GeneralEvents",
            "HelpCommand",
            "Logs",
            "restrict"
        ]
        self.start_logger(
            name="discord",
            filename="discord.log",
            encoding="utf-8",
            mode="w",
            format=BASIC_FORMAT,
        )

    def start_logger(
        self,
        name="discord",
        filename="discord.log",
        encoding="utf-8",
        mode="w",
        format=BASIC_FORMAT,
    ):
        logger = LoggerHandler(
            name=name,
            filename=filename,
            encoding=encoding,
            mode=mode,
            format=format
        )
        logger._start_handler()

    async def get_context(self, message, *, cls=CustomContext):
        return await super().get_context(message, cls=cls)

    def get_message(self, id: int):

        return self._connection._get_message(id)

    def reload_extension(self, name, *, package=None):
        try:
            super().reload_extension(name, package=package)
            log.cog(f'Cog reloaded: {name} - package: {package}')
        except ImportError:
            for file in os.listdir("utility"):
                valid_file = f"utility.{file[:-3]}"
                importlib.reload(eval(valid_file))
                super().reload_extension(name, package=package)
                log.cog(f'Cog reloaded: {name} - package: {package}')
                

    def get_extensions_files(self, path: str, invalid_files: list = []):

        files = []
        for file in os.listdir(path):
            if file in invalid_files or not file.endswith(".py"):
                pass
            else:

                files.append(file[:-3])

        return path, files

    def load_extension(self, name, *, package=None):
        super().load_extension(name, package=package)
        log.cog(f'Extension loaded: {name} - package: {package}')
    
    def unload_extension(self, name, *, package=None):
        super().unload_extension(name, package=package)
        log.cog(f'Unloaded extension: {name} - package: {package}')

    def load_extensions(self):

        path, files = self.get_extensions_files(
            "exts",
            invalid_files=self.invalid_exts
        )
        for file in files:
            self.load_extension(f"{path}.{file}")
            print(f"Loaded {path}.{file}")

    @property
    def retrieve_token(self):

        load_dotenv()

        token_string = os.getenv("TOKEN")
        return token_string

    @property
    def retrieve_dsn(self):
        load_dotenv()
        dsn_string = os.getenv("DSN")
        return dsn_string

    def run(self, *args, **kwargs):
        self.load_extensions()
        super().run(*args, **kwargs)

    async def close(self):
        if self._session:
            await self._session.close()
        await super().close()
    
    async def login(self, *args, **kwargs):
        self._session = aiohttp.ClientSession()
        await super().login(*args, **kwargs)



async def get_prefix(bot: Bot, message: discord.Message):
    if not message.guild and message.author.id not in bot.allowed_users:
        return
    if message.guild.id not in bot.prefixes:
        async with bot.pool.acquire() as conn:
            data = await conn.fetch(
                """SELECT prefix FROM guilds_config WHERE guild_id = ($1)""",
                message.guild.id,
            )
        if not data:
            bot.prefixes[message.guild.id] = "m!"
        else:
            prefix = data[0]["prefix"]
            bot.prefixes[message.guild.id] = prefix
    return commands.when_mentioned_or(
        bot.prefixes.get(message.guild.id)
    )(bot, message)
