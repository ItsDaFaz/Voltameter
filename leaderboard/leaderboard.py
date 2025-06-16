import random
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import discord
from discord.ext import tasks
from discord import Guild, TextChannel, ForumChannel, Member, Embed, Color, Thread, Role, VoiceChannel
from config import  DESTINATION_CHANNEL_ID as DESTINATION_CHANNEL_ID, GUILD_ID, MR_ELECTRICITY_ROLE_ID, HIGH_VOLTAGE_ROLE_ID, ADMIN_ROLES_IDS, TEXT_CHANNEL_LIST, FORUM_CHANNEL_LIST, EMBED_DESCRIPTION, EMBED_TITLE, EMBED_COLOR
from utils.helpers import escape_markdown, async_db_retry

from db.session import get_engine, get_session_maker
from db.models import Member as DBMember, Message as DBMessage
from sqlalchemy import select, func





class LeaderboardManager:
    def __init__(self, client, IS_PROD):
        self.client = client
        # Leaderboard settings
        self.leaderboard_days = 5
        self.leaderboard_lock = asyncio.Lock()
        self.cached_leaderboard_embed = None
        self.voltage_multiplier = 3  # Multiplier for volt calculation
        self.voice_voltage_multiplier = 5  # Multiplier for voice channel volt calculation

        # Channel message counts
        self.channel_message_counts = {}
        self.forum_message_counts = {}

        self.is_prod = IS_PROD
        # self.is_prod = True  # For testing purposes
        # Create engine and sessionmaker for this thread/event loop
        self.engine = get_engine()
        self.SessionLocal = get_session_maker(self.engine)

        # Global multipliers
        self.text_multiplier = 3
        self.in_voice_boost_multiplier = 2

    async def update_leaderboard_days(self):
        
        async with self.leaderboard_lock:
            self.leaderboard_days = random.randint(4, 7)
            print(f"Updated leaderboard days to: {self.leaderboard_days}")

    async def get_leaderboard_days(self):
        async with self.leaderboard_lock:
            return self.leaderboard_days
        
    async def update_channel_message_counts(self, guild: Guild, count: Counter):
        async with self.leaderboard_lock:
            self.channel_message_counts[guild.id] = count
            print(f"Updated channel message counts for guild {guild.id}: {count}")
    
    async def get_channel_message_counts(self, guild: Guild):
        async with self.leaderboard_lock:
            return self.channel_message_counts.get(guild.id, Counter())
    
    async def update_forum_message_counts(self, guild: Guild, count: Counter):
        async with self.leaderboard_lock:
            self.forum_message_counts[guild.id] = count
            print(f"Updated forum message counts for guild {guild.id}: {count}")
    async def get_forum_message_counts(self, guild: Guild):
        async with self.leaderboard_lock:
            return self.forum_message_counts.get(guild.id, Counter())

    @async_db_retry()
    async def fetch_leaderboard_db_data(self, guild: Guild, member_ids: List[int]):
        """
        Fetch members and message counts from the database for the given guild and member IDs.
        Returns (db_members, db_message_counts)
        """
        async with self.SessionLocal() as session:
            try:
                from sqlalchemy import literal
                members = await session.scalars(
                    select(DBMember).where(literal(guild.id).op('= ANY')(DBMember.guild_id))
                )
                db_members = members.all()
            except Exception as e:
                print(f"Error fetching members from DB: {e}")
                return [], {}

            db_message_counts = {}
            if member_ids:
                try:
                    result = await session.execute(
                        select(DBMessage.author_id, func.count(DBMessage.id))
                        .where(
                            DBMessage.author_id.in_(member_ids),
                            DBMessage.guild_id == guild.id
                        )
                        .group_by(DBMessage.author_id)
                    )
                    db_message_counts = {int(row[0]): int(row[1]) for row in result}
                except Exception as e:
                    print(f"Error fetching message counts from DB: {e}")
            return db_members, db_message_counts

    async def generate_leaderboard_embed(self, guild: Guild):
        days_ago = datetime.now(tz=timezone.utc) - timedelta(days=await self.get_leaderboard_days())
        channel_list = TEXT_CHANNEL_LIST
        text_channels: List[TextChannel | VoiceChannel] = [
            channel for channel in guild.channels
            if isinstance(channel, (TextChannel, VoiceChannel)) and channel.id in channel_list
        ]
        channel_names = [channel.name for channel in text_channels]
        print(f"Selected text channels: {channel_names}")
        count_messages_by_members = Counter()
        count_messages_per_channel = Counter()
        for channel in text_channels:
            try:
                async for message in channel.history(limit=None, after=days_ago):
                    count_messages_per_channel[channel.id] += 1
                    if message.author and not message.author.bot:
                        count_messages_by_members[message.author] += 1
            except Exception as e:
                print(f"Error processing channel {channel.name}: {e}")
            continue
        print(f"Message counts per channel: {count_messages_per_channel}")

        await self.update_channel_message_counts(guild, count_messages_per_channel)

        forum_channel_list = FORUM_CHANNEL_LIST
        forum_channels: List[ForumChannel] = [
            channel for channel in getattr(guild, 'forums', [])
            if isinstance(channel, ForumChannel) and channel.id in forum_channel_list
        ]
        forum_channel_names = [channel.name for channel in forum_channels]
        print(f"Selected forum channels: {forum_channel_names}")
        if not forum_channels:
            print("No valid forum channels found in the guild.")
            return None, []
        if not text_channels:
            print("No valid text channels found in the guild.")
            return None, []

        thread_list: List[Thread] = []
        count_messages_per_forum_channel = Counter()
        for forum_channel in forum_channels:
            try:
                forum_threads = forum_channel.threads
                thread_list.extend(forum_threads)
                forum_message_count = 0
                for thread in forum_threads:
                    thread_message_count = 0
                    try:
                        async for message in thread.history(limit=None, after=days_ago):
                            thread_message_count += 1
                            if message.author and not message.author.bot:
                                count_messages_by_members[message.author] += 1
                        forum_message_count += thread_message_count
                    except Exception as e:
                        print(f"Error processing thread {thread.name}: {e}")
                    continue
                count_messages_per_forum_channel[forum_channel.id] = forum_message_count
            except Exception as e:
                print(f"Error processing forum channel {forum_channel.name}: {e}")
            continue

        print(f"Message counts per forum channel: {count_messages_per_forum_channel}")

        await self.update_forum_message_counts(guild, count_messages_per_forum_channel)

        # Filter members not with admin roles
        non_admin_messages = {
            member: count for member, count in count_messages_by_members.items()
            if (
                isinstance(member, Member)
                and not ({role.id for role in member.roles} & set(ADMIN_ROLES_IDS))
                and not any(role.permissions.administrator for role in member.roles)
            )
        }
        top_ten = Counter(non_admin_messages).most_common(10)

        # Efficiently fetch DB message counts for these members (messages sent in voice)
        member_ids = [member.id for member, _ in top_ten if isinstance(member, Member)]
        db_members, db_message_counts = await self.fetch_leaderboard_db_data(guild, member_ids)

        embed = Embed(
            title=EMBED_TITLE,
            description=EMBED_DESCRIPTION,
            color=Color.from_str(EMBED_COLOR),
        )
        # Calculate total volt for each member and sort accordingly
        leaderboard_entries = []
        for member, count in top_ten:
            if isinstance(member, Member):
                text_volt = count * self.text_multiplier
                in_voice_count = db_message_counts.get(int(member.id), 0)
                in_voice_boost = in_voice_count * self.in_voice_boost_multiplier
                total_volt = text_volt + in_voice_boost
                leaderboard_entries.append({
                    "member": member,
                    "text_volt": text_volt,
                    "in_voice_boost": in_voice_boost,
                    "total_volt": total_volt,
                })

        # Sort by total_volt descending
        leaderboard_entries.sort(key=lambda x: x["total_volt"], reverse=True)

        embed_content = ""
        top_ten_list = []
        for idx, entry in enumerate(leaderboard_entries):
            member = entry["member"]
            total_volt = entry["total_volt"]
            in_voice_boost = entry["in_voice_boost"]
            memberName = escape_markdown(member.display_name)
            embed_content += f"`{idx+1}` **{memberName}** — `{total_volt}` volt"
            if in_voice_boost != 0:
                embed_content += f"\t<:_:1380603159906619452> `+{in_voice_boost}`"
            embed_content += "\n"
            top_ten_list.append(member.id)  # Always append, regardless of in_voice_boost
        embed_content += f"\nBased on last `{str(await self.get_leaderboard_days())}` **days** of messaging activities."
        if not embed_content:
            return None, []
        embed.add_field(name="", value=embed_content)
        embed.set_image(url="https://res.cloudinary.com/codebound/image/upload/v1681039731/hlb-post_high-voltage_fhd_v2.1_paegjl.jpg")
        embed.set_thumbnail(url="https://res.cloudinary.com/codebound/image/upload/v1681116021/pfp-hlb-high-voltage_em6tpk.png")
        embed.set_footer(text="© Codebound")
        return embed, top_ten_list

    @tasks.loop(minutes=30)
    async def auto_leaderboard(self):
        try:
            guild: Optional[Guild] = self.client.get_guild(GUILD_ID)
            print("Beginning leaderboard update...")
            if not guild:
                print(f"Could not find guild with ID {GUILD_ID}")
                return
            try:
                destination_channel = await self.client.fetch_channel(DESTINATION_CHANNEL_ID)
            except discord.NotFound:
                print(f"Channel {DESTINATION_CHANNEL_ID} was not found")
                return
            except discord.Forbidden:
                print(f"Bot does not have permission to access channel {DESTINATION_CHANNEL_ID}")
                return
            except discord.HTTPException as e:
                print(f"HTTP error while fetching channel: {e}")
                return
            if not isinstance(destination_channel, (TextChannel, Thread)):
                print(f"Channel {DESTINATION_CHANNEL_ID} is not a text channel or thread.")
                return
            bot_user: Optional[discord.ClientUser] = self.client.user
            if not bot_user:
                print("Bot user is not initialized")
                return
            embed, top_ten_list = await self.generate_leaderboard_embed(guild)
            if not embed:
                print("No valid non-admin members found for leaderboard")
                return
            try:
                async for message in destination_channel.history(limit=None):
                    if message.author == bot_user:
                        await message.delete()
            except Exception as e:
                print(f"Error cleaning previous messages: {e}")
            self.cached_leaderboard_embed = embed
            await destination_channel.send(embed=embed)
            
            #Role assignment logic
            mr_electricity_role: Optional[Role] = discord.utils.get(guild.roles, id=MR_ELECTRICITY_ROLE_ID)
            high_voltage_role: Optional[Role] = discord.utils.get(guild.roles, id=HIGH_VOLTAGE_ROLE_ID)
            if not high_voltage_role or not mr_electricity_role:
                print("Required roles not found")
                return
            try:
                for member in high_voltage_role.members:
                    if member.id not in top_ten_list:
                        try:
                            await member.remove_roles(high_voltage_role)
                        except Exception as e:
                            print(f"Error removing High Voltage from {member.name}: {e}")
                for member_id in top_ten_list:
                    try:
                        member = await guild.fetch_member(member_id)
                        if member:
                            await member.add_roles(high_voltage_role)
                    except Exception as e:
                        print(f"Error adding High Voltage to member {member_id}: {e}")
                current_top_member = None
                for member_id in top_ten_list:
                    try:
                        member = await guild.fetch_member(member_id)
                        if not member:
                            continue
                        has_admin = bool({role.id for role in member.roles} & set(ADMIN_ROLES_IDS))
                        if not has_admin:
                            current_top_member = member
                            break
                    except Exception as e:
                        print(f"Error fetching member {member_id}: {e}")
                for member in mr_electricity_role.members:
                    if current_top_member and member.id == current_top_member.id:
                        continue
                    try:
                        await member.remove_roles(mr_electricity_role)
                        print(f"Removed Mr. Electricity from {member.name}")
                    except Exception as e:
                        print(f"Error removing Mr. Electricity from {member.name}: {e}")
                if current_top_member:
                    try:
                        await current_top_member.add_roles(mr_electricity_role)
                        print(f"Awarded Mr. Electricity to {current_top_member.name}")
                    except Exception as e:
                        print(f"Error adding Mr. Electricity to {current_top_member.name}: {e}", flush=True)
            except Exception as e:
                print(f"Unexpected error during role management: {e}", flush=True)
            # Role management logic end
        except Exception as e:
            print(f"Error in auto leaderboard task: {e}, will retry in 5 minutes.",flush=True)

    @tasks.loop(hours=1)
    async def update_leaderboard_days_task(self):
        print("Updating leaderboard days...")
        await self.update_leaderboard_days()