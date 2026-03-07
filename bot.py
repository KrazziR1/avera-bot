import discord
from discord.ext import commands
import aiohttp
import json
import os
from datetime import datetime

# ============================================================
#  AVERA CLAN BOT - Configuration
#  Edit these values to customize your bot!
# ============================================================

PREFIX = "!"  # Change this if you want a different command prefix

CLAN_NAME = "Avera"

CLAN_RULES = """
**📜 Avera Clan Rules**

We like to keep it pretty relaxed here at Avera.

1. Maintain respect for all members of the clan at all times
2. Friendly banter is encouraged, drama and toxicity is not
3. Do not scam, mislead, lure or disrespect other clan members
4. Do not promote outside communities, clans or discords
5. Abide by all rules set by discord and Jagex
6. Most importantly, enjoy yourself

"""

CLAN_INFO = """
**⚔️ About Avera**

Welcome to **Avera**, We are a brand new clan established in March of 2026!

🏰 **Focus:** Creating an engaging environment for everyone to enjoy
🌍 **World:** Ask an admin for our clan world!
📅 **Events:** Held weekly — check #events for details
💬 **Discord:** You're already here!

**Ranks:**
👤 Recruit → 🗡️ Corporal → ⚔️ Sergeant → 🛡️ Lieutenant → 👑 General → 🌟 Admin

*Earn ranks by being active, attending events, and contributing to the clan!*
"""

# ============================================================
#  BOT SETUP
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# In-memory points storage (resets on restart — see README for persistent option)
points_data = {}

# ============================================================
#  EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} is online and ready!")
    print(f"   Serving {len(bot.guilds)} server(s)")
    await bot.change_presence(activity=discord.Game(name="Old School RuneScape | !help"))

