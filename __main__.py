import discord
import asyncpg
from bot import Bot, get_prefix
import logging

bot = Bot(command_prefix=get_prefix, intents=discord.Intents.all(), help_command=None, max_messages=1500)



bot.run(bot.retrieve_token)