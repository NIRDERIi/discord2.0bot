import datetime
from utility.functions import ProcessError
import discord
from discord.ext import commands
from bot import Bot, CustomContext
from utility.converters import CharLimit
from utility.buttons import Paginator


class Fun(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bad_status = "Couldn\'t fetch data, returned status: {status}"
        self.not_found = "Couldn\'t find any mathces to: {query}"
        self.stackoverflow_url = 'https://api.stackexchange.com/2.2/search/advanced'
        self.realpython_url = 'https://realpython.com/search/api/v1/?'
        self.realpython_basic_url = 'https://realpython.com/{url}'

    @commands.command(name='stackoverflow', description='Shows top 3 resultes on stackoverflow.', aliases=['so'])
    async def stackoverflow(self, ctx: CustomContext, *, query: CharLimit(char_limit=100)):
        params = {"order": "desc","sort": "activity","site": "stackoverflow", 'q': query}
        async with self.bot._session.get(url=self.stackoverflow_url, params=params) as response:
            if response.status != 200:
                raise ProcessError(self.bad_status(status=response.status))
            data = await response.json(encoding='utf-8', content_type=None)
        if not data.get('items'):
            raise ProcessError(self.not_found.format(query=query))
        top3 = data['items'][:3]
        embeds = []
        for data in top3:
            tags = ', '.join([f'`{tag}`' for tag in data.get('tags')])
            was_answered = data.get('is_answered')
            last_activity_unixtime = data.get('last_activity_date')
            last_activity = f'<t:{last_activity_unixtime}:F>'
            created_at_unixtime = data.get('creation_date')
            created_at = f'<t:{created_at_unixtime}:F>'
            link = data.get('link')
            owner = data.get('owner')
            username = owner.get('display_name')
            owner_link = owner.get('link')
            profile_image = owner.get('profile_image')
            title = data.get('title')
            description = f'**Tags:** {tags}\n\n**Answered:** {was_answered}\n\n**Last activity:** {last_activity}\n\n**Created at:** {created_at}\n\n**Link:** [Link]({link})'
            embed = discord.Embed(title=title, description=description, color=discord.Colour.blurple())
            embed.set_author(name=username, url=owner_link, icon_url=profile_image)
            embeds.append(embed)
        if not embeds:
            raise ProcessError(f'Search result were empty for some reason.')
        async def check(interaction: discord.Interaction):
            return interaction.user.id == ctx.author.id
        paginator = Paginator(ctx=ctx, embeds=embeds, timeout=20.0, check=check)
        await paginator.run()
    
    @commands.command(name='realpython', description='Shows top 3 results from realpython.', aliases=['realp'])
    async def realpython(self, ctx: CustomContext, *, query: CharLimit(char_limit=100)):
        params = {'q': query, 'limit': 3}
        async with self.bot._session.get(url=self.realpython_url, params=params) as response:
            if response.status != 200:
                raise ProcessError(self.bad_status.format(status=response.status))
            data = await response.json(encoding='utf-8', content_type=None)
            if not data.get('results'):
                raise ProcessError(self.not_found.format(query=query))
            embeds = []
            for project in data.get('results'):
                kind = project.get('kind')
                title = project.get('title')
                project_description = project.get('description')
                full_link = self.realpython_basic_url.format(url=project.get('url'))
                publish_date = discord.utils.format_dt(datetime.datetime.fromisoformat(project.get('pub_date')))
                image_url = project.get('image_url')
                categories = ', '.join([f'`{category}`' for category in project.get('categories')])
                description = f'**Description:** {project_description}\n\n**Kind:** {kind}\n\n**Link:** ({full_link})\n\n**Publish date:** {publish_date}\n\n**Categories:** {categories}'
                embed = discord.Embed(title=title, description=description)
                embed.set_image(url=image_url)
                embeds.append(embed)
            if not embed:
                raise ProcessError(self.not_found(query=query))
            async def check(interaction: discord.Interaction):
                return interaction.user.id == ctx.author.id
            paginator = Paginator(ctx=ctx, embeds=embeds, timeout=20.0, check=check)
            await paginator.run()



def setup(bot: Bot):
    bot.add_cog(Fun(bot))