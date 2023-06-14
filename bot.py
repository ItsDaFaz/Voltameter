from config import TOKEN
from discord.ext import tasks
import os
import discord
from collections import Counter
from datetime import datetime, timedelta

intents=discord.Intents.default()
intents.messages=True
intents.typing = False
intents.presences = False
#intents.message_content=True
intents.guild_messages=True
bot=discord.Bot(intents=intents)



@bot.event
async def on_ready():
    print(f"{bot.user} has logged in!")
    auto_leaderboard.start()

@bot.event
async def on_message(message):
    if(message.author.id!=1117105897710305330):
        pass
        #print(f"{message.author} has sent a message")
        #print(f"{message.author.name} said {message.content}")
       
@tasks.loop(minutes=1)
async def auto_leaderboard():
    

    destination_channel_id=1118501021195456572 #Terminal 2
    guild_id=636532413744414731 #HLB
    guild=bot.get_guild(guild_id)
    destination_channel=bot.get_channel(destination_channel_id)

    bot_user = bot.user

    messages = await destination_channel.history(limit=None).flatten()
    for message in messages:
        if message.author == bot_user:
            await message.delete()

    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    channels=guild.text_channels
    count_messages_by_members=Counter()
    
    
    for channel in channels:
        try:
            messages=await channel.history(limit=None, after=seven_days_ago).flatten() 
            #async for message in ctx.channel.history(limit=None,after=seven_days_ago):
            for message in messages:
                if not message.author.bot:
                    count_messages_by_members[message.author]+=1
        except Exception as e:
            #print(e)
            continue
    
    

    top_ten=count_messages_by_members.most_common(10)
    embed=discord.Embed(
            title="The Top Ten",
            description="The top ten members with most messages sent",
            color=discord.Color.from_rgb(206, 255, 0)
            #rgb(206, 255, 0)
    )
    #ID of High Voltage 873517967982362674
    #top_ten=c.most_common()
    #print(top_ten)
    top_ten_list=[]
    embed_content=""
    for idx,i in enumerate(top_ten):
            #embed.add_field(name=f"{idx}",value=f"{ {i[0].name}}")
            top_ten_list.append(i[0].id)
            embed_content=embed_content+f"{idx}. {i[0].name}• {i[1]} messages\n"
    print(top_ten_list)
    embed.add_field(name="Leaderboard",value=embed_content)
    await destination_channel.send(
        embed=embed
    )
    mr_electricity_role_id=1108079835265376426
    mr_electricity_role=discord.utils.get(guild.roles,id=mr_electricity_role_id)
    high_voltage_role_id=873517967982362674
    high_voltage_role=discord.utils.get(guild.roles,id=high_voltage_role_id)
    high_voltage_members=high_voltage_role.members

    for member in high_voltage_members:
        if member.id not in top_ten_list:
            await member.remove_roles(high_voltage_role)
    
    admin_roles_id=[1116013925574651975,880229392599617606,997834090797596763]

    print(high_voltage_members)
    for new_member_id in top_ten_list:
        print("for ",str(new_member_id))
        mr_electricity_flag=True
        member=guild.get_member(new_member_id)
        print("for ",str(member.name))
        await member.add_roles(high_voltage_role)
        member_roles=member.roles
        has_any_admin_role=any(role.id in admin_roles_id for role in member_roles)

        if not has_any_admin_role and mr_electricity_flag:
            await member.add_roles(mr_electricity_role)
            mr_electricity_flag=False




    
     

@bot.command()
async def voltage(ctx):
        
        
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        guild=ctx.guild
        channels=guild.text_channels    
        count_messages_by_members=Counter()
        
        await ctx.defer()
        for channel in channels:
            try:
                messages=await channel.history(limit=None, after=seven_days_ago).flatten() 
                #async for message in ctx.channel.history(limit=None,after=seven_days_ago):
                for message in messages:
                    if not message.author.bot:
                        count_messages_by_members[message.author]+=1
            except Exception as e:
                print(e)
                continue
        
        

        top_ten=count_messages_by_members.most_common(10)
        embed=discord.Embed(
             title="The Top Ten",
             description="The top ten members with most messages sent",
             color=discord.Color.from_rgb(206, 255, 0)
             #rgb(206, 255, 0)
        )
        #ID of High Voltage 873517967982362674
        #top_ten=c.most_common()
        print(top_ten)
        
        embed_content=""
        for idx,i in enumerate(top_ten):
             #embed.add_field(name=f"{idx}",value=f"{ {i[0].name}}")
             embed_content=embed_content+f"{idx}. {i[0].name}• {i[1]} messages\n"
        
        embed.add_field(name="Leaderboard",value=embed_content)
        
        await ctx.respond(
            embed=embed
        )



# cogfiles=[
#     f"cogs.{filename[:-3]}" for filename in os.listdir("./cogs/") if filename.endswith(".py")
# ]

# for cogfile in cogfiles:
#     try:
#         bot.load_extension(cogfile)
#     except Exception as e:
#         print(e)

bot.run(TOKEN)