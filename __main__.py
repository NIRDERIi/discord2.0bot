import discord
from bot import Bot, get_prefix

bot = Bot(
    command_prefix=get_prefix,
    intents=discord.Intents.all(),
    help_command=None,
    max_messages=1500,
)
bot.run(bot.retrieve_token)
