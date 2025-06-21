import random
import asyncio
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import discord
from discord.ext import tasks
from discord import Guild, TextChannel, ForumChannel, Member, Embed, Color, Thread, Role, VoiceChannel
from config import  DESTINATION_CHANNEL_ID as DESTINATION_CHANNEL_ID, ANNOUNCEMENT_CHANNEL_ID, GUILD_ID, MR_ELECTRICITY_ROLE_ID, HIGH_VOLTAGE_ROLE_ID, ADMIN_ROLES_IDS, ADMIN_ROLES_IDS_ELECTRICITY, TEXT_CHANNEL_LIST, FORUM_CHANNEL_LIST, EMBED_DESCRIPTION, EMBED_TITLE, EMBED_COLOR
from utils.helpers import escape_markdown, async_db_retry
import math
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
        
        self.leaderboard_entries = []  # List to store leaderboard entries
        
        # Winner settings
        self.cached_winners_embed = None  # Cache for the winner embed
        self.total_rewards_amount = 1000  # Total rewards amount to be distributed
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
                members = await session.scalars(select(DBMember).where(DBMember.guild_id == guild.id))
                db_members = members.all()
            except Exception as e:
                print(f"Error fetching members from DB: {e}")
                return [], {}

            db_message_counts = {}
            if member_ids:
                try:
                    # Calculate the datetime threshold for filtering messages
                    days_ago = datetime.now(tz=timezone.utc) - timedelta(days=self.leaderboard_days)
                    result = await session.execute(
                        select(DBMessage.author_id, func.count(DBMessage.id))
                        .where(
                            DBMessage.author_id.in_(member_ids),
                            DBMessage.guild_id == guild.id,
                            DBMessage.timestamp >= days_ago
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

        # Filter members not with admin roles (or include all if ADMIN_ROLES_IDS is empty)
        non_admin_messages = {
            member: count for member, count in count_messages_by_members.items()
            if (
            isinstance(member, Member)
            and (
                not ADMIN_ROLES_IDS
                or not ({role.id for role in member.roles} & set(ADMIN_ROLES_IDS))
            )
            )
        }
        top_ten = Counter(non_admin_messages).most_common(20)

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
        mr_electricity_assigned = False  # Flag to ensure only one member gets the Mr. Electricity role

        for member, count in top_ten:
            if isinstance(member, Member):
                text_volt = count * self.text_multiplier
                in_voice_count = db_message_counts.get(int(member.id), 0)
                in_voice_boost = in_voice_count * self.in_voice_boost_multiplier
                total_volt = text_volt + in_voice_boost

                # Check if member is eligible for Mr. Electricity (no admin roles)
                has_admin_electricity = bool({role.id for role in member.roles} & set(ADMIN_ROLES_IDS_ELECTRICITY))
                is_mr_electricity = False
                if not mr_electricity_assigned and not has_admin_electricity:
                    is_mr_electricity = True
                    mr_electricity_assigned = True

                leaderboard_entries.append({
                    "member": member,
                    "text_volt": text_volt,
                    "in_voice_boost": in_voice_boost,
                    "total_volt": total_volt,
                    "is_mr_electricity": is_mr_electricity,
                })

        # Sort by total_volt descending
        leaderboard_entries.sort(key=lambda x: x["total_volt"], reverse=True)

        self.leaderboard_entries = leaderboard_entries  # Store entries for later use

        embed_content = ""
        top_ten_list = []
        for idx, entry in enumerate(leaderboard_entries):
            member = entry["member"]
            total_volt = entry["total_volt"]
            in_voice_boost = entry["in_voice_boost"]
            memberName = escape_markdown(member.display_name)
            embed_content += f"`{idx+1}` **{memberName}** "
            if entry.get("is_mr_electricity") is True:
                embed_content += "<:hlbElectricity:1376631302681399439> "
            embed_content += f" — `{total_volt}` volt"
            if in_voice_boost != 0:
                embed_content += f"\t<:hlbInVoice:1385763040238112798> `+{in_voice_boost}`"
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
                    
                    if self.is_prod and message.author == bot_user:
                        await message.delete()
            except Exception as e:
                print(f"Error cleaning previous messages: {e}")
            self.cached_leaderboard_embed = embed
            if self.is_prod:
                await destination_channel.send(embed=embed)
            else:
                print("Skipping sending leaderboard embed in development mode.")
            
            #Role assignment logic
            mr_electricity_role: Optional[Role] = discord.utils.get(guild.roles, id=MR_ELECTRICITY_ROLE_ID)

            high_voltage_role: Optional[Role] = discord.utils.get(guild.roles, id=HIGH_VOLTAGE_ROLE_ID)
            
            if not high_voltage_role or not mr_electricity_role:
                print("Required roles not found")
                return
            if self.is_prod:
            # High Voltage role management
                try:
                    for member in high_voltage_role.members:
                        if member.id not in top_ten_list:
                            try:
                                await member.remove_roles(high_voltage_role)
                                print(f"Removed High Voltage from {member.display_name}", flush=True)
                            except Exception as e:
                                print(f"Error removing High Voltage from {member.display_name}: {e}")
                    for member_id in top_ten_list:
                        try:
                            member = await guild.fetch_member(member_id)
                            if member:
                                await member.add_roles(high_voltage_role)
                                print(f"Awarded High Voltage to {member.display_name}", flush=True)
                        except Exception as e:
                            print(f"Error adding High Voltage to member {member_id}: {e}")
                    # Get the current top member who does not have admin roles (electricity roles)
                    current_top_member = None
                    for member_id in top_ten_list:
                        try:
                            member = await guild.fetch_member(member_id)
                            if not member:
                                continue
                            has_admin = bool({role.id for role in member.roles} & set(ADMIN_ROLES_IDS_ELECTRICITY))
                            if not has_admin:
                                current_top_member = member
                                break
                        except Exception as e:
                            print(f"Error fetching member {member_id}: {e}")
                    
                    # Remove Mr. Electricity role from existing top member if they are not the current top member
                    for member in mr_electricity_role.members:
                        if current_top_member and member.id == current_top_member.id:
                            continue
                        try:
                            await member.remove_roles(mr_electricity_role)
                            print(f"Removed Mr. Electricity from {member.display_name}")
                        except Exception as e:
                            print(f"Error removing Mr. Electricity from {member.display_name}: {e}")
                    if current_top_member:
                        try:
                            await current_top_member.add_roles(mr_electricity_role)
                            print(f"Awarded Mr. Electricity to {current_top_member.display_name}", flush=True)
                        except Exception as e:
                            print(f"Error adding Mr. Electricity to {current_top_member.display_name}: {e}", flush=True)
                except Exception as e:
                    print(f"Unexpected error during role management: {e}", flush=True)
                # Role management logic end
            else:
                print("Skipping role management in development mode.")
        except Exception as e:
            print(f"Error in auto leaderboard task: {e}, will retry in 5 minutes.",flush=True)
    
    

    @tasks.loop(hours=1)
    async def update_leaderboard_days_task(self):
        print("Updating leaderboard days...")
        await self.update_leaderboard_days()

    @tasks.loop(minutes=1)
    async def auto_winner(self):
        """
        This task checks every minute and runs the winner logic every Sunday at 9:30PM Bangladesh time (UTC+6).
        """
        # Use only the standard library: datetime, timedelta, timezone
        now = datetime.now(timezone(timedelta(hours=6)))  # UTC+6 for Asia/Dhaka
        #print(f"Current time in Asia/Dhaka: {now.strftime('%A, %Y-%m-%d %H:%M:%S')}", flush=True)
        if now.weekday() == 6 and now.hour == 21 and now.minute == 30:
            # Add your winner selection logic here
            print("It's Sunday at 9:30 PM in Asia/Dhaka, running winner selection task...", flush=True)
            print("Running auto winner selection task...")
            embed= Embed(
                title="Winners of High Voltage Rewards",
                description="Winners of High Voltage rewards have been selected by our official bot HLB Volt based on the members' chat activities in recent days.",
                color=Color.from_str(EMBED_COLOR)
            )
            entries = self.leaderboard_entries
            embed_content = ""
            if not entries:
                print("No leaderboard entries available for winner selection.")
                return
            else:
                # Winner selection logic
                # Get total sum of total_volt for all members in self.leaderboard_entries
                total_volt_sum = sum(entry["total_volt"] for entry in entries)
                print(f"Total volt sum: {total_volt_sum}", flush=True)
                if total_volt_sum == 0:
                    print("Total volt sum is 0, cannot select winners.")
                    return
                #Get top 10 members
                top_members = entries[:10] if len(entries) >= 10 else entries
                for idx, entry in enumerate(top_members):
                    member = entry["member"]
                    total_volt = entry["total_volt"]
                    member_points_percent = (total_volt / total_volt_sum) * 100 
                    points = math.floor((member_points_percent / 100) * self.total_rewards_amount) 
                    print(f"{member.display_name} has {total_volt} total volt. Points: {points}\n", flush=True)
                    memberName = escape_markdown(member.display_name)
                    if points>0:
                        embed_content += f"`{idx+1}` **{memberName}** - <:hlbPoints:1091554934002040843> `{points}`"
                    
                    embed_content += "\n"
                
            embed_content += "\nThe winners are requested to <#841942978842066994> to claim their rewards.\n\n"
        
            embed.set_thumbnail(url="https://res.cloudinary.com/codebound/image/upload/v1681038436/hlb-fb-profile_v2.1_cmoamk.png")
            embed.set_image(url="https://res.cloudinary.com/codebound/image/upload/v1681039731/hlb-post_high-voltage_fhd_v2.1_paegjl.jpg")
            embed.set_footer(text="© Codebound")
            embed.add_field(name="", value=embed_content)
            # Send the embed to the announcement channel
            try:
                announcement_channel: discord.TextChannel = await self.client.fetch_channel(ANNOUNCEMENT_CHANNEL_ID)
                await announcement_channel.send(embed=embed, content="<@&803016602378829865>" )
                print("Winner announcement embed sent successfully.", flush=True)
            except discord.NotFound:
                print(f"Channel {ANNOUNCEMENT_CHANNEL_ID} was not found")
                return
            except discord.Forbidden:
                print(f"Bot does not have permission to access channel {ANNOUNCEMENT_CHANNEL_ID}")
                return
            except discord.HTTPException as e:
                print(f"HTTP error while fetching channel: {e}")
                return

            self.cached_winners_embed = embed
        else:
            print(f"Not the right time for winner selection. Current time: {now.strftime('%A, %Y-%m-%d %H:%M:%S')}", flush=True)