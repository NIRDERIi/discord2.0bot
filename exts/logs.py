import typing
from discord.utils import get
from more_itertools import more
from utility.functions import build_embed
import discord
from discord.ext import commands
from bot import Bot, CustomContext
from utility.constants import Time
import more_itertools
import datetime
import asyncio


class Logs(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.bin_link = "https://hastebin.com/documents"
        self.bin_link_format = "https://hastebin.com/{}"
        self.db_messages_cache = {}

    @commands.Cog.listener(name="on_message")
    async def db_messages(self, message: discord.Message):
        if message.author.bot:
            return
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            attachment = (
                await message.attachments[0].read() if message.attachments else None
            )
            await conn.execute(
                """INSERT INTO messages VALUES($1, $2, $3, $4, $5, $6)""",
                message.guild.id,
                message.channel.id,
                message.id,
                message.author.id,
                message.content,
                attachment,
            )
            self.db_messages_cache[message.id] = {
                "guild_id": message.guild.id,
                "channel_id": message.channel.id,
                "author_id": message.author.id,
                "message_content": message.content,
                "attachment": attachment,
            }

    async def get_db_message(self, message_id: discord.Message) -> tuple:
        if self.db_messages_cache.get(message_id):
            message_data: dict = self.db_messages_cache.get(message_id)
            guild_id = message_data.get("guild_id")
            channel_id = message_data.get("channel_id")
            author_id = message_data.get("author_id")
            message_content = message_data.get("message_content")
            attachment = message_data.get("attachment")
        else:
            async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
                data = await conn.fetch(
                    """SELECT * FROM messages WHERE message_id = ($1)""", message_id
                )
                if not data:
                    return None, None, None, None, None
                guild_id = data[0]["guild_id"]
                channel_id = data[0]["channel_id"]
                author_id = data[0]["author_id"]
                message_content = data[0]["message_content"]
                attachment = data[0]["attachment"]
        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id)
        author = guild.get_member(author_id) or self.bot.get_user(author_id)
        return guild, channel, author, message_content, attachment

    async def update_db_message(self, message_id: int, message_content: str):
        if message_id in self.db_messages_cache:
            self.db_messages_cache[message_id]["message_content"] = message_content
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            await conn.execute(
                """UPDATE messages SET message_content = ($1) WHERE message_id = ($2)""",
                message_content,
                message_id,
            )

    async def delete_db_message(self, message_id: int):
        if message_id in self.db_messages_cache:
            self.db_messages_cache.pop(message_id)
        async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
            await conn.execute(
                """DELETE FROM messages WHERE message_id = ($1)""", message_id
            )

    def check_all_none(self, iterable: typing.Iterable):
        none_counter = 0
        for data in iterable:
            if data is None:
                none_counter += 1

        if none_counter == len(iterable):
            return True
        return False

    async def get_webhook(self, guild: discord.Guild) -> discord.Webhook:
        webhook_url = self.bot.logs_webhooks.get(guild.id)
        if not webhook_url:
            async with self.bot.pool.acquire(timeout=Time.BASIC_DBS_TIMEOUT()) as conn:
                data = await conn.fetch(
                    """SELECT webhook_url FROM guilds_config WHERE guild_id = ($1)""",
                    guild.id,
                )
                if not data[0]["webhook_url"]:
                    return False
                try:
                    webhook = discord.Webhook.from_url(
                        url=data[0]["webhook_url"], session=self.bot._session
                    )
                except discord.InvalidArgument:
                    return False
                webhook_url = webhook.url
                self.bot.logs_webhooks[guild.id] = webhook_url
        webhook_url = self.bot.logs_webhooks.get(guild.id)
        try:
            webhook = discord.Webhook.from_url(
                url=webhook_url, session=self.bot._session
            )
        except discord.InvalidArgument:
            return False
        return webhook

    async def get_hastebin(self, text):
        formatted_text = "-\n".join(
            [i for i in [i for i in more_itertools.sliced(text, 158)]]
        )
        data = bytes(formatted_text, "utf-8")
        async with self.bot._session.post(self.bin_link, data=data) as raw_response:
            response = await raw_response.json()
            key = response["key"]
            return self.bin_link_format.format(key)

    async def dispatch_channel_update_event(
        self,
        before: discord.abc.GuildChannel,
        after: discord.abc.GuildChannel,
        webhook: discord.Webhook,
    ):
        if isinstance(before, discord.TextChannel):
            await self.on_text_channel_update(before, after, webhook)
        elif isinstance(before, discord.VoiceChannel):
            await self.on_voice_channel_update(before, after, webhook)
        elif isinstance(before, discord.CategoryChannel):
            channel_type = "CategoryChannel"
        elif isinstance(before, discord.StageChannel):
            await self.on_stage_channel_update(before, after, webhook)

    def find_channel_type(self, channel: discord.abc.GuildChannel):
        if isinstance(channel, discord.TextChannel):
            channel_type = "TextChannel"
        elif isinstance(channel, discord.VoiceChannel):
            channel_type = "VoiceChannel"
        elif isinstance(channel, discord.CategoryChannel):
            channel_type = "CategoryChannel"
        elif isinstance(channel, discord.StageChannel):
            channel_type = "StageChannel"
        return channel_type

    async def on_text_channel_update(
        self,
        before: discord.TextChannel,
        after: discord.TextChannel,
        webhook: discord.Webhook,
    ):
        changes = ""
        before_change = ""
        after_change = ""
        executer = "Not found."
        if before.category != after.category:
            if after.category and before.category:
                changes = "Switched category."
            elif after.category and not before.category:
                changes = "A new category."
            elif before.category and not after.category:
                changes = "Removed from category."
            before_change = before.category.name if before.category else "No category."
            after_change = after.category.name if after.category else "No category."
        elif before.members != after.members:
            if len(before.members) > len(after.members):
                members_less = len(before.members) - len(after.members)
                changes = f"{members_less} members can no longer see {after}"
            else:
                members_more = len(after.members) - len(before.members)
                changes = f"{members_more} more members can see {after}"
            before_change = str(len(before.members)) + " members."
            after_change = str(len(after.members)) + " members."
        elif before.name != after.name:
            changes = "New name."
            before_change = before.name
            after_change = after.name
        elif before.nsfw != after.nsfw:
            changes = "New NSFW settings."
            before_change = before.nsfw
            after_change = after.nsfw
        # do overwrites
        elif before.position != after.position:
            changes = "New channel position."
            before_change = before.position
            after_change = after.position
        elif before.topic != after.topic:
            changes = "New topic."
            before_change = before.topic
            after_change = after.topic
        async for entry in after.guild.audit_logs(
            limit=3, action=discord.AuditLogAction.channel_update
        ):
            if entry.target.id == after.id:
                executer = entry.user
                break
        description = f"**Channel:** {after.mention}\n\n**Overall changes:** `{changes}`\n\n**Before changes:** {before_change}\n\n**After change:** {after_change}\n\n**Executer:** {executer}"
        embed = discord.Embed(
            title="Guild channel update.",
            color=discord.Colour.blurple(),
            description=description,
            timestamp=datetime.datetime.utcnow(),
        )
        await webhook.send(embed=embed)

    async def on_voice_channel_update(
        self,
        before: discord.VoiceChannel,
        after: discord.VoiceChannel,
        webhook: discord.Webhook,
    ):
        changes = ""
        before_change = ""
        after_change = ""
        executer = "Not found."
        if before.category != after.category:
            if after.category and before.category:
                changes = "Switched category."
            elif after.category and not before.category:
                changes = "A new category."
            elif before.category and not after.category:
                changes = "Removed from category."
            before_change = before.category.name if before.category else "No category."
            after_change = after.category.name if after.category else "No category."
        elif before.name != after.name:
            changes = "New name."
            before_change = before.name
            after_change = after.name
        elif before.position != after.position:
            changes = "New channel position."
            before_change = before.position
            after_change = after.position
        elif before.user_limit != after.user_limit:
            changes = "New user limit."
            before_change = f"{before.user_limit} members."
            after_change = f"{after.user_limit} members."
        elif before.rtc_region != after.rtc_region:
            changes = "New region."
            before_change = (
                str(before.rtc_region) if before.rtc_region else "Automatic."
            )
            after_change = str(after.rtc_region) if after.rtc_region else "Automatic."
        else:
            return
        async for entry in after.guild.audit_logs(
            limit=3, action=discord.AuditLogAction.channel_update
        ):
            if entry.target.id == after.id:
                executer = entry.user
                break
        description = f"**Channel:** {after.mention}\n\n**Overall changes:** `{changes}`\n\n**Before changes:** {before_change}\n\n**After change:** {after_change}\n\n**Executer:** {executer}"
        embed = discord.Embed(
            title="Guild channel update.",
            color=discord.Colour.blurple(),
            description=description,
            timestamp=datetime.datetime.utcnow(),
        )
        await webhook.send(embed=embed)

    async def on_stage_channel_update(
        self,
        before: discord.StageChannel,
        after: discord.StageChannel,
        webhook: discord.Webhook,
    ):
        changes = ""
        before_change = ""
        after_change = ""
        executer = "Not found."
        if before.bitrate != after.bitrate:
            changes = "New bitrate."
            before_change = f"{before.bitrate} bitrate."
            after_change = f"{after.bitrate} bitrate."
        elif before.category != after.category:
            if after.category and before.category:
                changes = "Switched category."
            elif after.category and not before.category:
                changes = "A new category."
            elif before.category and not after.category:
                changes = "Removed from category."
            before_change = before.category.name if before.category else "No category."
            after_change = after.category.name if after.category else "No category."
        elif before.name != after.name:
            changes = "New name."
            before_change = before.name
            after_change = after.name
        elif before.position != after.position:
            changes = "New channel position."
            before_change = before.position
            after_change = after.position
        elif before.rtc_region != after.rtc_region:
            changes = "New region."
            before_change = (
                str(before.rtc_region) if before.rtc_region else "Automatic."
            )
            after_change = str(after.rtc_region) if after.rtc_region else "Automatic."
        elif before.topic != after.topic:
            changes = "New topic."
            before_change = before.topic or "No topic."
            after_change = after.topic or "No topic."
        else:
            return
        async for entry in after.guild.audit_logs(
            limit=3, action=discord.AuditLogAction.channel_update
        ):
            if entry.target.id == after.id:
                executer = entry.user
                break
        description = f"**Channel:** {after.mention}\n\n**Overall changes:** `{changes}`\n\n**Before changes:** {before_change}\n\n**After change:** {after_change}\n\n**Executer:** {executer}"
        embed = discord.Embed(
            title="Guild channel update.",
            color=discord.Colour.blurple(),
            description=description,
            timestamp=datetime.datetime.utcnow(),
        )
        await webhook.send(embed=embed)

    @commands.Cog.listener(name="on_raw_message_delete")
    async def raw_message_delete_logs(self, payload: discord.RawMessageDeleteEvent):

        guild = self.bot.get_guild(payload.guild_id)
        webhook = await self.get_webhook(guild)
        if not webhook:
            return

        channel = guild.get_channel(payload.channel_id)
        content = (
            payload.cached_message.content
            if payload.cached_message
            else "Couldn't fetch."
        )
        content = content if len(content) < 512 else await self.get_hastebin(content)
        content = content or "`Not a string content.`"
        executer = "Not found. Probably self-delete or message not in cache."
        if payload.cached_message:
            async for entry in guild.audit_logs(
                limit=3, action=discord.AuditLogAction.message_delete
            ):
                if entry.target.id == payload.cached_message.author.id:
                    executer = entry.user
                    break
        description = f"**Channel:** {channel.mention}\n\n**Content:** {content}\n\n**Executer:** {executer}"
        await webhook.send(
            embed=build_embed(
                title="Message delete.",
                description=description,
                timestamp=datetime.datetime.utcnow(),
            )
        )

    @commands.Cog.listener(name="on_raw_bulk_message_delete")
    async def raw_bulk_message_delete_logs(
        self, payload: discord.RawBulkMessageDeleteEvent
    ):
        guild = self.bot.get_guild(payload.guild_id)
        webhook = await self.get_webhook(guild)
        if not webhook:
            return
        channel = guild.get_channel(payload.channel_id)
        description = f"**Channel:** {channel.mention}\n\n**Messages deleted:** {len(payload.message_ids)}\n\n"
        executer = "Not found."
        async for entry in guild.audit_logs(
            limit=3, action=discord.AuditLogAction.message_bulk_delete
        ):
            if entry.target.id == channel.id:
                executer = entry.user
                break
        description += f"**Executer:** {executer}"
        await webhook.send(
            embed=build_embed(
                title="Bulk message delete.",
                description=description,
                timestamp=datetime.datetime.utcnow(),
            )
        )

    @commands.Cog.listener(name="on_raw_message_edit")
    async def raw_message_edit_logs(self, payload: discord.RawMessageUpdateEvent):
        guild = self.bot.get_guild(payload.guild_id)
        webhook = await self.get_webhook(guild)
        if not webhook:
            return
        message_db = await self.get_db_message(payload.message_id)
        all_none = self.check_all_none(message_db)
        if all_none:

            channel = guild.get_channel(payload.channel_id)

            new_content = payload.data.get("content")
            old_content = (
                payload.cached_message.content
                if payload.cached_message
                else "Couldn't fetch."
            )
            if new_content == old_content:
                return
            author_name = payload.data.get("author").get("username")
            author_discriminator = payload.data.get("author").get("discriminator")
            old_content = old_content or "`No string content.`"
            old_content = (
                old_content
                if len(old_content) < 350
                else await self.get_hastebin(old_content)
            )
            new_content = (
                new_content
                if len(new_content) < 350
                else await self.get_hastebin(new_content)
            )
            new_content = new_content or "`No string content.`"
        else:
            new_content = payload.data.get("content")
            author_name = payload.data.get("author").get("username")
            author_discriminator = payload.data.get("author").get("discriminator")
            guild, channel, author, message_content, attachment = message_db
            if new_content == message_content:
                return
        await self.update_db_message(payload.message_id, payload.data.get("content"))
        description = f"**Channel:** {channel.mention}\n\n**Author:** {author_name}#{author_discriminator}\n\n**Old content:** {old_content}\n\n**New content:** {new_content}"
        await webhook.send(
            embed=build_embed(
                title="Message edit.",
                description=description,
                timestamp=datetime.datetime.utcnow(),
            )
        )

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def guild_channel_delete_logs(self, channel: discord.abc.GuildChannel):
        webhook = await self.get_webhook(channel.guild)
        if not webhook:
            return
        channel_type = self.find_channel_type(channel)
        executer = "Couldn't fetch."
        async for entry in channel.guild.audit_logs(
            limit=3, action=discord.AuditLogAction.channel_delete
        ):
            if entry.target.id == channel.id:
                executer = entry.user
                break
        description = f"**Name:** {channel.name}\n\n**Type:** `{channel_type}`\n\n**Excecuter:** {executer}"
        await webhook.send(
            embed=build_embed(
                title="Guild channel delete.",
                description=description,
                timestamp=datetime.datetime.utcnow(),
            )
        )

    @commands.Cog.listener(name="on_guild_channel_create")
    async def guild_channel_create_logs(self, channel: discord.abc.GuildChannel):
        webhook = await self.get_webhook(channel.guild)
        if not webhook:
            return
        channel_type = self.find_channel_type(channel)
        executer = "Couldn't fetch."
        async for entry in channel.guild.audit_logs(
            limit=3, action=discord.AuditLogAction.channel_create
        ):
            if entry.target.id == channel.id:
                executer = entry.user
                break
        description = f"**Name:** {channel.name}\n\n**Type:** `{channel_type}`\n\n**Excecuter:** {executer}"
        await webhook.send(
            embed=build_embed(
                title="Guild channel created.",
                description=description,
                timestamp=datetime.datetime.utcnow(),
            )
        )

    @commands.Cog.listener(name="on_guild_channel_update")
    async def guild_channel_update_logs(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ):
        webhook = await self.get_webhook(before.guild)
        if not webhook:
            return
        await self.dispatch_channel_update_event(before, after, webhook)

    @commands.Cog.listener(name="on_message")
    async def pinned_message(self, message: discord.Message):
        webhook = await self.get_webhook(message.guild)
        if not webhook:
            return
        if not message.type is discord.MessageType.pins_add:
            return
        if not message.reference:
            return
        message_ref: discord.Message = (
            message.reference.cached_message
            or message.reference.resolved
            or await message.channel.fetch_message(message.reference.message_id)
        )
        if not message_ref:
            return
        if not message_ref.pinned:
            return
        executer = "Not found."

        embed = build_embed(title="Message pinned.", description="")
        async for entry in message.guild.audit_logs(
            limit=2, action=discord.AuditLogAction.message_pin
        ):
            if entry.target.id == message_ref.author.id:
                executer = entry.user
                break
        content = message_ref.content or "No content."
        content = content if len(content) < 2000 else await self.get_hastebin(content)
        kwargs = {}
        embed.description = f"**Channel:** {message_ref.channel.mention}\n\n**Author:** {message_ref.author}\n\n**Content:** {content}\n\n**Executer:** {executer}"
        if message_ref.attachments:
            files = []
            for attachment in message_ref.attachments:

                files.append(await attachment.to_file())
            kwargs["files"] = files
        embeds = [embed]
        if message_ref.embeds:
            for sent_embed in message_ref.embeds:
                embeds.append(sent_embed.copy())

        if len(embeds) > 10:
            embeds.pop(11)
        kwargs["embeds"] = embeds
        await webhook.send(**kwargs)

    @commands.Cog.listener(name="on_member_update")
    async def member_update_logs(self, before: discord.Member, after: discord.Member):
        guild = after.guild or before.guild
        webhook = await self.get_webhook(guild)
        if not webhook:
            return
        if before.nick != after.nick:
            before_changes = before.nick or "Had no nickname."
            after_changes = after.nick or "Nickname reseted."
            changes = "New nickname."
        elif before.roles != after.roles:
            if len(before.roles) > len(after.roles):  # Removed a role.
                changed_roles


def setup(bot: Bot):
    bot.add_cog(Logs(bot))
