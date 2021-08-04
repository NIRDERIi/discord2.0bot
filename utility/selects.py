import discord
from discord.ext import commands
import typing
from . import functions
from bot import CustomContext

class HelpCommandView(discord.ui.View):
    def __init__(self, *, timeout: typing.Optional[float], ctx: CustomContext):
        self.ctx = ctx
        self.bot = self.ctx.bot
        super().__init__(timeout=timeout)
        item = HelpCommandSelect(ctx=self.ctx, view=self)
        for cog_name, cog_object in self.bot.cogs.items():
            item.add_option(label=cog_name, description=cog_object.__doc__)
        self.add_item(item=item)

    async def on_timeout(self) -> None:
        try:
            self.stop()
        except Exception as e:
            pass
        return await super().on_timeout()


class HelpCommandSelect(discord.ui.Select):
    def __init__(self, *args, ctx: CustomContext, view: HelpCommandView, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ctx = ctx
        self._inner_view = view

    async def callback(self, interaction: discord.Interaction):
        cog_selected = self.values[0]
        try:
            self._inner_view.stop()
            await interaction.response.defer(ephemeral=False)
        except Exception as e:
            pass
        await functions.start_cog_help(self.ctx, cog_selected)        
        return await super().callback(interaction)