@bot.event
async def on_member_join(member):
    """Sends a welcome message when a new member joins."""
    # Try to find a channel named 'welcome' or 'general', otherwise use the first available
    channel = discord.utils.get(member.guild.text_channels, name="welcome") or \
              discord.utils.get(member.guild.text_channels, name="general") or \
              member.guild.system_channel

    if channel:
        embed = discord.Embed(
            title=f"⚔️ Welcome to {CLAN_NAME}!",
            description=(
                f"Hey {member.mention}, welcome to the **{CLAN_NAME}** clan Discord! 🎉\n\n"
                f"We're an OSRS clan focused on having fun and progressing together.\n\n"
                f"📜 Read our rules with `!rules`\n"
                f"ℹ️ Learn about us with `!info`\n"
                f"📊 Check your stats with `!stats <username>`\n"
                f"❓ See all commands with `!help`\n\n"
                f"*Grats on joining — may your drops be plentiful!* 🍀"
            ),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{CLAN_NAME} Clan • {datetime.now().strftime('%Y-%m-%d')}")
        await channel.send(embed=embed)

# ============================================================
#  COMMANDS
# ============================================================

@bot.command(name="help")
async def help_command(ctx):
    """Shows all available bot commands."""
    embed = discord.Embed(
        title=f"⚔️ {CLAN_NAME} Bot Commands",
        description=f"Use `{PREFIX}<command>` to run a command.",
        color=discord.Color.gold()
    )
    embed.add_field(name="📋 Clan Info", value=(
        f"`{PREFIX}info` — About the clan\n"
        f"`{PREFIX}rules` — View clan rules"
    ), inline=False)
    embed.add_field(name="📊 OSRS Stats", value=(
        f"`{PREFIX}stats <username>` — Look up any OSRS player's stats\n"
        f"`{PREFIX}kc <username>` — Look up boss kill counts"
    ), inline=False)
    embed.add_field(name="📅 Events", value=(
        f"`{PREFIX}events` — View upcoming clan events\n"
        f"`{PREFIX}addevent <details>` — Add an event *(Admin only)*"
    ), inline=False)
    embed.add_field(name="🏆 Points & Ranks", value=(
        f"`{PREFIX}points [@member]` — Check your (or someone's) points\n"
        f"`{PREFIX}addpoints @member <amount>` — Add points *(Admin only)*\n"
        f"`{PREFIX}leaderboard` — View top 10 clan members by points"
    ), inline=False)
    embed.set_footer(text=f"{CLAN_NAME} Clan Bot")
    await ctx.send(embed=embed)


@bot.command(name="rules")
async def rules(ctx):
    """Displays clan rules."""
    embed = discord.Embed(description=CLAN_RULES, color=discord.Color.red())
    embed.set_footer(text=f"{CLAN_NAME} Clan")
    await ctx.send(embed=embed)


@bot.command(name="info")
async def info(ctx):
    """Displays clan info."""
    embed = discord.Embed(description=CLAN_INFO, color=discord.Color.blue())
    embed.set_footer(text=f"{CLAN_NAME} Clan")
    await ctx.send(embed=embed)


@bot.command(name="stats")
async def stats(ctx, *, username: str = None):
    """Look up OSRS stats for a player. Usage: !stats <username>"""
    if not username:
        await ctx.send("❌ Please provide a username. Example: `!stats Zezima`")
        return

    await ctx.send(f"🔍 Looking up stats for **{username}**...")

    url = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={username.replace(' ', '%20')}"

    skill_names = [
        "Overall", "Attack", "Defence", "Strength", "Hitpoints", "Ranged",
        "Prayer", "Magic", "Cooking", "Woodcutting", "Fletching", "Fishing",
        "Firemaking", "Crafting", "Smithing", "Mining", "Herblore", "Agility",
        "Thieving", "Slayer", "Farming", "Runecrafting", "Hunter", "Construction"
    ]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 404:
                    await ctx.send(f"❌ Player **{username}** not found on the hiscores.")
                    return
                if response.status != 200:
                    await ctx.send("❌ Could not reach the OSRS hiscores right now. Try again later.")
                    return

                text = await response.text()
                lines = text.strip().split("\n")

                embed = discord.Embed(
                    title=f"📊 {username}'s OSRS Stats",
                    color=discord.Color.green(),
                    url=f"https://secure.runescape.com/m=hiscore_oldschool/hiscorepersonal.ws?user1={username.replace(' ', '+')}"
                )

                # Overall stats
                overall = lines[0].split(",")
                total_level = overall[1]
                total_xp = f"{int(overall[2]):,}" if overall[2] != "-1" else "N/A"

                embed.add_field(
                    name="🌟 Overall",
                    value=f"**Level:** {total_level}\n**XP:** {total_xp}",
                    inline=False
                )

                # Combat stats (Attack, Defence, Strength, HP, Ranged, Prayer, Magic)
                combat_stats = ""
                combat_indices = [1, 2, 3, 4, 5, 6, 7]
                for i in combat_indices:
                    if i < len(lines):
                        parts = lines[i].split(",")
                        level = parts[1] if parts[1] != "-1" else "N/A"
                        combat_stats += f"**{skill_names[i]}:** {level}\n"

                embed.add_field(name="⚔️ Combat Skills", value=combat_stats, inline=True)

                # Gathering/artisan stats
                other_stats = ""
                other_indices = [8, 9, 11, 15, 21]  # Cook, WC, Fish, Mine, RC
                for i in other_indices:
                    if i < len(lines):
                        parts = lines[i].split(",")
                        level = parts[1] if parts[1] != "-1" else "N/A"
                        other_stats += f"**{skill_names[i]}:** {level}\n"

                embed.add_field(name="🪓 Gathering Skills", value=other_stats, inline=True)

                embed.set_footer(text="Data from OSRS Hiscores • Avera Clan")
                await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ An error occurred while fetching stats. Please try again.")
        print(f"Stats error: {e}")


@bot.command(name="kc")
async def kc(ctx, *, username: str = None):
    """Look up boss kill counts for a player. Usage: !kc <username>"""
    if not username:
        await ctx.send("❌ Please provide a username. Example: `!kc Zezima`")
        return

    await ctx.send(f"🔍 Looking up boss KCs for **{username}**...")

    url = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={username.replace(' ', '%20')}"

    # Boss names mapped to their line index in the hiscores API
    boss_map = {
        "Abyssal Sire": 41,
        "Alchemical Hydra": 42,
        "Barrows Chests": 44,
        "Bryophyta": 45,
        "Callisto": 46,
        "Cerberus": 48,
        "Chambers of Xeric": 49,
        "Corp": 52,
        "Dagannoth Rex": 57,
        "Dagannoth Prime": 56,
        "Dagannoth Supreme": 58,
        "Giant Mole": 62,
        "Grotesque Guardians": 63,
        "Hespori": 64,
        "Kalphite Queen": 65,
        "King Black Dragon": 66,
        "Kraken": 67,
        "Kree'Arra": 68,
        "K'ril Tsutsaroth": 69,
        "Mimic": 71,
        "Nex": 72,
        "The Nightmare": 73,
        "Phosani's Nightmare": 74,
        "Obor": 75,
        "Sarachnis": 77,
        "Scorpia": 78,
        "Skotizo": 79,
        "Tempoross": 80,
        "The Gauntlet": 81,
        "Theatre of Blood": 83,
        "Thermonuclear Smoke Devil": 85,
        "TzTok-Jad": 86,
        "Venenatis": 88,
        "Vet'ion": 89,
        "Vorkath": 90,
        "Wintertodt": 91,
        "Zalcano": 92,
        "Zulrah": 93,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 404:
                    await ctx.send(f"❌ Player **{username}** not found on the hiscores.")
                    return
                if response.status != 200:
                    await ctx.send("❌ Could not reach the OSRS hiscores right now. Try again later.")
                    return

                text = await response.text()
                lines = text.strip().split("\n")

                embed = discord.Embed(
                    title=f"💀 {username}'s Boss Kill Counts",
                    color=discord.Color.dark_red(),
                )

                kc_list = []
                for boss_name, idx in boss_map.items():
                    if idx < len(lines):
                        parts = lines[idx].split(",")
                        kc = int(parts[1]) if parts[1] not in ["-1", "0"] else 0
                        if kc > 0:
                            kc_list.append((boss_name, kc))

                if not kc_list:
                    embed.description = f"**{username}** has no recorded boss kills on the hiscores."
                else:
                    kc_list.sort(key=lambda x: x[1], reverse=True)
                    kc_text = "\n".join([f"**{boss}:** {kc:,}" for boss, kc in kc_list[:20]])
                    embed.description = kc_text
                    if len(kc_list) > 20:
                        embed.set_footer(text=f"Showing top 20 of {len(kc_list)} bosses • Avera Clan")
                    else:
                        embed.set_footer(text="Data from OSRS Hiscores • Avera Clan")

                await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ An error occurred while fetching KCs. Please try again.")
        print(f"KC error: {e}")


# ============================================================
#  EVENTS SYSTEM
# ============================================================

clan_events = []  # Stores events as list of dicts

@bot.command(name="events")
async def events_list(ctx):
    """Lists upcoming clan events."""
    if not clan_events:
        embed = discord.Embed(
            title="📅 Upcoming Avera Events",
            description="No events scheduled right now. Check back soon!\n\n*Admins can add events with `!addevent <details>`*",
            color=discord.Color.orange()
        )
    else:
        embed = discord.Embed(
            title="📅 Upcoming Avera Events",
            color=discord.Color.orange()
        )
        for i, event in enumerate(clan_events, 1):
            embed.add_field(
                name=f"Event #{i} — {event['name']}",
                value=f"📅 **Date/Time:** {event['datetime']}\n📝 {event['details']}\n*Added by {event['added_by']}*",
                inline=False
            )
    embed.set_footer(text="Avera Clan")
    await ctx.send(embed=embed)


@bot.command(name="addevent")
@commands.has_permissions(manage_guild=True)
async def add_event(ctx, *, details: str = None):
    """Add a clan event. Usage: !addevent <Name> | <Date/Time> | <Details>
    Example: !addevent Cox Mass | Saturday 8PM EST | Bring your best gear!"""
    if not details:
        await ctx.send("❌ Usage: `!addevent <Name> | <Date/Time> | <Details>`\nExample: `!addevent Cox Mass | Saturday 8PM EST | Bring your best gear!`")
        return

    parts = [p.strip() for p in details.split("|")]
    if len(parts) < 3:
        await ctx.send("❌ Please use the format: `!addevent <Name> | <Date/Time> | <Details>`")
        return

    event = {
        "name": parts[0],
        "datetime": parts[1],
        "details": parts[2],
        "added_by": ctx.author.display_name
    }
    clan_events.append(event)

    embed = discord.Embed(
        title="✅ Event Added!",
        description=f"**{event['name']}** has been added to the events list.",
        color=discord.Color.green()
    )
    embed.add_field(name="Date/Time", value=event['datetime'])
    embed.add_field(name="Details", value=event['details'])
    await ctx.send(embed=embed)


@bot.command(name="removeevent")
@commands.has_permissions(manage_guild=True)
async def remove_event(ctx, number: int = None):
    """Remove an event by its number. Usage: !removeevent <number>"""
    if not number or number < 1 or number > len(clan_events):
        await ctx.send(f"❌ Please provide a valid event number between 1 and {len(clan_events)}. Use `!events` to see the list.")
        return
    removed = clan_events.pop(number - 1)
    await ctx.send(f"✅ Removed event: **{removed['name']}**")


# ============================================================
#  POINTS & RANK SYSTEM
# ============================================================

@bot.command(name="points")
async def check_points(ctx, member: discord.Member = None):
    """Check your points or another member's points. Usage: !points [@member]"""
    target = member or ctx.author
    user_id = str(target.id)
    pts = points_data.get(user_id, 0)

    rank = get_rank(pts)

    embed = discord.Embed(
        title=f"🏆 {target.display_name}'s Points",
        description=f"**Points:** {pts}\n**Rank:** {rank}",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text="Avera Clan Points System")
    await ctx.send(embed=embed)


@bot.command(name="addpoints")
@commands.has_permissions(manage_guild=True)
async def add_points(ctx, member: discord.Member = None, amount: int = None):
    """Add points to a member. Admins only. Usage: !addpoints @member <amount>"""
    if not member or amount is None:
        await ctx.send("❌ Usage: `!addpoints @member <amount>`\nExample: `!addpoints @PlayerName 10`")
        return
    if amount <= 0:
        await ctx.send("❌ Amount must be a positive number.")
        return

    user_id = str(member.id)
    points_data[user_id] = points_data.get(user_id, 0) + amount
    new_total = points_data[user_id]
    rank = get_rank(new_total)

    embed = discord.Embed(
        title="✅ Points Added",
        description=f"Added **{amount}** points to {member.mention}!\n**New Total:** {new_total} points\n**Rank:** {rank}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="removepoints")
@commands.has_permissions(manage_guild=True)
async def remove_points(ctx, member: discord.Member = None, amount: int = None):
    """Remove points from a member. Admins only. Usage: !removepoints @member <amount>"""
    if not member or amount is None:
        await ctx.send("❌ Usage: `!removepoints @member <amount>`")
        return

    user_id = str(member.id)
    current = points_data.get(user_id, 0)
    points_data[user_id] = max(0, current - amount)

    await ctx.send(f"✅ Removed **{amount}** points from {member.mention}. New total: **{points_data[user_id]}**")


@bot.command(name="leaderboard")
async def leaderboard(ctx):
    """Shows the top 10 clan members by points."""
    if not points_data:
        await ctx.send("📊 No points have been awarded yet! Admins can use `!addpoints` to get started.")
        return

    sorted_members = sorted(points_data.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(
        title="🏆 Avera Clan Leaderboard",
        color=discord.Color.gold()
    )

    medals = ["🥇", "🥈", "🥉"]
    leaderboard_text = ""
    for i, (user_id, pts) in enumerate(sorted_members):
        member = ctx.guild.get_member(int(user_id))
        name = member.display_name if member else f"Unknown ({user_id})"
        medal = medals[i] if i < 3 else f"**#{i+1}**"
        leaderboard_text += f"{medal} {name} — **{pts} pts**\n"

    embed.description = leaderboard_text
    embed.set_footer(text="Avera Clan Points System")
    await ctx.send(embed=embed)


def get_rank(points):
    """Returns rank title based on points."""
    if points >= 500:
        return "🌟 Legend"
    elif points >= 250:
        return "👑 General"
    elif points >= 100:
        return "🛡️ Lieutenant"
    elif points >= 50:
        return "⚔️ Sergeant"
    elif points >= 20:
        return "🗡️ Corporal"
    else:
        return "👤 Recruit"


# ============================================================
#  ERROR HANDLING
# ============================================================

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use that command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found. Make sure you @mention them.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ Unknown command. Use `{PREFIX}help` to see available commands.")
    else:
        print(f"Unhandled error: {error}")


# ============================================================
#  RUN THE BOT
# ============================================================

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN environment variable not set!")
    print("   Set your bot token in Railway/Replit environment variables.")
else:
    bot.run(TOKEN)
