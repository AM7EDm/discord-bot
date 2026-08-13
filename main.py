import discord
from discord.ext import commands
import os
import random
import asyncio
from flask import Flask
from threading import Thread

# -----------------------------------------------------
#  Keep-alive web server (works on Replit, Render, bot-hosting.net, etc.)
# -----------------------------------------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)

# -----------------------------------------------------
#  Bot setup
# -----------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# تخزين مؤقت (بالذاكرة) - يُمسح إذا أعيد تشغيل البوت
warnings = {}
message_count = {}
event_participants = []


@bot.event
async def on_ready():
    print(f'{bot.user} is now online!')


@bot.event
async def on_message(message):
    if message.author.bot:
        await bot.process_commands(message)
        return

    user_id = message.author.id
    message_count[user_id] = message_count.get(user_id, 0) + 1

    await bot.process_commands(message)


# =======================================================
#  أوامر الإدارة (Admin only)
# =======================================================

@bot.command()
@commands.has_permissions(administrator=True)
async def mute(ctx, member: discord.Member = None, duration: int = None):
    if member is None:
        await ctx.send("الرجاء ذكر العضو المطلوب كتمه")
        return
    voice_client = ctx.guild.voice_client
    if voice_client:
        voice_client.pause()
        await ctx.send("تم كتم الصوت")
        if duration:
            await asyncio.sleep(duration)
            voice_client.resume()
            await ctx.send("تم إلغاء الكتم تلقائياً")


@bot.command()
@commands.has_permissions(administrator=True)
async def unmute(ctx):
    voice_client = ctx.guild.voice_client
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await ctx.send("تم إلغاء الكتم")
    else:
        await ctx.send("لا يوجد شيء متوقف حالياً")


@bot.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        await ctx.send("الرجاء ذكر العضو المطلوب طرده")
        return
    await member.kick(reason=reason)
    await ctx.send(f"تم طرد {member.mention}")


