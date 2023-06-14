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
    auto_volt.start()

@bot.event
async def on_message(message):
    if(message.author.id!=1117105897710305330):
        pass
        #print(f"{message.author} has sent a message")
        #print(f"{message.author.name} said {message.content}")
       
@tasks.loop(minutes=1)
async def auto_volt():
    

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
    await destination_channel.send(
        embed=embed
    )
    
    





     

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