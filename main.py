import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} is now online!')

@bot.command()
async def mute(ctx, member: discord.Member = None, duration: int = None):
    if member is None:
        await ctx.send("الرجاء ذكر العضو المطلوب كتمه")
        return
    voice_client = ctx.guild.voice_client
    if voice_client:
        voice_client.pause()
        await ctx.send("تم كتم الصوت")
        if duration:
            import asyncio
            await asyncio.sleep(duration)
            voice_client.resume()
            await ctx.send("تم إلغاء الكتم تلقائياً")

@bot.command()
async def unmute(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("تم إلغاء الكتم")
    else:
        await ctx.send("لا يوجد شيء متوقف حالياً")

@bot.command()
async def kick(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        await ctx.send("الرجاء ذكر العضو المطلوب طرده")
        return
    await member.kick(reason=reason)
    await ctx.send(f"تم طرد {member.mention}")

Thread(target=run_flask).start()
bot.run(os.environ.get("DISCORD_TOKEN"))
