import datetime
from utility.functions import ProcessError
import discord
from discord.ext import commands
from bot import Bot, CustomContext
from utility.converters import CharLimit
from utility.buttons import Paginator
from dateutil.parser import parse
from utility.constants import General
import more_itertools


class Fun(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bad_status = "Couldn\'t fetch data, returned status: {status}"
        self.not_found = "Couldn\'t find any mathces to: {query}"
        self.stackoverflow_url = 'https://api.stackexchange.com/2.2/search/advanced'
        self.realpython_url = 'https://realpython.com/search/api/v1/?'
        self.realpython_basic_url = 'https://realpython.com{url}'
        self.github_api = 'https://api.github.com'
        self.lyrics_api = 'https://some-random-api.ml/lyrics?title={title}'

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
                publish_date = 'Not found.'
                if project.get('pub_date'):
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

    @commands.command(name='github-user', description='Shows info about github user.')
    async def github_user(self, ctx: CustomContext, *, name: CharLimit(char_limit=50)):
        async with self.bot._session.get(url=f'{self.github_api}/users/{name}') as response:
            if response.status != 200:
                raise ProcessError(self.bad_status.format(status=response.status))
            data = await response.json(content_type=None)
        login = data.get('login')
        user_id = data.get('id')
        avatar_url = data.get('avatar_url')
        url = data.get('html_url')
        email = data.get('email') or 'None.'
        bio = data.get('bio') or 'None.'
        repos = data.get('public_repos')
        gists = data.get('public_gists')
        followers = data.get('followers')
        following = data.get('following')
        created_at_time = data.get('created_at')
        updated_at_time = data.get('updated_at')
        created_at = discord.utils.format_dt(parse(created_at_time), style='F')
        updated_at = discord.utils.format_dt(parse(updated_at_time), style='F')
        description = f'**User id:** {user_id}\n**Bio:** {bio}\n**Public repos:** {repos}\n**Public gists:** {gists}\n**Followers:** {followers}\n**Following:** {following}\n**Created at:** {created_at}\n**Updated at:** {updated_at}'
        embed = discord.Embed(title='Github user info.', description=description, color=discord.Colour.blurple())
        embed.set_author(name=login, url=url, icon_url=avatar_url)
        embed.set_thumbnail(url=General.GITHUB_IMAGE())
        await ctx.send(embed=embed)
        
    @commands.command(name='github-repo', description='Shows info about a specific repo.', aliases=['repo'])
    async def github_repo(self, ctx: CustomContext, *, query: CharLimit(char_limit=100)):
        if query.count('/') != 1:
            raise ProcessError(f'Invalid input. Please make sure this is the format you use: USERNAME/REPONAME')
        async with self.bot._session.get(url=f'{self.github_api}/repos/{query}') as response:
            if response.status != 200:
                raise ProcessError(self.bad_status.format(status=response.status))
            data = await response.json(encoding='utf-8' ,content_type=None)
            repo_id = data.get('id')
            full_name = data.get('full_name')
            owner_url = data.get('owner').get('avatar_url')
            repo_url = data.get('html_url')
            repo_description = data.get('description')
            is_fork = data.get('fork')
            created_at = discord.utils.format_dt(parse(data.get('created_at')), style='F')
            updated_at = discord.utils.format_dt(parse(data.get('updated_at')), style='F')
            pushed_at = discord.utils.format_dt(parse(data.get('pushed_at')), style='F')
            language = data.get('language')
            forks = data.get('forks_count')
            opened_issue = data.get('open_issues_count')
            license = data.get('license') or None
            license = license.get('name') if license else None
            default_branch = data.get('default_branch')
            add = f'\n**Updated at:** {updated_at}\n**Pushed at:** {pushed_at}\n**Language:** {language}\n**Forks:** {forks}\n**Opened_issue:** {opened_issue}'
            description = f'**Repo id:** {repo_id}\n**Description:** {repo_description}\n**Is fork:** {is_fork}\n**Created at:** {created_at}'
            add2 = f'\n**License:** {license}\n**Default branch:** {default_branch}'
            description += add
            description += add2
            embed = discord.Embed(title='Repository info.', description=description, color=discord.Colour.blurple())
            embed.set_author(name=full_name, url=repo_url, icon_url=owner_url)
            await ctx.send(embed=embed)

    @commands.command(name='lyrics', description='Shows lyrics for a specific song.')
    async def lyrics(self, ctx: CustomContext, *, song_title: CharLimit(char_limit=50)):
        song_title = song_title.replace(' ', '%20')
        url = self.lyrics_api.format(title=song_title)
        async with self.bot._session.get(url=url) as response:
            if response.status != 200:
                raise ProcessError(self.bad_status.format(status=response.status))
            data = await response.json(content_type=None)
            title = data.get('title')
            author = data.get('author')
            lyrics_list = more_itertools.sliced(data.get('lyrics'), 1000)
            thumbnail = data.get('thumbnail').get('genius')
            link = data.get('links').get('genius')
            embeds = []
            for lines in lyrics_list:
                description = f'**Author:** {author}\n\n\n**Lyrics:** {lines}'
                embed = discord.Embed(title='Song lyrics.', description=description, color=discord.Colour.blurple())
                embed.set_author(name=title, url=link)
                embed.set_thumbnail(url=thumbnail)
                embeds.append(embed)
            async def check(interaction: discord.Interaction):
                return interaction.user.id == ctx.author.id
            paginator = Paginator(ctx=ctx, embeds=embeds, timeout=20.0, check=check)
            await paginator.run()

def setup(bot: Bot):
    bot.add_cog(Fun(bot))