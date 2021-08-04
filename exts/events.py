import discord
from discord.ext import commands
from discord.ext.commands import cog
from bot import Bot, CustomContext
import typing
from utility.decorators import events


class GeneralEvents(commands.Cog):

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.Cog.listener(name='on_connect')
    @events()
    async def on_connect(self):
        print('Client has successfully connected to Discord.')

    @commands.Cog.listener(name='on_shard_connect')
    @events()
    async def on_shard_connect(self, shard_id: typing.Optional[int]):
        print(f'A particular shard ID ({shard_id}) has connected to Discord.')

    @commands.Cog.listener(name='on_disconnect')
    @events()
    async def on_disconnect(self):
        print('Client has disconnected from Discord, or a connection attempt to Discord has failed.')

    @commands.Cog.listener(name='on_shard_disconnect')
    @events()
    async def on_shard_disconnect(self, shard_id: typing.Optional[int]):
        print(f'A particular shard ID ({shard_id}) has disconnected from Discord.')

    @commands.Cog.listener(name='on_ready')
    @events()
    async def on_ready(self):
        print('Client is done preparing the data received from Discord.')

    @commands.Cog.listener(name='on_shard_ready')
    @events()
    async def on_shard_ready(self, shard_id: typing.Optional[int]):
        print(f'A particular shard ID ({shard_id}) has become ready.')
    
    @commands.Cog.listener(name='on_resumed')
    @events()
    async def on_resumed(self):
        print('Client has resumed a session.')

    @commands.Cog.listener(name='on_shard_resumed')
    @events()
    async def on_shard_resumed(self, shard_id: typing.Optional[int]):
        print(f'A particular shard ID ({shard_id}) has resumed a session.')

    

    

def setup(bot: Bot):
    bot.add_cog(GeneralEvents(bot))