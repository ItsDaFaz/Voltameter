from config import TOKEN
from discord.ext import commands
import os
import discord
from collections import Counter
from datetime import datetime, timedelta

intents=discord.Intents.default()
intents.messages=True
bot=discord.Bot(intents=intents)
c=Counter()


@bot.event
async def on_ready():
    print(f"{bot.user} has logged in!")

@bot.event
async def on_message(message):
    if(message.author.id!=1117105897710305330):
        #print(f"{message.author} has sent a message")
        #print(f"{message.author.name} said {message.content}")
        c[message.author]+=1
        print(f"{message.author} has sent {c[message.author]} messages")

@bot.command()
async def voltage(ctx):
        voltage_list=[]
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        members=ctx.guild.members
        guild=ctx.guild
        channels=guild.text_channels    
        count_messages_by_members=Counter()
        
        for channel in channels:
            messages=await channel.history(limit=None, after=seven_days_ago).flatten() 
            #async for message in ctx.channel.history(limit=None,after=seven_days_ago):
            async for message in messages:
                count_messages_by_members[message.author]+=1
        

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
             embed_content=embed_content+f"{idx}. {i[0].name}\n"
        
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