@bot.command()
@commands.has_permissions(administrator=True)
async def warn(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        await ctx.send("الاستخدام الصحيح: `!warn @عضو سبب_التحذير`")
        return

    warnings.setdefault(member.id, []).append(reason or "بدون سبب محدد")
    warn_count = len(warnings[member.id])

    embed = discord.Embed(
        title="⚠️ تحذير جديد",
        description=f"{member.mention} حصل على تحذير رقم **{warn_count}**",
        color=discord.Color.orange()
    )
    embed.add_field(name="السبب", value=reason or "بدون سبب محدد", inline=False)
    embed.add_field(name="📌 ملاحظة", value="لمشاهدة كل تحذيرات العضو اكتب `!warnings @عضو`", inline=False)
    await ctx.send(embed=embed)

    try:
        await member.send(
            f"⚠️ حصلت على تحذير بسيرفر **{ctx.guild.name}**\n"
            f"السبب: {reason or 'بدون سبب محدد'}\nعدد تحذيراتك: {warn_count}"
        )
    except discord.Forbidden:
        pass

    if warn_count >= 3:
        await ctx.send(f"🚫 {member.mention} وصل لـ 3 تحذيرات، جاري الطرد التلقائي...")
        try:
            await member.kick(reason="وصل للحد الأقصى من التحذيرات (3)")
            warnings[member.id] = []
        except discord.Forbidden:
            await ctx.send("⚠️ ما قدرت أطرد العضو، تأكد من صلاحيات البوت")


@bot.command(name="warnings")
@commands.has_permissions(administrator=True)
async def warnings_list(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("الاستخدام الصحيح: `!warnings @عضو`")
        return

    member_warnings = warnings.get(member.id, [])
    if not member_warnings:
        await ctx.send(f"{member.mention} ما عنده أي تحذيرات ✅")
        return

    embed = discord.Embed(
        title=f"⚠️ تحذيرات {member.display_name}",
        description=f"العدد الكلي: {len(member_warnings)}",
        color=discord.Color.orange()
    )
    for i, reason in enumerate(member_warnings, 1):
        embed.add_field(name=f"تحذير {i}", value=reason, inline=False)

    embed.add_field(
        name="📌 ملاحظة",
        value="لإزالة تحذير معين اكتب `!unwarn @عضو رقم` أو لمسح الكل `!clearwarns @عضو`",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def unwarn(ctx, member: discord.Member = None, warn_number: int = None):
    if member is None or warn_number is None:
        await ctx.send("الاستخدام الصحيح: `!unwarn @عضو رقم_التحذير`\nمثال: `!unwarn @أحمد 2`")
        return

    member_warnings = warnings.get(member.id, [])
    if not member_warnings:
        await ctx.send(f"{member.mention} ما عنده أي تحذيرات أساساً ✅")
        return

    if warn_number < 1 or warn_number > len(member_warnings):
        await ctx.send(f"⚠️ رقم غير صحيح، {member.mention} عنده {len(member_warnings)} تحذيرات فقط")
        return

    removed_reason = member_warnings.pop(warn_number - 1)

    embed = discord.Embed(
        title="✅ تم إلغاء التحذير",
        description=f"تم حذف التحذير رقم **{warn_number}** من {member.mention}",
        color=discord.Color.green()
    )
    embed.add_field(name="التحذير المحذوف", value=removed_reason, inline=False)
    embed.add_field(
        name="📌 ملاحظة",
        value=f"باقي عنده {len(member_warnings)} تحذيرات، اكتب `!warnings @عضو` لمشاهدتها",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def clearwarns(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send("الاستخدام الصحيح: `!clearwarns @عضو`")
        return

    warnings[member.id] = []
    await ctx.send(f"✅ تم مسح كل تحذيرات {member.mention}")


@bot.command()
@commands.has_permissions(administrator=True)
async def clear(ctx, amount: int = None):
    if amount is None:
        await ctx.send("الاستخدام الصحيح: `!clear عدد_الرسائل`\nمثال: `!clear 10`")
        return

    if amount < 1 or amount > 100:
        await ctx.send("⚠️ العدد لازم يكون بين 1 و 100")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)
    confirm_msg = await ctx.send(
        f"✅ تم حذف **{len(deleted) - 1}** رسالة\n"
        f"📌 ملاحظة: هذي الرسالة رح تختفي تلقائياً بعد 5 ثواني"
    )
    await asyncio.sleep(5)
    await confirm_msg.delete()


@bot.command()
@commands.has_permissions(administrator=True)
async def helpadmin(ctx):
    embed = discord.Embed(
        title="🛡️ قائمة أوامر الإدارة",
        description="هذي الأوامر الخاصة بالمشرفين فقط:",
        color=discord.Color.red()
    )
    embed.add_field(
        name="🔧 أوامر الإشراف",
        value=(
            "`!mute @عضو [مدة بالثواني]` - كتم عضو بالصوت\n"
            "`!unmute` - إلغاء الكتم\n"
            "`!kick @عضو [سبب]` - طرد عضو\n"
            "`!clear [عدد]` - مسح رسائل"
        ),
        inline=False
    )
    embed.add_field(
        name="⚠️ أوامر التحذيرات",
        value=(
            "`!warn @عضو [سبب]` - إضافة تحذير (3 تحذيرات = طرد تلقائي)\n"
            "`!warnings @عضو` - عرض كل تحذيرات العضو\n"
            "`!unwarn @عضو [رقم]` - حذف تحذير معين\n"
            "`!clearwarns @عضو` - حذف كل التحذيرات"
        ),
        inline=False
    )
    embed.set_footer(text="🔒 هذا الأمر يظهر للمشرفين فقط")
    await ctx.send(embed=embed)


@helpadmin.error
async def helpadmin_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("⛔ عذراً، هذا الأمر مخصص للمشرفين فقط.")


# =======================================================
#  أوامر الأعضاء (Everyone)
# =======================================================

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📋 قائمة أوامر الأعضاء",
        description="هذي الأوامر المتاحة لجميع الأعضاء:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🎮 أوامر الألعاب",
        value="`!team [عدد الفرق] @عضو1 @عضو2...` - قرعة فرق عشوائية",
        inline=False
    )
    embed.add_field(
        name="🎵 أوامر الموسيقى",
        value="`!play [اسم الأغنية]` - تشغيل أغنية",
        inline=False
    )
    embed.add_field(
        name="🎉 أوامر الإيفنت",
        value="`!event [اسم] [دقائق]` - إنشاء إيفنت بوقت محدد",
        inline=False
    )
    embed.add_field(
        name="📊 الإحصائيات",
        value="`!top [عدد]` - لوحة الأعضاء الأكثر نشاطاً",
        inline=False
    )
    embed.set_footer(text="🤖 البوت شغال 24/7 لخدمتكم")
    await ctx.send(embed=embed)


@bot.command()
async def team(ctx, num_teams: int = None, *members: discord.Member):
    if num_teams is None or len(members) < num_teams:
        await ctx.send(
            "الاستخدام الصحيح: `!team عدد_الفرق @شخص1 @شخص2 @شخص3...`\n"
            "مثال: `!team 3 @أحمد @سالم @خالد @فهد @علي @ياسر`"
        )
        return

    if num_teams < 2:
        await ctx.send("لازم تحدد فريقين على الأقل!")
        return

    members_list = list(members)
    random.shuffle(members_list)

    teams = [[] for _ in range(num_teams)]
    for i, member in enumerate(members_list):
        teams[i % num_teams].append(member)

    colors = ["🔵", "🔴", "🟢", "🟡", "🟣", "⚪", "🟠", "🟤"]
    embed = discord.Embed(title=f"🎲 نتيجة القرعة ({num_teams} فرق)", color=discord.Color.gold())

    for i, team_members in enumerate(teams):
        color_emoji = colors[i % len(colors)]
        team_text = "\n".join([m.mention for m in team_members]) or "لا يوجد"
        embed.add_field(name=f"{color_emoji} الفريق {i+1}", value=team_text, inline=True)

    embed.add_field(
        name="📌 ملاحظة",
        value="تبي قرعة جديدة؟ اكتب `!team` مرة ثانية بنفس الأعضاء",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command()
async def event(ctx, name: str = None, minutes: int = None):
    global event_participants
    if name is None or minutes is None:
        await ctx.send(
            "الاستخدام الصحيح: `!event اسم_الإيفنت الوقت_بالدقائق`\n"
            "مثال: `!event بطولة_فالورانت 30`"
        )
        return

    event_participants = []
    await ctx.send(
        f"📢 تم إنشاء إيفنت **{name}**! يبدأ بعد **{minutes} دقيقة**.\n"
        f"📌 ملاحظة: اللي يبي ينضم يكتب `!eventjoin`"
    )

    await asyncio.sleep(minutes * 60)

    if len(event_participants) < 2:
        await ctx.send(f"⚠️ ما فيه عدد كافي للفرق بإيفنت **{name}** (لازم عضوين على الأقل انضموا).")
        return

    participants_copy = event_participants.copy()
    random.shuffle(participants_copy)
    mid = len(participants_copy) // 2
    team_a = participants_copy[:mid]
    team_b = participants_copy[mid:]

    embed = discord.Embed(title=f"🎉 بدأ إيفنت {name}! نتيجة القرعة:", color=discord.Color.gold())
    embed.add_field(name="🔵 الفريق الأزرق", value="\n".join([m.mention for m in team_a]) or "لا يوجد", inline=True)
    embed.add_field(name="🔴 الفريق الأحمر", value="\n".join([m.mention for m in team_b]) or "لا يوجد", inline=True)
    await ctx.send(content="@everyone", embed=embed)

    for member in participants_copy:
        try:
            await member.send(f"🎉 بدأ إيفنت **{name}** الحين بسيرفر **{ctx.guild.name}**!")
        except discord.Forbidden:
            pass


@bot.command()
async def eventjoin(ctx):
    global event_participants
    if ctx.author in event_participants:
        await ctx.send(f"{ctx.author.mention} انت مسجل بالفعل! ✅")
        return
    event_participants.append(ctx.author)
    await ctx.send(f"✅ {ctx.author.mention} انضم للإيفنت! (العدد الحالي: {len(event_participants)})")


@bot.command()
async def top(ctx, amount: int = 10):
    if not message_count:
        await ctx.send("ما فيه أي إحصائيات مسجلة بعد!")
        return

    sorted_users = sorted(message_count.items(), key=lambda x: x[1], reverse=True)
    top_users = sorted_users[:amount]

    embed = discord.Embed(
        title=f"🏆 أنشط {len(top_users)} أعضاء (حسب عدد الرسائل)",
        color=discord.Color.gold()
    )

    medals = ["🥇", "🥈", "🥉"]
    description = ""
    for i, (user_id, count) in enumerate(top_users):
        member = ctx.guild.get_member(user_id)
        name = member.display_name if member else "عضو غير معروف"
        medal = medals[i] if i < 3 else f"{i+1}."
        description += f"{medal} **{name}** - {count} رسالة\n"

    embed.description = description
    embed.set_footer(text="📌 ملاحظة: الإحصائيات تبدأ من وقت تشغيل البوت")
    await ctx.send(embed=embed)


@bot.command()
async def play(ctx, *, query: str = None):
    if query is None:
        await ctx.send("الاستخدام الصحيح: `!play اسم الأغنية أو رابط`")
        return

    if not ctx.author.voice:
        await ctx.send("لازم تكون بقناة صوتية عشان أشغل الأغنية!")
        return

    voice_channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await voice_channel.connect()

    # ملاحظة: تشغيل الصوت الفعلي يحتاج مكتبة yt-dlp + ffmpeg
    # هذا الهيكل الأساسي جاهز للتوسعة لاحقاً
    await ctx.send(
        f"🎵 جاري البحث عن: **{query}**...\n"
        f"📌 ملاحظة: لإيقاف الأغنية اكتب `!stop`"
    )


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ تم إيقاف الموسيقى وطلع البوت من القناة الصوتية")
    else:
        await ctx.send("البوت مو متصل بأي قناة صوتية حالياً")


# -----------------------------------------------------
#  تشغيل السيرفر + البوت
# -----------------------------------------------------
Thread(target=run_flask).start()
bot.run(os.environ.get("DISCORD_TOKEN"))
