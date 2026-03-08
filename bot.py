import discord
from discord.ext import commands
import aiohttp
import json
import os
from datetime import datetime
import asyncio
from discord.ext import tasks
import random
from pymongo import MongoClient

# ============================================================
#  AVERA CLAN BOT - Configuration
#  Edit these values to customize your bot!
# ============================================================

PREFIX = "!"  # Change this if you want a different command prefix

CLAN_NAME = "Avera"

CLAN_RULES = """
**📜 Avera Clan Rules**

1. **Be Respectful** — Treat everyone with basic respect.
2. **No Begging, Scamming or PKing Clan Members** — We're a community, not a target.
3. **Keep it Clean** — Avoid excessive toxicity, racism, or hate speech of any kind.
4. **No Drama** — Sort personal issues privately. Don't bring beef into clan chat or Discord.
5. **Stay Reasonably Active** — Real life comes first, but let staff know if you'll be away for a while.
6. **Represent Avera in a Positive Light** — Be a good face for the clan wherever you are.
7. **Clan Events** — Participation is encouraged but never forced. Show up when you can!
8. **No Advertising** — Do not advertise outside communities or clans. Streaming is the only exception.
9. **Have Fun** — This is a game. Enjoy it, help each other out, and don't take it too seriously. 🎮

*For questions or concerns, open a ticket or speak to a staff member.*
"""

CLAN_INFO = """
**⚔️ About Avera**

Welcome to **Avera**, an Old School RuneScape clan built on friendship, fun, and gains!

🏰 **Focus:** PvM, Skilling, and Clan Events
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

# Prevent duplicate command responses
_processed_messages = set()

@bot.before_invoke
async def before_command(ctx):
    if ctx.message.id in _processed_messages:
        raise commands.CheckFailure("duplicate")
    _processed_messages.add(ctx.message.id)
    if len(_processed_messages) > 1000:
        _processed_messages.clear()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure) and "duplicate" in str(error):
        return
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use that command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found. Make sure you @mention them.")
    elif isinstance(error, commands.CommandNotFound):
        return  # Silently ignore unknown commands
    else:
        print(f"Unhandled error: {error}")

# ============================================================
#  DATA PERSISTENCE
# ============================================================


# ============================================================
#  MONGODB PERSISTENCE
# ============================================================

MONGO_URI = os.environ.get("MONGO_URI", "")
_mongo_client = None
_mongo_col = None

def get_mongo_col():
    """Returns the MongoDB collection, creating the connection if needed."""
    global _mongo_client, _mongo_col
    if _mongo_col is None:
        _mongo_client = MongoClient(MONGO_URI)
        db = _mongo_client["avera"]
        _mongo_col = db["bot_data"]
    return _mongo_col


def load_data():
    """Load all persistent data from MongoDB on startup."""
    global points_data, clan_events, bounties, bounty_counter, claim_channels
    global coffer_balance, coffer_donations, coffer_payouts, active_giveaways
    global verified_rsns, verify_times, referrals, event_streaks, shop_redemptions, member_ranks
    global announced_milestones, dashboard_message_id, weekly_stats

    try:
        col = get_mongo_col()
        doc = col.find_one({"_id": "avera_data"})
        if not doc:
            print("📂 No data found in MongoDB — starting fresh.")
            return

        points_data = doc.get("points_data", {})
        clan_events = doc.get("clan_events", [])
        bounties = {int(k): v for k, v in doc.get("bounties", {}).items()}
        bounty_counter = doc.get("bounty_counter", 0)
        claim_channels = {int(k): v for k, v in doc.get("claim_channels", {}).items()}
        coffer_balance = doc.get("coffer_balance", 0)
        coffer_donations = doc.get("coffer_donations", [])
        coffer_payouts = doc.get("coffer_payouts", [])
        active_giveaways = doc.get("active_giveaways", [])
        verified_rsns = doc.get("verified_rsns", {})
        verify_times = doc.get("verify_times", {})
        member_ranks = doc.get("member_ranks", {})
        referrals = doc.get("referrals", {})
        event_streaks = doc.get("event_streaks", {})
        shop_redemptions = doc.get("shop_redemptions", [])
        announced_milestones = set(doc.get("announced_milestones", []))
        dashboard_message_id = doc.get("dashboard_message_id", None)
        weekly_stats.update(doc.get("weekly_stats", {}))

        print(f"✅ Data loaded from MongoDB — {len(points_data)} members, coffer: {coffer_balance:,} gp")
    except Exception as e:
        print(f"⚠️ Failed to load data from MongoDB: {e}")


def save_data():
    """Save all persistent data to MongoDB."""
    try:
        col = get_mongo_col()
        data = {
            "_id": "avera_data",
            "points_data": points_data,
            "clan_events": clan_events,
            "bounties": {str(k): v for k, v in bounties.items()},
            "bounty_counter": bounty_counter,
            "claim_channels": {str(k): v for k, v in claim_channels.items()},
            "coffer_balance": coffer_balance,
            "coffer_donations": coffer_donations,
            "coffer_payouts": coffer_payouts,
            "active_giveaways": active_giveaways,
            "verified_rsns": verified_rsns,
            "verify_times": verify_times,
            "member_ranks": member_ranks,
            "referrals": referrals,
            "event_streaks": event_streaks,
            "shop_redemptions": shop_redemptions,
            "announced_milestones": list(announced_milestones),
            "dashboard_message_id": dashboard_message_id,
            "weekly_stats": weekly_stats,
        }
        col.replace_one({"_id": "avera_data"}, data, upsert=True)
    except Exception as e:
        print(f"⚠️ Failed to save data to MongoDB: {e}")




# Points storage — loaded from file on startup
points_data = {}

# ============================================================
#  EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ {bot.user.name} is online and ready!")
    print(f"   Serving {len(bot.guilds)} server(s)")
    await bot.change_presence(activity=discord.Game(name="Old School RuneScape | !help"))
    # Load persistent data
    load_data()
    # Re-register persistent views so buttons keep working after restarts
    bot.add_view(TicketPanel())
    bot.add_view(CloseTicketView())
    bot.add_view(AccountRoleView())
    bot.add_view(RegionRoleView())
    bot.add_view(RaidRoleView())
    bot.add_view(DashboardView())
    bot.add_view(ShopView())
    # Start background tasks
    if not weekly_recap.is_running():
        weekly_recap.start()
    if not check_member_milestones.is_running():
        check_member_milestones.start()
    if not auto_save.is_running():
        auto_save.start()
    if not auto_dashboard_refresh.is_running():
        auto_dashboard_refresh.start()
    if not daily_rankup_check.is_running():
        daily_rankup_check.start()

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
                f"✅ Link your RSN with `!verify <username>`\n"
                f"📜 Read our rules with `!rules` or check <#{RULES_CHANNEL_ID}>\n"
                f"🎯 Check active bounties with `!bounties` in <#{BOUNTY_CHANNEL_ID}>\n"
                f"🛒 Browse the clan shop with `!shop`\n"
                f"📊 View the clan dashboard with `!dashboard`\n"
                f"❓ See all commands with `!help`\n\n"
                f"*Grats on joining — may your drops be plentiful!* 🍀"
            ),
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{CLAN_NAME} Clan • {datetime.now().strftime('%Y-%m-%d')}")
        await channel.send(embed=embed)

# ============================================================
#  WELCOME CHANNEL GUARD
# ============================================================

@bot.event
async def on_message(message):
    """Delete any message in the welcome channel that isn't !verify or from an admin/bot."""
    # Always process commands first
    await bot.process_commands(message)

    # Ignore messages from bots
    if message.author.bot:
        return

    # Only police the welcome channel
    if message.channel.id != WELCOME_PANEL_CHANNEL_ID:
        return

    # Let admins say whatever they want
    if message.author.guild_permissions.manage_guild:
        return

    # Allow !verify commands — they're handled by the verify command itself
    if message.content.lower().startswith(f"{PREFIX}verify"):
        return

    # Delete everything else
    try:
        await message.delete()
    except discord.NotFound:
        pass

    # Send a subtle reminder that auto-deletes after 7 seconds
    try:
        reminder = await message.channel.send(
            f"👋 {message.author.mention} — this channel is for verification only. "
            f"Please use `!verify <your OSRS username>` to get started!",
        )
        await asyncio.sleep(7)
        await reminder.delete()
    except discord.NotFound:
        pass

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
        f"`{PREFIX}addevent <details>` — Add an event *(Admin only)*\n"
        f"`{PREFIX}startattendance <#> [@host] [pts]` — Open attendance, optionally tag a host with points *(Admin only)*\n"
        f"`{PREFIX}attend` — Check in to the active event\n"
        f"`{PREFIX}attendance` — See who has checked in\n"
        f"`{PREFIX}endattendance` — Close attendance & post summary *(Admin only)*"
    ), inline=False)
    embed.add_field(name="🏆 Points & Ranks", value=(
        f"`{PREFIX}points [@member]` — Check your (or someone's) points\n"
        f"`{PREFIX}addpoints @member <amount>` — Add points *(Admin only)*\n"
        f"`{PREFIX}awardplacement <1/2/3> @member <event>` — Award placement points *(Admin only)*\n"
        f"`{PREFIX}leaderboard` — View top 10 clan members by points\n"
        f"`{PREFIX}clanstats` — Full clan snapshot\n"
        f"`{PREFIX}profile [@member]` — View a member's full clan profile\n"
        f"`{PREFIX}compare @member1 @member2` — Compare two members side by side\n"
        f"`{PREFIX}rankcheck [@member]` — Check & update your rank\n"
        f"`{PREFIX}assignrank @member <rank>` — Assign admin rank *(Admin only)*\n"
        f"`{PREFIX}removerank @member` — Remove admin rank *(Admin only)*\n"
        f"`{PREFIX}rankupdate` — Recalculate all ranks *(Admin only)*"
    ), inline=False)
    embed.add_field(name="🎯 Bounties", value=(
        f"`{PREFIX}bounties` — View all active bounties\n"
        f"`{PREFIX}claim <id>` — Claim a bounty (attach screenshot!)\n"
        f"`{PREFIX}bounty <target> <points> <desc>` — Create bounty *(Admin only)*\n"
        f"`{PREFIX}approveclaim <id>` — Approve a claim *(Admin only)*\n"
        f"`{PREFIX}denyclaim <id>` — Deny a claim *(Admin only)*\n"
        f"`{PREFIX}cancelbounty <id>` — Cancel a bounty *(Admin only)*"
    ), inline=False)
    embed.add_field(name="🎫 Tickets", value=(
        f"`{PREFIX}ticketpanel` — Post the support panel *(Admin only)*\n"
        f"`{PREFIX}closeticket` — Close the current ticket"
    ), inline=False)
    embed.add_field(name="🎭 Roles", value=(
        f"`{PREFIX}rolepanel` — Post the role selection panels *(Admin only)*"
    ), inline=False)
    embed.add_field(name="🏰 Dashboard & Coffer", value=(
        f"`{PREFIX}dashboard` — Post/refresh the clan dashboard *(Admin only)*\n"
        f"`{PREFIX}cofferdeposit @member <amount> [note]` — Log a donation *(Admin only)*\n"
        f"`{PREFIX}cofferpayout <amount> <reason>` — Log a payout *(Admin only)*\n"
        f"`{PREFIX}cofferbalance` — Check the current coffer balance\n"
        f"`{PREFIX}addgiveaway <prize> | <end>` — Add a giveaway to dashboard *(Admin only)*\n"
        f"`{PREFIX}endgiveaway <number>` — Remove a giveaway from dashboard *(Admin only)*\n"
        f"`{PREFIX}giveaway <duration> <prize>` — Start a live giveaway *(Admin only)*\n"
        f"`{PREFIX}rerollgiveaway <message_id>` — Reroll a giveaway winner *(Admin only)*"
    ), inline=False)
    embed.add_field(name="🛒 Clan Shop", value=(
        f"`{PREFIX}shop` — Browse the clan shop\n"
        f"`{PREFIX}redeem <#>` — Redeem an item with points\n"
        f"`{PREFIX}shopanel` — Post a permanent shop panel *(Admin only)*\n"
        f"`{PREFIX}redemptions` — View pending redemptions *(Admin only)*\n"
        f"`{PREFIX}fulfil <#>` — Mark a redemption as done *(Admin only)*"
    ), inline=False)
    embed.add_field(name="📣 Other", value=(
        f"`{PREFIX}verifypanel` — Post the verification panel *(Admin only)*\n"
        f"`{PREFIX}welcomepanel` — Post the welcome panel *(Admin only)*\n"
        f"`{PREFIX}bountypanel` — Post the bounty info panel *(Admin only)*\n"
        f"`{PREFIX}rulespanel` — Post the rules panel *(Admin only)*\n"
        f"`{PREFIX}faqpanel` — Post the FAQ panel *(Admin only)*\n"
        f"`{PREFIX}dinkpanel` — Post the Dink setup guide *(Admin only)*"
    ), inline=False)
    embed.add_field(name="📊 Polls", value=(
        f"`{PREFIX}poll <mins> <question> | <opt1> | <opt2>` — Create a poll *(Admin only)*"
    ), inline=False)
    embed.add_field(name="🔥 Streaks & Verify", value=(
        f"`{PREFIX}streak [@member]` — Check event attendance streak\n"
        f"`{PREFIX}verify <rsn>` — Link your OSRS username\n"
        f"`{PREFIX}whoami` — Check your verified RSN\n"
        f"`{PREFIX}whois @member` — Look up a member\'s RSN\n"
        f"`{PREFIX}referral @member` — Credit someone for referring you"
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
#  ATTENDANCE TRACKING
# ============================================================

EVENTS_CHANNEL_ID = 1479914219888578632
ATTENDANCE_POINTS = 5

# Tracks the currently active attendance session
active_attendance = None


@bot.command(name="startattendance")
@commands.has_permissions(manage_guild=True)
async def start_attendance(ctx, event_number: int = None, host: discord.Member = None, host_points: int = None):
    """Start attendance tracking for an event. Admin only.
    Usage: !startattendance <event number> [@host] [host points]
    Example: !startattendance 1 @Jerzi 25"""
    global active_attendance

    if active_attendance:
        await ctx.send(
            f"❌ Attendance is already open for **{active_attendance['event_name']}**!\n"
            f"Use `!endattendance` to close it first."
        )
        return

    if event_number is None:
        await ctx.send(
            "❌ Please provide an event number. Example: `!startattendance 1`\n"
            "To tag a host with points: `!startattendance 1 @Jerzi 25`\n"
            "Use `!events` to see the list."
        )
        return

    if event_number < 1 or event_number > len(clan_events):
        await ctx.send("❌ Invalid event number. Use `!events` to see available events.")
        return

    # If host is tagged but no points given, ask admin to specify
    if host and host_points is None:
        await ctx.send(
            f"❌ Please specify how many points **{host.display_name}** should receive for hosting.\n"
            f"Example: `!startattendance {event_number} {host.mention} 25`"
        )
        return

    if host_points is not None and host_points < 0:
        await ctx.send("❌ Host points must be a positive number.")
        return

    event = clan_events[event_number - 1]
    active_attendance = {
        "event_name": event["name"],
        "event_details": event["details"],
        "attendees": {},
        "started_by": ctx.author.display_name,
        "host_id": str(host.id) if host else None,
        "host_name": host.display_name if host else None
    }

    # Award host points immediately
    host_text = ""
    if host and host_points:
        host_id = str(host.id)
        points_data[host_id] = points_data.get(host_id, 0) + host_points
        weekly_stats["points_awarded"] += host_points
        weekly_stats["weekly_points"][host_id] = weekly_stats["weekly_points"].get(host_id, 0) + host_points
        host_text = f"\n🌟 **Hosted by {host.display_name}** — +{host_points} pts awarded for organising!"

    events_channel = bot.get_channel(EVENTS_CHANNEL_ID)

    embed = discord.Embed(
        title=f"📋 Attendance Open — {event['name']}!",
        description=(
            f"The event **{event['name']}** is starting!\n\n"
            f"📝 {event['details']}\n\n"
            f"Type `!attend` to mark yourself as present and earn **{ATTENDANCE_POINTS} points**! 🎉"
            + host_text +
            f"\n\n*Attendance will be closed by an admin when the event ends.*"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Started by {ctx.author.display_name}")
    embed.timestamp = datetime.now()

    if events_channel:
        await events_channel.send("@everyone", embed=embed)

    if ctx.channel.id != EVENTS_CHANNEL_ID:
        host_confirm = f" Host: **{host.display_name}** (+{host_points} pts)" if host else " No host tagged."
        await ctx.send(f"✅ Attendance tracking started for **{event['name']}**!{host_confirm} Members can now type `!attend`.")


@bot.command(name="attend")
async def attend(ctx):
    """Mark yourself as present for the current event. Usage: !attend"""
    global active_attendance

    if not active_attendance:
        await ctx.send("❌ There is no active event right now. Keep an eye on the events channel!")
        return

    user_id = str(ctx.author.id)

    if user_id in active_attendance["attendees"]:
        await ctx.send(f"✅ {ctx.author.mention} you're already marked as present for **{active_attendance['event_name']}**!")
        return

    # Log the attendee and award points
    active_attendance["attendees"][user_id] = ctx.author.display_name
    points_data[user_id] = points_data.get(user_id, 0) + ATTENDANCE_POINTS
    new_total = points_data[user_id]
    rank = get_rank_display(get_rank(new_total, user_id))

    # Update weekly stats
    weekly_stats["points_awarded"] += ATTENDANCE_POINTS
    weekly_stats["weekly_points"][user_id] = weekly_stats["weekly_points"].get(user_id, 0) + ATTENDANCE_POINTS

    # Check streak
    streak, bonus = update_streak(user_id, ctx.author.display_name)
    streak_text = ""
    if bonus > 0:
        points_data[user_id] += bonus
        new_total = points_data[user_id]
        weekly_stats["points_awarded"] += bonus
        weekly_stats["weekly_points"][user_id] = weekly_stats["weekly_points"].get(user_id, 0) + bonus
        streak_text = f"\n🔥 **{streak}-event streak!** Bonus **+{bonus} pts** awarded!"

    embed = discord.Embed(
        description=(
            f"✅ {ctx.author.mention} has checked in to **{active_attendance['event_name']}**!\n"
            f"**+{ATTENDANCE_POINTS} points** awarded! *(Total: {new_total} — {rank})*"
            + streak_text
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


@bot.command(name="attendance")
async def check_attendance(ctx):
    """Check who has checked in to the current event."""
    if not active_attendance:
        await ctx.send("❌ There is no active event right now.")
        return

    attendees = active_attendance["attendees"]
    count = len(attendees)

    embed = discord.Embed(
        title=f"📋 Attendance — {active_attendance['event_name']}",
        color=discord.Color.orange()
    )

    if not attendees:
        embed.description = "Nobody has checked in yet! Members can type `!attend` to join."
    else:
        names = "\n".join([f"✅ {name}" for name in attendees.values()])
        embed.description = names
        embed.set_footer(text=f"{count} member{'s' if count != 1 else ''} checked in so far")

    await ctx.send(embed=embed)


@bot.command(name="endattendance")
@commands.has_permissions(manage_guild=True)
async def end_attendance(ctx):
    """Close attendance and post a summary. Admin only. Usage: !endattendance"""
    global active_attendance

    if not active_attendance:
        await ctx.send("❌ There is no active attendance session to end.")
        return

    attendees = active_attendance["attendees"]
    event_name = active_attendance["event_name"]
    count = len(attendees)

    events_channel = bot.get_channel(EVENTS_CHANNEL_ID)

    embed = discord.Embed(
        title=f"🏁 Event Over — {event_name}",
        description=(
            f"Attendance for **{event_name}** is now closed!\n\n"
            f"**{count} member{'s' if count != 1 else ''}** attended and each earned **{ATTENDANCE_POINTS} points**. 🎉"
        ),
        color=discord.Color.gold()
    )

    if attendees:
        names = "\n".join([f"✅ {name}" for name in attendees.values()])
        embed.add_field(name="Attendees", value=names, inline=False)
    else:
        embed.add_field(name="Attendees", value="No one checked in.", inline=False)

    embed.set_footer(text=f"Closed by {ctx.author.display_name}")
    embed.timestamp = datetime.now()

    if events_channel:
        await events_channel.send(embed=embed)

    if ctx.channel.id != EVENTS_CHANNEL_ID:
        await ctx.send(f"✅ Attendance closed for **{event_name}**. Summary posted in <#{EVENTS_CHANNEL_ID}>.")

    # Update weekly stats
    weekly_stats["events_held"] += 1
    active_attendance = None


# ============================================================
#  POINTS & RANK SYSTEM
# ============================================================

@bot.command(name="points")
async def check_points(ctx, member: discord.Member = None):
    """Check your points or another member's points. Usage: !points [@member]"""
    target = member or ctx.author
    user_id = str(target.id)
    pts = points_data.get(user_id, 0)

    rank = get_rank_display(get_rank(pts, user_id))

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
    rank = get_rank_display(get_rank(new_total, user_id))

    save_data()
    embed = discord.Embed(
        title="✅ Points Added",
        description=f"Added **{amount}** points to {member.mention}!\n**New Total:** {new_total} points\n**Rank:** {rank}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


# Placement points: 1st = 10, 2nd = 5, 3rd = 3
PLACEMENT_POINTS = {1: 10, 2: 5, 3: 3}
PLACEMENT_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


@bot.command(name="awardplacement")
@commands.has_permissions(manage_guild=True)
async def award_placement(ctx, placement: int = None, member: discord.Member = None, *, event_name: str = None):
    """Award placement points to a member. Admin only.
    Usage: !awardplacement <1/2/3> @member <event name>
    Example: !awardplacement 1 @Jerzi Skill of the Week"""
    if placement is None or member is None or event_name is None:
        await ctx.send(
            "❌ Usage: `!awardplacement <1/2/3> @member <event name>`\n"
            "Example: `!awardplacement 1 @Jerzi Skill of the Week`\n\n"
            f"**Placement rewards:**\n"
            f"🥇 1st — {PLACEMENT_POINTS[1]} pts\n"
            f"🥈 2nd — {PLACEMENT_POINTS[2]} pts\n"
            f"🥉 3rd — {PLACEMENT_POINTS[3]} pts"
        )
        return

    if placement not in PLACEMENT_POINTS:
        await ctx.send("❌ Placement must be 1, 2, or 3.")
        return

    pts = PLACEMENT_POINTS[placement]
    medal = PLACEMENT_MEDALS[placement]
    user_id = str(member.id)
    points_data[user_id] = points_data.get(user_id, 0) + pts
    new_total = points_data[user_id]
    rank = get_rank_display(get_rank(new_total, user_id))

    # Update weekly stats
    weekly_stats["points_awarded"] += pts
    weekly_stats["weekly_points"][user_id] = weekly_stats["weekly_points"].get(user_id, 0) + pts

    ordinal = {1: "1st", 2: "2nd", 3: "3rd"}[placement]

    embed = discord.Embed(
        title=f"{medal} Placement Points Awarded",
        description=(
            f"{member.mention} finished **{ordinal} place** in **{event_name}**!\n\n"
            f"**+{pts} points** awarded\n"
            f"**New Total:** {new_total} pts — {rank}"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Awarded by {ctx.author.display_name}")
    save_data()
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

    save_data()
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


@bot.command(name="clanstats")
async def clan_stats(ctx):
    """Shows a full snapshot of the clan's stats. Usage: !clanstats"""

    # Member stats
    total_members = ctx.guild.member_count
    verified_count = len(verified_rsns)
    total_points_distributed = sum(points_data.values())

    # Top earner all time
    top_earner_name = "No one yet"
    top_earner_pts = 0
    if points_data:
        top_id = max(points_data, key=points_data.get)
        top_earner_pts = points_data[top_id]
        top_member = ctx.guild.get_member(int(top_id))
        top_earner_name = top_member.display_name if top_member else "Unknown"

    # Bounty stats
    total_bounties = len(bounties)
    completed_bounties = sum(1 for b in bounties.values() if not b.get("active", True))
    active_bounties = sum(1 for b in bounties.values() if b.get("active", True))

    # Event stats
    total_events_held = weekly_stats.get("events_held", 0)

    # Coffer stats
    total_donated = sum(d.get("amount", 0) for d in coffer_donations)
    total_paid_out = sum(p.get("amount", 0) for p in coffer_payouts)

    # Referral stats
    total_referrals = len(referrals)

    # Rank distribution
    rank_counts = {r: 0 for r in RANK_EMOJIS.keys()}
    for uid, pts in points_data.items():
        rank = get_rank(pts, uid)
        if rank in rank_counts:
            rank_counts[rank] += 1

    rank_text = "\n".join(
        f"{get_rank_display(rank)} — {count}" for rank, count in rank_counts.items() if count > 0
    ) or "No ranked members yet"

    embed = discord.Embed(
        title="📊 Avera Clan Statistics",
        description="A full snapshot of everything Avera has accomplished.",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="👥 Members",
        value=(
            f"**Total Members:** {total_members}\n"
            f"**Verified Members:** {verified_count}\n"
            f"**Referrals Made:** {total_referrals}"
        ),
        inline=True
    )

    embed.add_field(
        name="🏆 Points",
        value=(
            f"**Total Distributed:** {total_points_distributed:,} pts\n"
            f"**All-Time Top Earner:** {top_earner_name}\n"
            f"**Their Total:** {top_earner_pts:,} pts"
        ),
        inline=True
    )

    embed.add_field(
        name="🎯 Bounties",
        value=(
            f"**Total Posted:** {total_bounties}\n"
            f"**Completed:** {completed_bounties}\n"
            f"**Currently Active:** {active_bounties}"
        ),
        inline=True
    )

    embed.add_field(
        name="📅 Events",
        value=(
            f"**Events Held:** {total_events_held}\n"
            f"**Shop Redemptions:** {len(shop_redemptions)}"
        ),
        inline=True
    )

    embed.add_field(
        name="🏦 Clan Coffer",
        value=(
            f"**Current Balance:** {coffer_balance:,} gp\n"
            f"**Total Donated:** {total_donated:,} gp\n"
            f"**Total Paid Out:** {total_paid_out:,} gp"
        ),
        inline=True
    )

    embed.add_field(
        name="📈 Rank Distribution",
        value=rank_text,
        inline=True
    )

    embed.set_footer(text=f"Avera Clan • Stats as of {datetime.now().strftime('%d %b %Y')}")
    embed.timestamp = datetime.now()

    await ctx.send(embed=embed)





# ============================================================
#  RANK SYSTEM
# ============================================================

# Custom emoji IDs
RANK_EMOJIS = {
    "Recruit":     "<:Recruit:1479877159743914119>",
    "Corporal":    "<:Corporal:1479877075333681315>",
    "Sergeant":    "<:Sergeant:1479877030500896849>",
    "Noble":       "<:Noble:1479979876214640742>",
    "Legionnaire": "<:Legionnaire:1479979893365407876>",
    "Lieutenant":  "<:Lieutenant:1479877009479045210>",
    "Captain":     "<:Captain:1479877103863468296>",
    "General":     "<:General:1479877126693064936>",
}

# Admin-assigned ranks (not earnable automatically)
ADMIN_RANKS = ["Lieutenant", "Captain", "General"]

# member_ranks: { user_id: rank_name } — stores admin-assigned ranks
member_ranks = {}


def get_months_since_verify(user_id):
    """Returns how many months since a member verified. Returns 0 if not verified."""
    ts = verify_times.get(str(user_id))
    if not ts:
        return 0
    from datetime import timezone
    verified_dt = datetime.fromisoformat(ts)
    now = datetime.now()
    months = (now.year - verified_dt.year) * 12 + (now.month - verified_dt.month)
    return months


def get_rank(points, user_id=None, total_level=None, ehp=None):
    """Returns rank name based on admin assignment, time, stats, or points."""
    uid = str(user_id) if user_id else None

    # Admin-assigned ranks take priority
    if uid and uid in member_ranks:
        return member_ranks[uid]

    months = get_months_since_verify(uid) if uid else 0

    # Legionnaire: 1 year + (total level 2200 OR EHP 1000)
    if months >= 12:
        if (total_level and total_level >= 2200) or (ehp and ehp >= 1000):
            return "Legionnaire"

    # Noble: 6 months + (total level 2000 OR EHP 600)
    if months >= 6:
        if (total_level and total_level >= 2000) or (ehp and ehp >= 600):
            return "Noble"

    # Sergeant: 3 months + (total level 1750 OR EHP 300)
    if months >= 3:
        if (total_level and total_level >= 1750) or (ehp and ehp >= 300):
            return "Sergeant"

    # Corporal: 1 month verified
    if months >= 1:
        return "Corporal"

    return "Recruit"


def get_rank_display(rank_name):
    """Returns emoji + rank name for display."""
    emoji = RANK_EMOJIS.get(rank_name, "")
    return f"{emoji} {rank_name}"


async def fetch_osrs_stats(rsn):
    """Fetch total level and EHP from OSRS hiscores. Returns (total_level, ehp) or (None, None)."""
    try:
        url = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={rsn.replace(' ', '%20')}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None, None
                text = await resp.text()

        lines = text.strip().split("\n")
        # Line 0 = Overall (rank, level, xp)
        overall = lines[0].split(",")
        total_level = int(overall[1]) if len(overall) > 1 else None

        # EHP is at index 52 in the hiscores lite format
        ehp = None
        if len(lines) > 52:
            ehp_line = lines[52].split(",")
            if len(ehp_line) > 1:
                try:
                    ehp = float(ehp_line[1])
                except ValueError:
                    ehp = None

        return total_level, ehp
    except Exception:
        return None, None


async def assign_rank_role(guild, member, rank_name):
    """Assign the correct rank role in Discord, removing old rank roles first."""
    rank_role = discord.utils.get(guild.roles, name=rank_name)
    if not rank_role:
        # Create the role if it doesn't exist
        try:
            rank_role = await guild.create_role(name=rank_name, reason="Avera rank role auto-created")
        except discord.Forbidden:
            return False

    # Remove all other rank roles from the member
    roles_to_remove = [
        r for r in member.roles
        if r.name in RANK_EMOJIS.keys() and r.name != rank_name
    ]
    if roles_to_remove:
        try:
            await member.remove_roles(*roles_to_remove)
        except discord.Forbidden:
            pass

    # Add new rank role
    if rank_role not in member.roles:
        try:
            await member.add_roles(rank_role)
            return True
        except discord.Forbidden:
            return False
    return False


@bot.command(name="rankcheck")
async def rank_check(ctx, member: discord.Member = None):
    """Check and update your rank based on in-game stats. Usage: !rankcheck [@member]"""
    target = member or ctx.author
    user_id = str(target.id)
    rsn = verified_rsns.get(user_id)

    if not rsn:
        await ctx.send(f"❌ **{target.display_name}** hasn't verified their RSN yet. Use `!verify <rsn>` first.")
        return

    msg = await ctx.send(f"🔍 Checking **{rsn}** on the hiscores...")

    total_level, ehp = await fetch_osrs_stats(rsn)
    points = points_data.get(user_id, 0)
    months = get_months_since_verify(user_id)

    new_rank = get_rank(points, user_id, total_level, ehp)
    rank_display = get_rank_display(new_rank)

    # Assign Discord role
    role_changed = await assign_rank_role(ctx.guild, target, new_rank)

    stats_text = ""
    if total_level:
        stats_text += f"📊 **Total Level:** {total_level:,}\n"
    if ehp:
        stats_text += f"⏱️ **EHP:** {ehp:.1f}\n"
    stats_text += f"🏅 **Clan Points:** {points}\n"
    stats_text += f"📅 **Months Verified:** {months}"

    embed = discord.Embed(
        title=f"{rank_display} — {target.display_name}",
        description=(
            f"{stats_text}\n\n"
            + (f"✅ Rank role updated to **{new_rank}**!" if role_changed else f"✔️ Already ranked as **{new_rank}**.")
        ),
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.set_footer(text="Use !rankcheck to refresh your rank anytime")
    await msg.edit(content=None, embed=embed)


@bot.command(name="assignrank")
@commands.has_permissions(manage_guild=True)
async def assign_rank(ctx, member: discord.Member = None, *, rank: str = None):
    """Manually assign an admin rank to a member. Admin only.
    Usage: !assignrank @member <rank>
    Admin ranks: Lieutenant, Captain, General"""
    if not member or not rank:
        await ctx.send(
            "❌ Usage: `!assignrank @member <rank>`\n"
            "Admin ranks: `Lieutenant`, `Captain`, `General`"
        )
        return

    # Match rank name case-insensitively
    matched = next((r for r in RANK_EMOJIS.keys() if r.lower() == rank.lower()), None)
    if not matched:
        await ctx.send(f"❌ Unknown rank **{rank}**. Valid ranks: {', '.join(RANK_EMOJIS.keys())}")
        return

    user_id = str(member.id)
    member_ranks[user_id] = matched
    save_data()

    await assign_rank_role(ctx.guild, member, matched)

    embed = discord.Embed(
        title="✅ Rank Assigned",
        description=f"{member.mention} has been assigned **{get_rank_display(matched)}**!",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Assigned by {ctx.author.display_name}")
    await ctx.send(embed=embed)


@bot.command(name="removerank")
@commands.has_permissions(manage_guild=True)
async def remove_rank(ctx, member: discord.Member = None):
    """Remove an admin-assigned rank from a member. Admin only.
    Usage: !removerank @member"""
    if not member:
        await ctx.send("❌ Usage: `!removerank @member`")
        return

    user_id = str(member.id)
    if user_id in member_ranks:
        del member_ranks[user_id]
        save_data()
        await ctx.send(f"✅ Removed admin-assigned rank from **{member.display_name}**. Their rank will now be determined automatically.")
    else:
        await ctx.send(f"❌ **{member.display_name}** doesn't have an admin-assigned rank.")


@bot.command(name="rankupdate")
@commands.has_permissions(manage_guild=True)
async def rank_update_all(ctx):
    """Recalculate and update ranks for all verified members. Admin only.
    Usage: !rankupdate"""
    msg = await ctx.send(f"⏳ Updating ranks for all verified members... (this may take a moment)")
    updated = 0
    skipped = 0

    for user_id, rsn in verified_rsns.items():
        member = ctx.guild.get_member(int(user_id))
        if not member:
            skipped += 1
            continue

        total_level, ehp = await fetch_osrs_stats(rsn)
        points = points_data.get(user_id, 0)
        new_rank = get_rank(points, user_id, total_level, ehp)
        changed = await assign_rank_role(ctx.guild, member, new_rank)
        if changed:
            updated += 1
        await asyncio.sleep(1)  # avoid rate limiting

    await msg.edit(content=f"✅ Rank update complete! **{updated}** members updated, **{skipped}** skipped (left server).")


# ── Daily Rank-Up Notification Task ──────────────────────────

@tasks.loop(hours=24)
async def daily_rankup_check():
    """Once a day, check all verified members and DM anyone newly eligible for a higher rank."""
    for guild in bot.guilds:
        for user_id, rsn in list(verified_rsns.items()):
            member = guild.get_member(int(user_id))
            if not member:
                continue

            # Get current Discord rank role
            current_role_name = next(
                (r.name for r in member.roles if r.name in RANK_EMOJIS.keys()), "Recruit"
            )

            # Skip admin-assigned ranks
            if user_id in member_ranks:
                continue

            total_level, ehp = await fetch_osrs_stats(rsn)
            points = points_data.get(user_id, 0)
            new_rank = get_rank(points, user_id, total_level, ehp)

            # Only notify if rank has improved
            rank_order = list(RANK_EMOJIS.keys())
            current_idx = rank_order.index(current_role_name) if current_role_name in rank_order else 0
            new_idx = rank_order.index(new_rank) if new_rank in rank_order else 0

            if new_idx > current_idx:
                # Assign the new role
                await assign_rank_role(guild, member, new_rank)

                # DM the member
                try:
                    embed = discord.Embed(
                        title="🎉 You're eligible for a rank up!",
                        description=(
                            f"Hey **{member.display_name}**, great news!\n\n"
                            f"You've met the requirements for **{get_rank_display(new_rank)}** in **Avera**!\n\n"
                            f"Your rank role has been automatically updated. "
                            f"If you'd like it officially recognised by staff, head to the support channel and open a **Rank Promotion** ticket!\n\n"
                            f"Keep up the grind! ⚔️"
                        ),
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text="Avera Clan • Rank System")
                    await member.send(embed=embed)
                except discord.Forbidden:
                    pass  # Member has DMs closed

            await asyncio.sleep(1)  # avoid rate limiting


@daily_rankup_check.before_loop
async def before_daily_rankup():
    await bot.wait_until_ready()


# ── Profile Command ───────────────────────────────────────────

@bot.command(name="profile")
async def profile(ctx, member: discord.Member = None):
    """View a member's full clan profile. Usage: !profile [@member]"""
    target = member or ctx.author
    user_id = str(target.id)

    rsn = verified_rsns.get(user_id)
    points = points_data.get(user_id, 0)
    months = get_months_since_verify(user_id)
    streak = event_streaks.get(user_id, 0)
    current_rank = get_rank(points, user_id)
    rank_display = get_rank_display(current_rank)

    # Bounties claimed
    bounties_claimed = sum(
        1 for b in bounties.values()
        if not b.get("active", True) and b.get("claimed_by") == target.display_name
    )

    # Shop redemptions
    redemptions = sum(1 for r in shop_redemptions if r.get("user_id") == user_id)

    # Events attended (count from weekly stats or points history — approximate via attendance)
    events_attended = weekly_stats.get("events_attended", {}).get(user_id, 0)

    # Next rank info
    rank_order = list(RANK_EMOJIS.keys())
    current_idx = rank_order.index(current_rank) if current_rank in rank_order else 0
    admin_ranks = ["Lieutenant", "Captain", "General"]
    next_rank = None
    next_rank_req = ""
    if current_rank not in admin_ranks and current_idx < len(rank_order) - 1:
        next_rank = rank_order[current_idx + 1]
        if next_rank == "Corporal":
            next_rank_req = "1 month verified"
        elif next_rank == "Sergeant":
            next_rank_req = "3 months verified + Level 1750 or EHP 300+"
        elif next_rank == "Noble":
            next_rank_req = "6 months verified + Level 2000 or EHP 600+"
        elif next_rank == "Legionnaire":
            next_rank_req = "12 months verified + Level 2200 or EHP 1000+"
        elif next_rank in admin_ranks:
            next_rank_req = "Admin assigned only"

    embed = discord.Embed(
        title=f"📋 {target.display_name}'s Clan Profile",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=target.display_avatar.url)

    embed.add_field(
        name="🎮 RSN",
        value=rsn if rsn else "*Not verified*",
        inline=True
    )
    embed.add_field(
        name="🎖️ Rank",
        value=rank_display,
        inline=True
    )
    embed.add_field(
        name="📅 Time in Clan",
        value=f"{months} month{'s' if months != 1 else ''}" if months > 0 else "< 1 month",
        inline=True
    )
    embed.add_field(
        name="🏅 Clan Points",
        value=f"{points:,} pts",
        inline=True
    )
    embed.add_field(
        name="🔥 Event Streak",
        value=f"{streak} consecutive event{'s' if streak != 1 else ''}",
        inline=True
    )
    embed.add_field(
        name="🎯 Bounties Claimed",
        value=str(bounties_claimed),
        inline=True
    )
    embed.add_field(
        name="🛒 Shop Redemptions",
        value=str(redemptions),
        inline=True
    )

    if next_rank and next_rank not in admin_ranks:
        embed.add_field(
            name=f"⬆️ Next Rank — {get_rank_display(next_rank)}",
            value=next_rank_req,
            inline=False
        )
    elif current_rank in admin_ranks:
        embed.add_field(
            name="👑 Staff Rank",
            value="You hold a staff rank — assigned by admins.",
            inline=False
        )

    embed.set_footer(text="Avera Clan • Use !rankcheck to update your rank role")
    embed.timestamp = datetime.now()
    await ctx.send(embed=embed)


# ── Compare Command ───────────────────────────────────────────

@bot.command(name="compare")
async def compare(ctx, member1: discord.Member = None, member2: discord.Member = None):
    """Compare two clan members side by side. Usage: !compare @member1 @member2"""
    if not member1 or not member2:
        await ctx.send("❌ Usage: `!compare @member1 @member2`")
        return

    if member1.id == member2.id:
        await ctx.send("❌ You can't compare a member with themselves!")
        return

    msg = await ctx.send("🔍 Fetching stats for both members...")

    results = []
    for target in [member1, member2]:
        uid = str(target.id)
        rsn = verified_rsns.get(uid)
        points = points_data.get(uid, 0)
        months = get_months_since_verify(uid)
        streak = event_streaks.get(uid, 0)
        bounties_claimed = sum(
            1 for b in bounties.values()
            if not b.get("active", True) and b.get("claimed_by") == target.display_name
        )
        total_level, ehp = await fetch_osrs_stats(rsn) if rsn else (None, None)
        rank = get_rank(points, uid, total_level, ehp)

        results.append({
            "member": target,
            "rsn": rsn or "Not verified",
            "points": points,
            "months": months,
            "streak": streak,
            "bounties": bounties_claimed,
            "total_level": total_level,
            "ehp": ehp,
            "rank": rank,
        })

    a, b_data = results[0], results[1]

    def winner(val_a, val_b, higher_is_better=True):
        if val_a is None and val_b is None:
            return "➖", "➖"
        if val_a is None:
            return "➖", "✅" if higher_is_better else "✅"
        if val_b is None:
            return "✅" if higher_is_better else "✅", "➖"
        if val_a == val_b:
            return "➖", "➖"
        if higher_is_better:
            return ("✅", "➡️") if val_a > val_b else ("➡️", "✅")
        else:
            return ("✅", "➡️") if val_a < val_b else ("➡️", "✅")

    pts_w = winner(a["points"], b_data["points"])
    months_w = winner(a["months"], b_data["months"])
    streak_w = winner(a["streak"], b_data["streak"])
    bounty_w = winner(a["bounties"], b_data["bounties"])
    level_w = winner(a["total_level"], b_data["total_level"])
    ehp_w = winner(a["ehp"], b_data["ehp"])

    embed = discord.Embed(
        title=f"⚔️ {member1.display_name} vs {member2.display_name}",
        color=discord.Color.gold()
    )

    embed.add_field(
        name=f"📊 {member1.display_name}",
        value=(
            f"**RSN:** {a['rsn']}\n"
            f"**Rank:** {get_rank_display(a['rank'])}\n"
            f"{pts_w[0]} **Points:** {a['points']:,}\n"
            f"{months_w[0]} **Months:** {a['months']}\n"
            f"{streak_w[0]} **Streak:** {a['streak']}\n"
            f"{bounty_w[0]} **Bounties:** {a['bounties']}\n"
            f"{level_w[0]} **Total Level:** {a['total_level']:,}" if a['total_level'] else f"{level_w[0]} **Total Level:** N/A" + f"\n{ehp_w[0]} **EHP:** {a['ehp']:.1f}" if a['ehp'] else f"\n{ehp_w[0]} **EHP:** N/A"
        ),
        inline=True
    )

    embed.add_field(
        name=f"📊 {member2.display_name}",
        value=(
            f"**RSN:** {b_data['rsn']}\n"
            f"**Rank:** {get_rank_display(b_data['rank'])}\n"
            f"{pts_w[1]} **Points:** {b_data['points']:,}\n"
            f"{months_w[1]} **Months:** {b_data['months']}\n"
            f"{streak_w[1]} **Streak:** {b_data['streak']}\n"
            f"{bounty_w[1]} **Bounties:** {b_data['bounties']}\n"
            f"{level_w[1]} **Total Level:** {b_data['total_level']:,}" if b_data['total_level'] else f"{level_w[1]} **Total Level:** N/A" + f"\n{ehp_w[1]} **EHP:** {b_data['ehp']:.1f}" if b_data['ehp'] else f"\n{ehp_w[1]} **EHP:** N/A"
        ),
        inline=True
    )

    embed.set_footer(text="✅ = winner in that category • Avera Clan")
    embed.timestamp = datetime.now()
    await msg.edit(content=None, embed=embed)







# ============================================================
#  BOUNTY SYSTEM
# ============================================================

BOUNTY_CHANNEL_ID = 1479471419577602199

# Active bounties: { bounty_id: { target, points, description, claimed_by, active } }
bounties = {}
bounty_counter = 0

# Tracks open claim review channels: { bounty_id: channel_id }
claim_channels = {}


@bot.command(name="bounty")
@commands.has_permissions(manage_guild=True)
async def create_bounty(ctx, target: str = None, points: int = None, *, description: str = None):
    """Create a bounty. Admin only.
    Usage: !bounty <target> <points> <description>
    Example: !bounty Zulrah 100 Kill her and submit a screenshot as proof!"""
    if not target or points is None or not description:
        await ctx.send(
            "❌ Usage: `!bounty <target> <points> <description>`\n"
            "Example: `!bounty Zulrah 100 Kill her and submit a screenshot as proof!`"
        )
        return
    if points <= 0:
        await ctx.send("❌ Points must be a positive number.")
        return

    global bounty_counter
    bounty_counter += 1
    bounty_id = bounty_counter

    bounties[bounty_id] = {
        "target": target,
        "points": points,
        "description": description,
        "claimed_by": None,
        "active": True,
        "created_by": ctx.author.display_name
    }

    bounty_channel = bot.get_channel(BOUNTY_CHANNEL_ID)
    if not bounty_channel:
        await ctx.send("❌ Could not find the Bounties channel. Double-check the channel ID in bot.py.")
        return

    embed = discord.Embed(
        title=f"🎯 NEW BOUNTY — {target}!",
        description=(
            f"There is a new bounty on **{target}**!\n\n"
            f"📝 {description}\n\n"
            f"Use `!claim {bounty_id}` and send proof to be rewarded **{points} points**!"
        ),
        color=discord.Color.red()
    )
    embed.add_field(name="🏆 Reward", value=f"{points} points", inline=True)
    embed.add_field(name="🎯 Target", value=target, inline=True)
    embed.add_field(name="🔖 Bounty ID", value=f"#{bounty_id}", inline=True)
    embed.set_footer(text=f"Posted by {ctx.author.display_name} • Use !claim {bounty_id} to claim")
    embed.timestamp = datetime.now()

    await bounty_channel.send("@everyone", embed=embed)
    save_data()

    if ctx.channel.id != BOUNTY_CHANNEL_ID:
        await ctx.send(f"✅ Bounty #{bounty_id} on **{target}** has been posted in <#{BOUNTY_CHANNEL_ID}>!")


@bot.command(name="claim")
async def claim_bounty(ctx, bounty_id: int = None):
    """Claim a bounty. Attach a screenshot as proof.
    Usage: !claim <bounty_id>  (with a screenshot attached)"""
    if bounty_id is None:
        await ctx.send("❌ Usage: `!claim <bounty_id>` — Find the bounty ID in the bounty post.\nExample: `!claim 1`")
        return

    if bounty_id not in bounties:
        await ctx.send(f"❌ Bounty #{bounty_id} doesn't exist. Use `!bounties` to see active bounties.")
        return

    bounty = bounties[bounty_id]

    if not bounty["active"]:
        claimer = bounty["claimed_by"] or "someone"
        await ctx.send(f"❌ Bounty #{bounty_id} has already been claimed by **{claimer}**!")
        return

    if not ctx.message.attachments:
        await ctx.send(
            f"❌ You need to attach a **screenshot** as proof!\n"
            f"Re-run the command and attach your proof image.\n"
            f"Example: `!claim {bounty_id}` *(with a screenshot attached)*"
        )
        return

    guild = ctx.guild
    attachment_url = ctx.message.attachments[0].url

    # Find the category that the bounty channel sits in (so the new channel appears nearby)
    bounty_channel = bot.get_channel(BOUNTY_CHANNEL_ID)
    category = bounty_channel.category if bounty_channel else None

    # Build permissions: private to everyone except the claimant and users with manage_guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }

    # Also grant access to any roles that have manage_guild (i.e. admin roles)
    for role in guild.roles:
        if role.permissions.manage_guild:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    # Create the private channel (unique per user so multiple claims can co-exist)
    channel_name = f"claim-{bounty_id}-{ctx.author.display_name}".lower().replace(" ", "-")[:100]
    review_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category,
        topic=f"Bounty #{bounty_id} claim review for {ctx.author.display_name}"
    )

    # Track all open claim channels for this bounty as a list
    if bounty_id not in claim_channels:
        claim_channels[bounty_id] = []
    claim_channels[bounty_id].append(review_channel.id)

    # Store the claim info on the bounty (append, don't overwrite)
    if "pending_claims" not in bounty:
        bounty["pending_claims"] = []
    bounty["pending_claims"].append({
        "user": ctx.author,
        "attachment": attachment_url,
        "review_channel_id": review_channel.id
    })

    # Post the claim details into the private channel
    embed = discord.Embed(
        title=f"⏳ Bounty #{bounty_id} Claim — Awaiting Review",
        description=(
            f"Hey {ctx.author.mention}! Your claim has been received.\n\n"
            f"🎯 **Target:** {bounty['target']}\n"
            f"🏆 **Reward:** {bounty['points']} points\n\n"
            f"An admin will review your screenshot below and approve or deny your claim.\n\n"
            f"*Admins: use `!approveclaim {bounty_id}` or `!denyclaim {bounty_id} [reason]` in this channel.*"
        ),
        color=discord.Color.orange()
    )
    embed.set_image(url=attachment_url)
    embed.set_footer(text=f"Submitted by {ctx.author.display_name}")
    embed.timestamp = datetime.now()

    await review_channel.send(embed=embed)

    # Count how many claims are open for this bounty
    open_claims = len(claim_channels.get(bounty_id, []))
    claim_word = "Member is" if open_claims == 1 else "Members are"

    # Post a public notice in the bounty channel
    bounty_channel_notify = bot.get_channel(BOUNTY_CHANNEL_ID)
    if bounty_channel_notify:
        await bounty_channel_notify.send(
            f"🎯 **{open_claims} {claim_word}** claiming to have completed Bounty #{bounty_id} — **{bounty['target']}**!\n"
            f"*Admins are reviewing the proof.*"
        )

    # DM the claimant with a link to their review channel
    try:
        await ctx.author.send(
            f"✅ Your claim for Bounty #{bounty_id} (**{bounty['target']}**) has been submitted!\n"
            f"Head over to {review_channel.mention} — an admin will review your proof there. 🎯"
        )
    except discord.Forbidden:
        pass  # Member has DMs disabled — review channel is their notification


@bot.command(name="approveclaim")
@commands.has_permissions(manage_guild=True)
async def approve_claim(ctx, bounty_id: int = None):
    """Approve a bounty claim and award points. Admin only.
    Usage: !approveclaim <bounty_id>"""
    if bounty_id is None:
        await ctx.send("❌ Usage: `!approveclaim <bounty_id>`")
        return

    if bounty_id not in bounties:
        await ctx.send(f"❌ Bounty #{bounty_id} doesn't exist.")
        return

    bounty = bounties[bounty_id]

    if not bounty["active"]:
        await ctx.send(f"❌ Bounty #{bounty_id} is no longer active.")
        return

    # Find the pending claim that belongs to the channel this command was used in
    pending = bounty.get("pending_claims", [])
    matched_claim = next((c for c in pending if c["review_channel_id"] == ctx.channel.id), None)

    # If not used inside a review channel, fall back to the first pending claim
    if not matched_claim and pending:
        matched_claim = pending[0]

    if not matched_claim:
        await ctx.send(f"❌ No pending claim found for Bounty #{bounty_id}.")
        return

    claimer = matched_claim["user"]
    pts = bounty["points"]
    review_channel_id = matched_claim.get("review_channel_id")

    # Award points
    user_id = str(claimer.id)
    points_data[user_id] = points_data.get(user_id, 0) + pts

    # Update weekly stats
    weekly_stats["bounties_completed"] += 1
    weekly_stats["points_awarded"] += pts
    weekly_stats["weekly_points"][user_id] = weekly_stats["weekly_points"].get(user_id, 0) + pts

    # Remove this claim from pending list and close all other open claims for this bounty
    bounty["pending_claims"] = []
    bounty["active"] = False
    bounty["claimed_by"] = claimer.display_name
    # Close all review channels for this bounty
    all_channel_ids = claim_channels.pop(bounty_id, [])

    new_total = points_data[user_id]
    rank = get_rank_display(get_rank(new_total, user_id))

    import asyncio

    # Announce approval in the approved review channel, then delete all review channels
    review_channel = bot.get_channel(review_channel_id) if review_channel_id else None
    if review_channel:
        approve_embed = discord.Embed(
            title="✅ Claim Approved!",
            description=(
                f"🎉 Congrats {claimer.mention}! Your claim has been approved by {ctx.author.mention}.\n\n"
                f"**+{pts} points** have been added to your total!\n"
                f"**New Total:** {new_total} points\n"
                f"**Rank:** {rank}\n\n"
                f"*This channel will be deleted in 10 seconds.*"
            ),
            color=discord.Color.green()
        )
        await review_channel.send(embed=approve_embed)

    # Notify and close any other open claim channels for this bounty
    for ch_id in all_channel_ids:
        if ch_id == review_channel_id:
            continue
        other_ch = bot.get_channel(ch_id)
        if other_ch:
            await other_ch.send("🚫 Another claim for this bounty was approved. This channel will be deleted in 10 seconds.")

    # Post a public announcement in the bounty channel
    bounty_channel = bot.get_channel(BOUNTY_CHANNEL_ID)
    if bounty_channel:
        public_embed = discord.Embed(
            title=f"✅ Bounty #{bounty_id} Claimed!",
            description=(
                f"🎉 {claimer.mention} has slain **{bounty['target']}** and claimed the bounty!\n\n"
                f"**+{pts} points** awarded!\n"
                f"**New Total:** {new_total} points\n"
                f"**Rank:** {rank}"
            ),
            color=discord.Color.green()
        )
        public_embed.set_footer(text=f"Approved by {ctx.author.display_name}")
        public_embed.timestamp = datetime.now()
        await bounty_channel.send(embed=public_embed)

    save_data()
    await ctx.send(f"✅ Approved! **{claimer.display_name}** has been awarded **{pts} points**.")

    # Delete all review channels after 10 seconds
    await asyncio.sleep(10)
    for ch_id in all_channel_ids:
        ch = bot.get_channel(ch_id)
        if ch:
            try:
                await ch.delete(reason=f"Bounty #{bounty_id} resolved.")
            except discord.NotFound:
                pass


@bot.command(name="denyclaim")
@commands.has_permissions(manage_guild=True)
async def deny_claim(ctx, bounty_id: int = None, *, reason: str = "No reason provided."):
    """Deny a bounty claim. Admin only.
    Usage: !denyclaim <bounty_id> [reason]"""
    if bounty_id is None:
        await ctx.send("❌ Usage: `!denyclaim <bounty_id> [reason]`")
        return

    if bounty_id not in bounties:
        await ctx.send(f"❌ Bounty #{bounty_id} doesn't exist.")
        return

    bounty = bounties[bounty_id]
    pending = bounty.get("pending_claims", [])

    # Match to the review channel this command was used in, or fall back to first
    matched_claim = next((c for c in pending if c["review_channel_id"] == ctx.channel.id), None)
    if not matched_claim and pending:
        matched_claim = pending[0]

    if not matched_claim:
        await ctx.send(f"❌ No pending claim found for Bounty #{bounty_id}.")
        return

    claimer = matched_claim["user"]
    review_channel_id = matched_claim.get("review_channel_id")

    # Remove just this claim from the pending list
    bounty["pending_claims"] = [c for c in pending if c["review_channel_id"] != review_channel_id]

    # Remove from claim_channels list
    if bounty_id in claim_channels:
        claim_channels[bounty_id] = [c for c in claim_channels[bounty_id] if c != review_channel_id]
        if not claim_channels[bounty_id]:
            del claim_channels[bounty_id]

    # Silently delete the admin's command so the member only sees the bot's response
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    review_channel = bot.get_channel(review_channel_id) if review_channel_id else None
    if review_channel:
        deny_embed = discord.Embed(
            title="❌ Claim Denied",
            description=(
                f"Sorry {claimer.mention}, your claim was denied by {ctx.author.mention}.\n\n"
                f"**Reason:** {reason}\n\n"
                f"The bounty on **{bounty['target']}** is still open — try again with better proof!\n\n"
                f"*This channel will be deleted in 10 seconds.*"
            ),
            color=discord.Color.red()
        )
        await review_channel.send(embed=deny_embed)

    await ctx.send(f"❌ Claim for Bounty #{bounty_id} denied. The bounty remains active.")

    # Delete the private review channel after 10 seconds
    if review_channel:
        import asyncio
        await asyncio.sleep(10)
        try:
            await review_channel.delete(reason=f"Bounty #{bounty_id} claim denied.")
        except discord.NotFound:
            pass


@bot.command(name="bounties")
async def list_bounties(ctx):
    """Lists all active bounties."""
    active = [(bid, b) for bid, b in bounties.items() if b["active"]]

    if not active:
        await ctx.send("🎯 There are no active bounties right now. Check back later!")
        return

    embed = discord.Embed(
        title="🎯 Active Avera Bounties",
        color=discord.Color.red()
    )
    for bounty_id, b in active:
        status = "⏳ Under Review" if bounty_id in claim_channels else "🟢 Open"
        embed.add_field(
            name=f"#{bounty_id} — {b['target']}",
            value=f"💰 **{b['points']} points**\n📝 {b['description']}\n{status} • `!claim {bounty_id}` to claim",
            inline=False
        )
    embed.set_footer(text="Attach a screenshot when using !claim")
    await ctx.send(embed=embed)


@bot.command(name="cancelbounty")
@commands.has_permissions(manage_guild=True)
async def cancel_bounty(ctx, bounty_id: int = None):
    """Cancel an active bounty. Admin only.
    Usage: !cancelbounty <bounty_id>"""
    if bounty_id is None or bounty_id not in bounties:
        await ctx.send("❌ Invalid bounty ID. Use `!bounties` to see active bounties.")
        return

    bounties[bounty_id]["active"] = False

    # Clean up any open review channel
    review_channel_id = claim_channels.pop(bounty_id, None)
    if review_channel_id:
        review_channel = bot.get_channel(review_channel_id)
        if review_channel:
            await review_channel.send("🚫 This bounty has been cancelled by an admin. Channel will be deleted in 10 seconds.")
            import asyncio
            await asyncio.sleep(10)
            try:
                await review_channel.delete(reason="Bounty cancelled.")
            except discord.NotFound:
                pass

    await ctx.send(f"✅ Bounty #{bounty_id} (**{bounties[bounty_id]['target']}**) has been cancelled.")


# ============================================================
#  ERROR HANDLING
# ============================================================


# ============================================================
#  TICKET SYSTEM
# ============================================================

TICKET_PANEL_CHANNEL_ID = 1479619326368551005

# Tracks open tickets: { user_id: channel_id }
open_tickets = {}


class TicketPanel(discord.ui.View):
    """Persistent button panel posted in the support channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.primary, emoji="🔧", custom_id="ticket_general")
    async def general_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket(interaction, "general-support", "General Support", "🔧",
            "Please describe your issue and a staff member will be with you shortly.")

    @discord.ui.button(label="Submissions", style=discord.ButtonStyle.secondary, emoji="📝", custom_id="ticket_submissions")
    async def submissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket(interaction, "submission", "Submission", "📝",
            "Please provide your submission details below and a staff member will review it.")

    @discord.ui.button(label="Staff Application", style=discord.ButtonStyle.success, emoji="⭐", custom_id="ticket_staffapp")
    async def staff_application(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket(interaction, "staff-app", "Staff Application", "⭐",
            "Thanks for your interest in joining the Avera staff team! Please tell us:\n\n"
            "• Your OSRS username\n"
            "• Your timezone\n"
            "• Why you want to be staff\n"
            "• Any relevant experience")

    @discord.ui.button(label="Report a Member", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="ticket_report")
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_ticket(interaction, "report", "Report", "🚨",
            "Please provide the following:\n\n"
            "• Username of the member you are reporting\n"
            "• What happened?\n"
            "• Any evidence (screenshots etc.)")

    @discord.ui.button(label="Rank Promotion", style=discord.ButtonStyle.success, emoji="⬆️", custom_id="ticket_promotion")
    async def rank_promotion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await open_promotion_ticket(interaction)


async def open_promotion_ticket(interaction: discord.Interaction):
    """Creates a private promotion review ticket with auto-posted rank check."""
    user = interaction.user
    guild = interaction.guild
    user_id = str(user.id)

    # Check for existing open ticket
    if user_id in open_tickets:
        existing = guild.get_channel(open_tickets[user_id])
        if existing:
            await interaction.response.send_message(
                f"❌ You already have an open ticket! Head to {existing.mention}.",
                ephemeral=True
            )
            return

    # Check they have a verified RSN
    rsn = verified_rsns.get(user_id)
    if not rsn:
        await interaction.response.send_message(
            "❌ You need to verify your RSN first! Use `!verify <username>` before requesting a promotion.",
            ephemeral=True
        )
        return

    # Build permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    for role in guild.roles:
        if role.permissions.manage_guild:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    panel_channel = guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    category = panel_channel.category if panel_channel else None

    channel_name = f"promotion-{user.display_name}".lower().replace(" ", "-")[:100]
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category,
        topic=f"Rank promotion request for {user.display_name}"
    )

    open_tickets[user_id] = ticket_channel.id

    # Opening embed
    embed = discord.Embed(
        title="⬆️ Rank Promotion Request — Avera",
        description=(
            f"Hey {user.mention}! Your promotion request has been received.\n\n"
            f"🔍 Pulling your current stats from the OSRS hiscores now...\n\n"
            f"*A staff member will review your stats and action your request as soon as possible.*\n\n"
            f"To close this ticket, click the button below or type `!closeticket`."
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Avera Clan • Rank Promotion")
    embed.timestamp = datetime.now()

    await ticket_channel.send(embed=embed, view=CloseTicketView())

    # Auto-fetch and post rank check
    total_level, ehp = await fetch_osrs_stats(rsn)
    points = points_data.get(user_id, 0)
    months = get_months_since_verify(user_id)
    current_rank = get_rank(points, user_id, total_level, ehp)
    rank_display = get_rank_display(current_rank)

    stats_embed = discord.Embed(
        title=f"📊 Rank Check — {user.display_name}",
        description=f"**Verified RSN:** {rsn}",
        color=discord.Color.blue()
    )
    stats_embed.add_field(name="📅 Months Verified", value=str(months), inline=True)
    stats_embed.add_field(name="🏅 Clan Points", value=str(points), inline=True)
    stats_embed.add_field(
        name="📊 In-Game Stats",
        value=(
            f"**Total Level:** {total_level:,}" if total_level else "Could not fetch stats"
        ) + (f"\n**EHP:** {ehp:.1f}" if ehp else ""),
        inline=True
    )
    stats_embed.add_field(name="🎖️ Current Rank", value=rank_display, inline=False)
    stats_embed.add_field(
        name="📋 Rank Requirements",
        value=(
            "**Corporal** — 1+ month verified\n"
            "**Sergeant** — 3+ months & Level 1750+ or EHP 300+\n"
            "**Noble** — 6+ months & Level 2000+ or EHP 600+\n"
            "**Legionnaire** — 12+ months & Level 2200+ or EHP 1000+\n"
            "**Lieutenant / Captain / General** — Admin assigned only"
        ),
        inline=False
    )
    stats_embed.set_footer(text="Staff: use !assignrank or !rankcheck to update this member's rank")
    stats_embed.timestamp = datetime.now()

    await ticket_channel.send(embed=stats_embed)

    await interaction.response.send_message(
        f"✅ Your promotion ticket has been created! Head to {ticket_channel.mention}.",
        ephemeral=True
    )


async def open_ticket(interaction: discord.Interaction, ticket_type: str, label: str, emoji: str, prompt: str):
    """Creates a private ticket channel for the user."""
    user = interaction.user
    guild = interaction.guild
    user_id = str(user.id)

    # Check if user already has an open ticket
    if user_id in open_tickets:
        existing = guild.get_channel(open_tickets[user_id])
        if existing:
            await interaction.response.send_message(
                f"❌ You already have an open ticket! Head to {existing.mention}.",
                ephemeral=True
            )
            return

    # Build permissions — private to user + admin roles only
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
    }
    for role in guild.roles:
        if role.permissions.manage_guild:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    # Try to place it in the same category as the panel channel
    panel_channel = guild.get_channel(TICKET_PANEL_CHANNEL_ID)
    category = panel_channel.category if panel_channel else None

    channel_name = f"{ticket_type}-{user.display_name}".lower().replace(" ", "-")[:100]
    ticket_channel = await guild.create_text_channel(
        name=channel_name,
        overwrites=overwrites,
        category=category,
        topic=f"{label} ticket for {user.display_name}"
    )

    open_tickets[user_id] = ticket_channel.id

    # Welcome embed inside the ticket
    embed = discord.Embed(
        title=f"{emoji} {label} — Avera Support",
        description=(
            f"Hey {user.mention}, thanks for reaching out to **Avera** support!\n\n"
            f"{prompt}\n\n"
            f"*A staff member will be with you as soon as possible.*\n\n"
            f"To close this ticket, click the button below or type `!closeticket`."
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Avera Clan Support • Only you and staff can see this")
    embed.timestamp = datetime.now()

    await ticket_channel.send(embed=embed, view=CloseTicketView())

    await interaction.response.send_message(
        f"✅ Your ticket has been created! Head to {ticket_channel.mention}.",
        ephemeral=True
    )


class CloseTicketView(discord.ui.View):
    """Close button shown inside a ticket channel."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await handle_close_ticket(interaction)


async def handle_close_ticket(interaction: discord.Interaction):
    """Handles closing a ticket channel."""
    channel = interaction.channel
    guild = interaction.guild

    # Find and remove from open_tickets
    user_id_to_remove = None
    for uid, cid in open_tickets.items():
        if cid == channel.id:
            user_id_to_remove = uid
            break
    if user_id_to_remove:
        del open_tickets[user_id_to_remove]

    embed = discord.Embed(
        description=f"🔒 Ticket closed by {interaction.user.mention}. This channel will be deleted in 5 seconds.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

    import asyncio
    await asyncio.sleep(5)
    try:
        await channel.delete(reason="Ticket closed.")
    except discord.NotFound:
        pass


@bot.command(name="closeticket")
async def close_ticket_cmd(ctx):
    """Close the current ticket channel. Usage: !closeticket"""
    # Check this is actually a ticket channel
    user_id_to_remove = None
    for uid, cid in open_tickets.items():
        if cid == ctx.channel.id:
            user_id_to_remove = uid
            break

    if not user_id_to_remove:
        await ctx.send("❌ This is not a ticket channel.")
        return

    del open_tickets[user_id_to_remove]

    embed = discord.Embed(
        description=f"🔒 Ticket closed by {ctx.author.mention}. This channel will be deleted in 5 seconds.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

    import asyncio
    await asyncio.sleep(5)
    try:
        await ctx.channel.delete(reason="Ticket closed.")
    except discord.NotFound:
        pass


@bot.command(name="ticketpanel")
@commands.has_permissions(manage_guild=True)
async def ticket_panel(ctx):
    """Post the ticket panel in the support channel. Admin only. Usage: !ticketpanel"""
    panel_channel = bot.get_channel(TICKET_PANEL_CHANNEL_ID)
    if not panel_channel:
        await ctx.send("❌ Could not find the support channel. Check the channel ID in bot.py.")
        return

    embed = discord.Embed(
        title="🔧 Avera Support",
        description=(
            "**Need help? We\'re here for you!**\n\n"
            "Please select one of the options below and we will get back to you as soon as possible.\n\n"
            "🔧 **General Support** — For general inquiries\n"
            "📝 **Submissions** — For all submissions\n"
            "⭐ **Staff Application** — Apply to join the staff team\n"
            "🚨 **Report a Member** — Report rule-breaking behaviour\n"
            "⬆️ **Rank Promotion** — Request a rank review from staff\n\n"
            "*A private channel will be created just for you and staff.*"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Avera Clan • Click a button below to open a ticket")

    await panel_channel.send(embed=embed, view=TicketPanel())

    if ctx.channel.id != TICKET_PANEL_CHANNEL_ID:
        await ctx.send(f"✅ Ticket panel posted in <#{TICKET_PANEL_CHANNEL_ID}>!")



# ============================================================
#  REACTION ROLES SYSTEM
# ============================================================

REACTION_ROLES_CHANNEL_ID = 1459413079438917672

# Role definitions for each category
ACCOUNT_ROLES = [
    (None, "Main"),
    (None, "Ironman"),
    (None, "HCIM"),
    (None, "UIM"),
    (None, "GIM"),
]

REGION_ROLES = [
    ("🌎", "North America"),
    ("🌍", "Europe"),
    ("🌏", "Oceania"),
    ("🌏", "Asia"),
    ("🌍", "Africa"),
    ("🌎", "South America"),
]

RAID_ROLES = [
    ("🪦", "Tombs of Amascut"),
    ("💎", "Chambers of Xeric"),
    ("🩸", "Theatre of Blood"),
]


async def get_or_create_role(guild, name):
    """Gets an existing role by name or creates it if it doesn't exist."""
    role = discord.utils.get(guild.roles, name=name)
    if not role:
        role = await guild.create_role(name=name, mentionable=False, reason="Avera reaction role auto-created")
        print(f"Created role: {name}")
    return role


def make_role_view(roles_list, view_id_prefix):
    """Dynamically builds a View with toggle buttons for a list of roles."""

    class RoleView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            for emoji, role_name in roles_list:
                self.add_item(RoleButton(emoji, role_name, f"{view_id_prefix}_{role_name.lower().replace(' ', '_')}"))

    return RoleView


class RoleButton(discord.ui.Button):
    def __init__(self, emoji, role_name, custom_id):
        super().__init__(
            label=role_name,
            emoji=emoji if emoji else None,
            style=discord.ButtonStyle.primary,
            custom_id=custom_id
        )
        self.role_name = role_name

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user

        role = await get_or_create_role(guild, self.role_name)

        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(
                f"✅ Removed the **{self.role_name}** role.",
                ephemeral=True
            )
        else:
            await member.add_roles(role)
            await interaction.response.send_message(
                f"✅ You now have the **{self.role_name}** role!",
                ephemeral=True
            )


# Pre-build persistent views
AccountRoleView = make_role_view(ACCOUNT_ROLES, "acct")
RegionRoleView = make_role_view(REGION_ROLES, "region")
RaidRoleView = make_role_view(RAID_ROLES, "raid")


@bot.command(name="rolepanel")
@commands.has_permissions(manage_guild=True)
async def role_panel(ctx):
    """Post the reaction role panels. Admin only. Usage: !rolepanel"""
    channel = bot.get_channel(REACTION_ROLES_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the reaction roles channel. Check the channel ID in bot.py.")
        return

    # --- Account Type ---
    embed1 = discord.Embed(
        title="🎮 What type of account do you play?",
        description=(
            "Let us know your account type so we can best support you!\n\n"
            "**Main** — Standard account\n"
            "**Ironman** — Self-sufficient ironman\n"
            "**HCIM** — Hardcore Ironman\n"
            "**UIM** — Ultimate Ironman\n"
            "**GIM** — Group Ironman\n\n"
            "*Click a button to add or remove a role. You can select multiple!*"
        ),
        color=discord.Color.blue()
    )
    embed1.set_footer(text="Avera Clan • Click to toggle a role")
    await channel.send(embed=embed1, view=AccountRoleView())

    # --- Region ---
    embed2 = discord.Embed(
        title="🌍 Where are you from?",
        description=(
            "Let us know your region so we can see where the clan is spread!\n\n"
            "🌎 **North America**\n"
            "🌍 **Europe**\n"
            "🌏 **Oceania**\n"
            "🌏 **Asia**\n"
            "🌍 **Africa**\n"
            "🌎 **South America**\n\n"
            "*Click a button to add or remove a role.*"
        ),
        color=discord.Color.green()
    )
    embed2.set_footer(text="Avera Clan • Click to toggle a role")
    await channel.send(embed=embed2, view=RegionRoleView())

    # --- Raid Interests ---
    embed3 = discord.Embed(
        title="⚔️ Which raids are you interested in?",
        description=(
            "Let the clan know which raids you enjoy so we can organise masses!\n\n"
            "🪦 **Tombs of Amascut** — The Tombs await\n"
            "💎 **Chambers of Xeric** — The Chambers call\n"
            "🩸 **Theatre of Blood** — Enter the Theatre\n\n"
            "*Click a button to add or remove a role. Pick as many as you like!*"
        ),
        color=discord.Color.red()
    )
    embed3.set_footer(text="Avera Clan • Click to toggle a role")
    await channel.send(embed=embed3, view=RaidRoleView())

    if ctx.channel.id != REACTION_ROLES_CHANNEL_ID:
        await ctx.send(f"✅ Role panels posted in <#{REACTION_ROLES_CHANNEL_ID}>!")


# ============================================================
#  CLAN DASHBOARD
# ============================================================

DASHBOARD_CHANNEL_ID = 1479551190189736199
SHOP_NOTIFY_CHANNEL_ID = 1479932547550150686

# Stores the message ID of the posted dashboard so we can edit it
dashboard_message_id = None

# ── Coffer Data ──────────────────────────────────────────────
# coffer_balance: current GP in the coffer
# coffer_donations: list of { member, amount, note, timestamp }
# coffer_payouts: list of { reason, amount, authorized_by, timestamp }
coffer_balance = 0
coffer_donations = []
coffer_payouts = []

# ── Giveaways ────────────────────────────────────────────────
# active_giveaways: list of { prize, ends, hosted_by }
active_giveaways = []


def format_gp(amount):
    """Formats a GP number with commas e.g. 1,500,000 gp"""
    return f"{amount:,} gp"


def build_dashboard_embed(guild):
    """Builds the full dashboard embed from current data."""
    now = datetime.now().strftime("%d %b %Y %I:%M %p")

    embed = discord.Embed(
        title="🏰 Avera Clan Dashboard",
        description=f"*Last refreshed: {now}*",
        color=discord.Color.gold()
    )

    # ── ACTIVE BOUNTIES ──
    active = [(bid, b) for bid, b in bounties.items() if b["active"]]
    if active:
        bounty_text = ""
        for bid, b in active[:5]:
            status = "⏳" if bid in claim_channels else "🟢"
            bounty_text += f"{status} **#{bid} — {b['target']}** · {b['points']} pts\n"
        if len(active) > 5:
            bounty_text += f"*...and {len(active) - 5} more*"
    else:
        bounty_text = "*No active bounties right now.*"
    embed.add_field(name="🎯 Active Bounties", value=bounty_text, inline=False)

    # ── UPCOMING EVENTS ──
    if clan_events:
        events_text = ""
        for i, e in enumerate(clan_events[:4], 1):
            events_text += f"**#{i} — {e['name']}**\n📅 {e['datetime']}\n"
        if len(clan_events) > 4:
            events_text += f"*...and {len(clan_events) - 4} more*"
    else:
        events_text = "*No upcoming events scheduled.*"
    embed.add_field(name="📅 Upcoming Events", value=events_text, inline=False)

    # ── ACTIVE GIVEAWAYS ──
    if active_giveaways:
        giveaway_text = ""
        for g in active_giveaways[:3]:
            giveaway_text += f"🎁 **{g['prize']}** — ends {g['ends']} *(hosted by {g['hosted_by']})*\n"
    else:
        giveaway_text = "*No active giveaways right now.*"
    embed.add_field(name="🎁 Active Giveaways", value=giveaway_text, inline=False)

    embed.add_field(name="​", value="─────────────────────────", inline=False)

    # ── CLAN STATS ──
    # Top 3 bounty completers
    bounty_counts = {}
    for b in bounties.values():
        if not b["active"] and b.get("claimed_by"):
            bounty_counts[b["claimed_by"]] = bounty_counts.get(b["claimed_by"], 0) + 1
    if bounty_counts:
        top_hunters = sorted(bounty_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        medals = ["🥇", "🥈", "🥉"]
        hunters_text = "\n".join([f"{medals[i]} **{name}** — {count} bounty{'s' if count != 1 else ''}" for i, (name, count) in enumerate(top_hunters)])
    else:
        hunters_text = "*No bounties claimed yet.*"
    embed.add_field(name="🏹 Top Bounty Hunters", value=hunters_text, inline=True)

    # Top 3 points earners
    if points_data:
        sorted_pts = sorted(points_data.items(), key=lambda x: x[1], reverse=True)[:3]
        medals = ["🥇", "🥈", "🥉"]
        pts_text = ""
        for i, (uid, pts) in enumerate(sorted_pts):
            member = guild.get_member(int(uid)) if guild else None
            name = member.display_name if member else "Unknown"
            pts_text += f"{medals[i]} **{name}** — {pts} pts\n"
    else:
        pts_text = "*No points awarded yet.*"
    embed.add_field(name="🏆 Top Point Earners", value=pts_text, inline=True)

    # Top 3 coffer donors
    if coffer_donations:
        donor_totals = {}
        for d in coffer_donations:
            donor_totals[d["member"]] = donor_totals.get(d["member"], 0) + d["amount"]
        top_donors = sorted(donor_totals.items(), key=lambda x: x[1], reverse=True)[:3]
        medals = ["🥇", "🥈", "🥉"]
        donors_text = "\n".join([f"{medals[i]} **{name}** — {format_gp(amt)}" for i, (name, amt) in enumerate(top_donors)])
    else:
        donors_text = "*No donations recorded yet.*"
    embed.add_field(name="💰 Top Coffer Supporters", value=donors_text, inline=True)

    embed.add_field(name="​", value="─────────────────────────", inline=False)

    # ── CLAN COFFER ──
    embed.add_field(
        name="🏦 Clan Coffer",
        value=f"**Current Balance:** {format_gp(coffer_balance)}",
        inline=False
    )

    # Recent donations (last 5)
    if coffer_donations:
        recent_donations = coffer_donations[-5:][::-1]
        don_text = ""
        for d in recent_donations:
            note = f" *({d['note']})*" if d.get("note") else ""
            don_text += f"➕ **{d['member']}** — {format_gp(d['amount'])}{note} · {d['timestamp']}\n"
    else:
        don_text = "*No donations recorded yet.*"
    embed.add_field(name="💚 Recent Donations", value=don_text, inline=True)

    # Recent payouts (last 5)
    if coffer_payouts:
        recent_payouts = coffer_payouts[-5:][::-1]
        pay_text = ""
        for p in recent_payouts:
            pay_text += f"➖ **{p['reason']}** — {format_gp(p['amount'])} · {p['timestamp']}\n"
    else:
        pay_text = "*No payouts recorded yet.*"
    embed.add_field(name="🔴 Recent Payouts", value=pay_text, inline=True)

    embed.set_footer(text="Avera Clan HQ • Press 🔄 Refresh to update")
    return embed


class DashboardView(discord.ui.View):
    """Persistent refresh button on the dashboard."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="dashboard_refresh")
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = build_dashboard_embed(interaction.guild)
        await interaction.message.edit(embed=embed, view=DashboardView())
        await interaction.response.send_message("✅ Dashboard refreshed!", ephemeral=True)


@bot.command(name="dashboard")
@commands.has_permissions(manage_guild=True)
async def post_dashboard(ctx):
    """Post or refresh the clan dashboard. Admin only. Usage: !dashboard"""
    global dashboard_message_id

    channel = bot.get_channel(DASHBOARD_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the dashboard channel.")
        return

    embed = build_dashboard_embed(ctx.guild)

    # If we have an existing message, try to edit it
    if dashboard_message_id:
        try:
            msg = await channel.fetch_message(dashboard_message_id)
            await msg.edit(embed=embed, view=DashboardView())
            if ctx.channel.id != DASHBOARD_CHANNEL_ID:
                await ctx.send(f"✅ Dashboard updated in <#{DASHBOARD_CHANNEL_ID}>!")
            return
        except discord.NotFound:
            pass

    # Otherwise post a fresh one
    msg = await channel.send(embed=embed, view=DashboardView())
    dashboard_message_id = msg.id
    if ctx.channel.id != DASHBOARD_CHANNEL_ID:
        await ctx.send(f"✅ Dashboard posted in <#{DASHBOARD_CHANNEL_ID}>!")


# ── Coffer Commands (Admin only) ─────────────────────────────

@bot.command(name="cofferdeposit")
@commands.has_permissions(manage_guild=True)
async def coffer_deposit(ctx, member: discord.Member = None, amount: int = None, *, note: str = ""):
    """Log a donation to the clan coffer. Admin only.
    Usage: !cofferdeposit @member <amount> [note]
    Example: !cofferdeposit @Jerzi 500000 Weekly donation"""
    global coffer_balance
    if not member or amount is None:
        await ctx.send("❌ Usage: `!cofferdeposit @member <amount> [note]`\nExample: `!cofferdeposit @Jerzi 500000 Weekly donation`")
        return
    if amount <= 0:
        await ctx.send("❌ Amount must be a positive number.")
        return

    coffer_balance += amount
    coffer_donations.append({
        "member": member.display_name,
        "amount": amount,
        "note": note,
        "timestamp": datetime.now().strftime("%d %b %Y")
    })

    embed = discord.Embed(
        title="💚 Coffer Donation Recorded",
        description=(
            f"**{member.display_name}** donated **{format_gp(amount)}** to the Avera coffer!\n"
            f"{'*' + note + '*' if note else ''}\n\n"
            f"**New Coffer Balance:** {format_gp(coffer_balance)}"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Logged by {ctx.author.display_name}")
    save_data()
    await ctx.send(embed=embed)


@bot.command(name="cofferpayout")
@commands.has_permissions(manage_guild=True)
async def coffer_payout(ctx, amount: int = None, *, reason: str = None):
    """Log a payout from the clan coffer. Admin only.
    Usage: !cofferpayout <amount> <reason>
    Example: !cofferpayout 1000000 Cox mass prize"""
    global coffer_balance
    if amount is None or not reason:
        await ctx.send("❌ Usage: `!cofferpayout <amount> <reason>`\nExample: `!cofferpayout 1000000 Cox mass prize`")
        return
    if amount <= 0:
        await ctx.send("❌ Amount must be a positive number.")
        return
    if amount > coffer_balance:
        await ctx.send(f"❌ Insufficient coffer balance. Current balance: **{format_gp(coffer_balance)}**")
        return

    coffer_balance -= amount
    coffer_payouts.append({
        "reason": reason,
        "amount": amount,
        "authorized_by": ctx.author.display_name,
        "timestamp": datetime.now().strftime("%d %b %Y")
    })

    embed = discord.Embed(
        title="🔴 Coffer Payout Recorded",
        description=(
            f"**{format_gp(amount)}** paid out from the Avera coffer.\n"
            f"**Reason:** {reason}\n\n"
            f"**New Coffer Balance:** {format_gp(coffer_balance)}"
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Authorized by {ctx.author.display_name}")
    save_data()
    await ctx.send(embed=embed)


@bot.command(name="cofferbalance")
async def coffer_balance_cmd(ctx):
    """Check the current clan coffer balance. Usage: !cofferbalance"""
    embed = discord.Embed(
        title="🏦 Avera Clan Coffer",
        description=f"**Current Balance:** {format_gp(coffer_balance)}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Avera Clan Treasury")
    await ctx.send(embed=embed)


# ── Giveaway Commands (Admin only) ───────────────────────────

@bot.command(name="addgiveaway")
@commands.has_permissions(manage_guild=True)
async def add_giveaway(ctx, *, details: str = None):
    """Add an active giveaway to the dashboard. Admin only.
    Usage: !addgiveaway <prize> | <end date/time>
    Example: !addgiveaway 10M GP | Sunday 8PM EST"""
    if not details or "|" not in details:
        await ctx.send("\u274c Usage: `!addgiveaway <prize> | <end date/time>`\nExample: `!addgiveaway 10M GP | Sunday 8PM EST`")
        return

    parts = [p.strip() for p in details.split("|")]
    active_giveaways.append({
        "prize": parts[0],
        "ends": parts[1],
        "hosted_by": ctx.author.display_name
    })
    await ctx.send(f"✅ Giveaway added: **{parts[0]}** ending **{parts[1]}**. Refresh the dashboard to see it!")


@bot.command(name="endgiveaway")
@commands.has_permissions(manage_guild=True)
async def end_giveaway(ctx, number: int = None):
    """Remove a giveaway from the dashboard. Admin only.
    Usage: !endgiveaway <number>"""
    if not number or number < 1 or number > len(active_giveaways):
        await ctx.send(f"❌ Please provide a valid giveaway number between 1 and {len(active_giveaways)}.")
        return
    removed = active_giveaways.pop(number - 1)
    await ctx.send(f"✅ Giveaway **{removed['prize']}** removed. Refresh the dashboard to update!")


# ============================================================
#  CLAN SHOP
# ============================================================

# Shop items: { item_id: { name, cost, description, emoji } }
SHOP_ITEMS = {
    1: {
        "name": "Skill of the Week",
        "cost": 25,
        "emoji": "📚",
        "description": "Choose the next **Skill of the Week** for the clan to grind together!",
        "detail": "After purchase, tell an admin which skill you want featured."
    },
    2: {
        "name": "Boss of the Week",
        "cost": 25,
        "emoji": "💀",
        "description": "Choose the next **Boss of the Week** for the clan to slay together!",
        "detail": "After purchase, tell an admin which boss you want featured."
    },
    3: {
        "name": "Create Your Own Room",
        "cost": 100,
        "emoji": "🏠",
        "description": "Get your very own **custom Discord room**! A new category with a voice channel named after you.",
        "detail": "After purchase, tell an admin your desired category name and voice channel name/font. See <#1479933965740802139> as an example!"
    },
}

# Tracks pending shop redemptions for admin review: [ { item_id, buyer, detail_request, timestamp } ]
shop_redemptions = []


def build_shop_embed(guild=None):
    """Builds the clan shop embed."""
    embed = discord.Embed(
        title="🛒 Avera Clan Shop",
        description=(
            "Spend your hard-earned clan points on exclusive rewards!\n"
            "Use `!redeem <item number>` to purchase an item.\n"
            "Check your points with `!points`.\n"
        ),
        color=discord.Color.gold()
    )

    for item_id, item in SHOP_ITEMS.items():
        embed.add_field(
            name=f"{item['emoji']} #{item_id} — {item['name']} · {item['cost']} pts",
            value=f"{item['description']}\n*{item['detail']}*",
            inline=False
        )

    embed.set_footer(text="Avera Clan Shop • Use !redeem <#> to purchase")
    return embed


class ShopView(discord.ui.View):
    """Persistent shop panel with redeem buttons."""
    def __init__(self):
        super().__init__(timeout=None)
        for item_id, item in SHOP_ITEMS.items():
            self.add_item(ShopButton(item_id, item))


class ShopButton(discord.ui.Button):
    def __init__(self, item_id, item):
        super().__init__(
            label=f"{item['name']} — {item['cost']} pts",
            emoji=item["emoji"],
            style=discord.ButtonStyle.primary if item["cost"] <= 25 else discord.ButtonStyle.success,
            custom_id=f"shop_item_{item_id}"
        )
        self.item_id = item_id
        self.item = item

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        user_id = str(user.id)
        balance = points_data.get(user_id, 0)
        cost = self.item["cost"]

        if balance < cost:
            await interaction.response.send_message(
                f"❌ You don't have enough points!\n"
                f"**{self.item['name']}** costs **{cost} pts** but you only have **{balance} pts**.\n"
                f"Keep earning points through events and bounties!",
                ephemeral=True
            )
            return

        # Show a modal to collect extra info for the purchase
        modal = RedeemModal(self.item_id, self.item)
        await interaction.response.send_modal(modal)


class RedeemModal(discord.ui.Modal):
    def __init__(self, item_id, item):
        super().__init__(title=f"Redeem: {item['name']}")
        self.item_id = item_id
        self.item = item

        if item_id == 1:
            self.detail = discord.ui.TextInput(
                label="Which skill do you want?",
                placeholder="e.g. Slayer, Fishing, Woodcutting...",
                max_length=50
            )
        elif item_id == 2:
            self.detail = discord.ui.TextInput(
                label="Which boss do you want?",
                placeholder="e.g. Zulrah, Vorkath, Cox...",
                max_length=50
            )
        elif item_id == 3:
            self.detail = discord.ui.TextInput(
                label="Room name & voice channel name",
                placeholder="e.g. Category: Jerzi's Room | Voice: The Hangout",
                max_length=100
            )
        else:
            self.detail = discord.ui.TextInput(
                label="Any additional details?",
                placeholder="Enter any details here...",
                max_length=200,
                required=False
            )
        self.add_item(self.detail)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user
        user_id = str(user.id)
        cost = self.item["cost"]

        # Deduct points
        points_data[user_id] = points_data.get(user_id, 0) - cost
        new_balance = points_data[user_id]

        # Log the redemption for admin review
        redemption = {
            "item_id": self.item_id,
            "item_name": self.item["name"],
            "buyer": user.display_name,
            "buyer_id": user_id,
            "detail": self.detail.value,
            "timestamp": datetime.now().strftime("%d %b %Y %I:%M %p"),
            "fulfilled": False
        }
        shop_redemptions.append(redemption)
        redemption_index = len(shop_redemptions)

        # Notify admins via the ticket channel or a DM to the buyer
        # Post redemption notice in the bounty channel so admins see it
        notify_channel = bot.get_channel(SHOP_NOTIFY_CHANNEL_ID)

        admin_embed = discord.Embed(
            title=f"🛒 Shop Redemption — {self.item['emoji']} {self.item['name']}",
            description=(
                f"{user.mention} has redeemed **{self.item['name']}** for **{cost} pts**!\n\n"
                f"📋 **Their request:** {self.detail.value}\n\n"
                f"*Use `!fulfil {redemption_index}` once completed, or `!redemptions` to see all pending.*"
            ),
            color=discord.Color.gold()
        )
        admin_embed.set_footer(text=f"Redemption #{redemption_index} • {redemption['timestamp']}")

        if notify_channel:
            await notify_channel.send(embed=admin_embed)

        # Confirm to the buyer
        confirm_embed = discord.Embed(
            title=f"✅ Purchase Successful!",
            description=(
                f"You've redeemed **{self.item['emoji']} {self.item['name']}** for **{cost} pts**!\n\n"
                f"📋 **Your request:** {self.detail.value}\n\n"
                f"An admin will action your request shortly. Your new balance is **{new_balance} pts**."
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)


@bot.command(name="shop")
async def show_shop(ctx):
    """View the clan shop. Usage: !shop"""
    embed = build_shop_embed(ctx.guild)
    await ctx.send(embed=embed, view=ShopView())


@bot.command(name="shopanel")
@commands.has_permissions(manage_guild=True)
async def shop_panel(ctx):
    """Post a permanent shop panel. Admin only. Usage: !shopanel"""
    embed = build_shop_embed(ctx.guild)
    await ctx.send(embed=embed, view=ShopView())
    if ctx.guild:
        await ctx.message.delete()


@bot.command(name="redeem")
async def redeem_item(ctx, item_id: int = None):
    """Redeem a shop item with points. Usage: !redeem <item number>"""
    if item_id is None or item_id not in SHOP_ITEMS:
        items_list = ", ".join([f"`{i}` {v['emoji']} {v['name']}" for i, v in SHOP_ITEMS.items()])
        await ctx.send(f"❌ Invalid item. Use `!shop` to see available items.\nAvailable: {items_list}")
        return

    item = SHOP_ITEMS[item_id]
    user_id = str(ctx.author.id)
    balance = points_data.get(user_id, 0)
    cost = item["cost"]

    if balance < cost:
        await ctx.send(
            f"❌ You don't have enough points!\n"
            f"**{item['name']}** costs **{cost} pts** but you only have **{balance} pts**."
        )
        return

    # Deduct and log
    points_data[user_id] = balance - cost
    new_balance = points_data[user_id]

    shop_redemptions.append({
        "item_id": item_id,
        "item_name": item["name"],
        "buyer": ctx.author.display_name,
        "buyer_id": user_id,
        "detail": "(redeemed via command — no extra details provided)",
        "timestamp": datetime.now().strftime("%d %b %Y %I:%M %p"),
        "fulfilled": False
    })
    redemption_index = len(shop_redemptions)

    notify_channel = bot.get_channel(SHOP_NOTIFY_CHANNEL_ID)
    admin_embed = discord.Embed(
        title=f"🛒 Shop Redemption — {item['emoji']} {item['name']}",
        description=(
            f"{ctx.author.mention} redeemed **{item['name']}** for **{cost} pts**.\n\n"
            f"*Use `!fulfil {redemption_index}` once completed.*"
        ),
        color=discord.Color.gold()
    )
    if notify_channel:
        await notify_channel.send(embed=admin_embed)

    await ctx.send(
        f"✅ You've redeemed **{item['emoji']} {item['name']}** for **{cost} pts**!\n"
        f"An admin will action your request. New balance: **{new_balance} pts**."
    )


@bot.command(name="redemptions")
@commands.has_permissions(manage_guild=True)
async def list_redemptions(ctx):
    """View all pending shop redemptions. Admin only."""
    pending = [(i+1, r) for i, r in enumerate(shop_redemptions) if not r["fulfilled"]]

    if not pending:
        await ctx.send("✅ No pending redemptions!")
        return

    embed = discord.Embed(title="🛒 Pending Shop Redemptions", color=discord.Color.gold())
    for idx, r in pending:
        embed.add_field(
            name=f"#{idx} — {r['item_name']} · {r['buyer']}",
            value=f"📋 {r['detail']}\n🕐 {r['timestamp']}",
            inline=False
        )
    await ctx.send(embed=embed)


@bot.command(name="fulfil")
@commands.has_permissions(manage_guild=True)
async def fulfil_redemption(ctx, redemption_id: int = None):
    """Mark a shop redemption as fulfilled. Admin only. Usage: !fulfil <id>"""
    if redemption_id is None or redemption_id < 1 or redemption_id > len(shop_redemptions):
        await ctx.send(f"❌ Invalid redemption ID. Use `!redemptions` to see pending ones.")
        return

    r = shop_redemptions[redemption_id - 1]
    if r["fulfilled"]:
        await ctx.send(f"❌ Redemption #{redemption_id} is already fulfilled.")
        return

    r["fulfilled"] = True

    # Try to notify the buyer
    guild = ctx.guild
    member = guild.get_member(int(r["buyer_id"])) if guild else None

    embed = discord.Embed(
        title="✅ Redemption Fulfilled!",
        description=(
            f"Redemption **#{redemption_id}** — **{r['item_name']}** for **{r['buyer']}** has been marked as fulfilled!\n\n"
            f"📋 Request: {r['detail']}"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Fulfilled by {ctx.author.display_name}")
    await ctx.send(embed=embed)

    if member:
        try:
            await member.send(
                f"🎉 Your **{r['item_name']}** redemption has been fulfilled by an admin!\n"
                f"📋 Your request: *{r['detail']}*\n\n"
                f"Enjoy! ⚔️"
            )
        except discord.Forbidden:
            pass


# ============================================================
#  WELCOME PANEL
# ============================================================

WELCOME_PANEL_CHANNEL_ID = 1459412579947642971


@bot.command(name="welcomepanel")
@commands.has_permissions(manage_guild=True)
async def welcome_panel(ctx):
    """Post the permanent welcome panel. Admin only. Usage: !welcomepanel"""
    channel = bot.get_channel(WELCOME_PANEL_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the welcome channel. Check the channel ID in bot.py.")
        return

    embed = discord.Embed(
        title="⚔️ Welcome to Avera!",
        description=(
            "We're an **Old School RuneScape** clan built on community, progression, and having fun together.\n\n"
            "Whether you're a seasoned veteran or just starting out, there's a place for you here.\n\n"
            "🔗 **Discord Invite:** https://discord.gg/Avera"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="📋 How to Join",
        value=(
            "1️⃣ Search for the **\"Avera\"** clan chat in-game\n"
            "2️⃣ Join the chat and let a **staff member** know you'd like to join\n"
            "3️⃣ Get accepted and grab your roles below — welcome to the clan! 🎉"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 What We Get Up To",
        value=(
            "🎯 **Custom Bounty & Point System** — Complete bounties, attend & host events, win competitions, and more to earn points — then spend them in the clan shop\n"
            "📚 **Skill of the Week** — Alternating weekly with Boss of the Week — community skill grind\n"
            "💀 **Boss of the Week** — Alternating weekly with Skill of the Week — featured boss for the clan to slay\n"
            "⚔️ **Clan PvM Masses** — Group bossing sessions open to all\n"
            "🧩 **Learner Raids** — New to raids? We'll teach you!\n"
            "🎁 **Giveaways & Events** — Regular community events with prizes"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Key Channels",
        value=(
            f"🎭 <#1459413079438917672> — Assign yourself roles\n"
            f"📜 <#1479886542771323012> — Read the clan rules\n"
            f"📣 <#1459412856146624643> — Announcements\n"
            f"🏰 <#1479551190189736199> — Clan Dashboard\n"
            f"🎯 <#1479471419577602199> — Custom Clan Bounties"
        ),
        inline=False
    )

    embed.set_footer(text="Avera Clan • OSRS • discord.gg/Avera")
    embed.timestamp = datetime.now()

    await channel.send(embed=embed)

    if ctx.channel.id != WELCOME_PANEL_CHANNEL_ID:
        await ctx.send(f"✅ Welcome panel posted in <#{WELCOME_PANEL_CHANNEL_ID}>!")


# ============================================================
#  BOUNTY INFO PANEL
# ============================================================

@bot.command(name="bountypanel")
@commands.has_permissions(manage_guild=True)
async def bounty_panel(ctx):
    """Post the permanent bounty info panel. Admin only. Usage: !bountypanel"""
    channel = bot.get_channel(BOUNTY_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the bounties channel.")
        return

    embed = discord.Embed(
        title="🎯 Avera Clan Bounties",
        description=(
            "Welcome to the **Avera Bounty Board**!\n\n"
            "Bounties are an opportunity to slay a boss and get rewarded. Complete them, submit your proof, "
            "and earn **clan points** that can be spent on exclusive rewards in the clan shop. "
            "The harder the bounty, the bigger the reward! ⚔️"
        ),
        color=discord.Color.red()
    )

    embed.add_field(
        name="📋 How It Works",
        value=(
            "1️⃣ Listen for word of a bounty\n"
            "2️⃣ Complete the bounty challenge in-game\n"
            "3️⃣ Use `!claim <bounty ID>` with a **screenshot attached** as proof\n"
            "⚠️ **YOUR SCREENSHOT MUST SHOW TODAY'S DATE — PROOF WITHOUT A VISIBLE TIMESTAMP WILL BE AUTOMATICALLY DENIED**\n"
            "4️⃣ A private review channel is created between you and staff\n"
            "5️⃣ Staff review your proof and approve or deny your claim\n"
            "6️⃣ Points are awarded automatically on approval! 🎉"
        ),
        inline=False
    )

    embed.add_field(
        name="🕹️ Commands",
        value=(
            "`!bounties` — View all currently active bounties\n"
            "`!claim <id>` — Claim a bounty *(attach a screenshot!)*\n"
            "`!points` — Check your current point balance\n"
            "`!leaderboard` — See the top point earners in the clan"
        ),
        inline=False
    )

    embed.add_field(
        name="💰 What Can I Spend Points On?",
        value=(
            "Points can be redeemed in the **Clan Shop** for exclusive rewards:\n\n"
            "📚 **Skill of the Week** — 25 pts — Choose the next skill the clan grinds\n"
            "💀 **Boss of the Week** — 25 pts — Choose the next featured boss\n"
            "🏠 **Create Your Own Room** — 100 pts — Get your own custom Discord category & voice channel\n\n"
            f"👉 Head to <#1479472183221682298> to browse and redeem!"
        ),
        inline=False
    )

    embed.add_field(
        name="📌 Tips",
        value=(
            "• Multiple members can claim the same bounty — first approved wins the points\n"
            "• Make sure your screenshot clearly shows the completed challenge\n"
            "• Bounties stay open until claimed or removed by staff\n"
            "• Keep an eye on this channel and be the first to claim!"
        ),
        inline=False
    )

    embed.set_footer(text="Avera Clan • Good luck, and may your drops be plentiful! 🍀")

    await channel.send(embed=embed)

    if ctx.channel.id != BOUNTY_CHANNEL_ID:
        await ctx.send(f"✅ Bounty info panel posted in <#{BOUNTY_CHANNEL_ID}>!")


# ============================================================
#  RULES PANEL
# ============================================================

RULES_CHANNEL_ID = 1479886542771323012


@bot.command(name="rulespanel")
@commands.has_permissions(manage_guild=True)
async def rules_panel(ctx):
    """Post the permanent rules panel. Admin only. Usage: !rulespanel"""
    channel = bot.get_channel(RULES_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the rules channel.")
        return

    embed = discord.Embed(
        title="📜 Avera Clan Rules",
        description=(
            "Welcome to **Avera**! To keep things fun and relaxed for everyone, "
            "we ask that all members follow these simple rules.\n\n"
            "We're a chill clan — we just ask for basic respect and good vibes. 🎮"
        ),
        color=discord.Color.dark_red()
    )

    embed.add_field(
        name="1️⃣ Be Respectful",
        value="Treat everyone with basic respect. Banter is fine — bullying isn't.",
        inline=False
    )
    embed.add_field(
        name="2️⃣ No Begging, Scamming or PKing Clan Members",
        value="We're a community, not a target. Don't take advantage of your fellow clanmates.",
        inline=False
    )
    embed.add_field(
        name="3️⃣ Keep it Clean",
        value="Avoid excessive toxicity, racism, or hate speech of any kind.",
        inline=False
    )
    embed.add_field(
        name="4️⃣ No Drama",
        value="Sort personal issues privately. Don't bring beef into clan chat or Discord.",
        inline=False
    )
    embed.add_field(
        name="5️⃣ Stay Reasonably Active",
        value="Real life comes first — we get it! Just let staff know if you'll be away for a while.",
        inline=False
    )
    embed.add_field(
        name="6️⃣ Represent Avera in a Positive Light",
        value="Be a good face for the clan wherever you are — in-game, on Discord, and beyond.",
        inline=False
    )
    embed.add_field(
        name="7️⃣ Clan Events",
        value="Participation is encouraged but never forced. Show up when you can — it's always more fun together!",
        inline=False
    )
    embed.add_field(
        name="8️⃣ No Advertising",
        value="Do not advertise outside communities or clans. Streaming is the only exception.",
        inline=False
    )
    embed.add_field(
        name="9️⃣ Have Fun",
        value="This is a game. Enjoy it, help each other out, and don't take it too seriously. 🎮",
        inline=False
    )

    embed.add_field(
        name="\u200b",
        value=(
            "*Failure to follow these rules may result in a warning, kick, or ban depending on severity.\n"
            "For questions or concerns, open a ticket or speak to a staff member.*"
        ),
        inline=False
    )

    embed.set_footer(text="Avera Clan • Last updated March 2026")

    await channel.send(embed=embed)

    if ctx.channel.id != RULES_CHANNEL_ID:
        await ctx.send(f"✅ Rules panel posted in <#{RULES_CHANNEL_ID}>!")


# ============================================================
#  AUTOMATED FEATURES — Milestones, Recap, Polls, Streaks, Verify
# ============================================================

ANNOUNCEMENTS_CHANNEL_ID = 1459412856146624643
MEMBER_MILESTONES = [10, 20, 50, 100, 200, 500]
STREAK_THRESHOLD = 3
STREAK_BONUS = 3

# Tracks which milestones have already been announced
announced_milestones = set()

# Tracks weekly stats for recap (resets every Monday)
weekly_stats = {
    "bounties_completed": 0,
    "points_awarded": 0,
    "events_held": 0,
    "top_earner_id": None,
    "top_earner_pts": 0,
    "weekly_points": {}  # { user_id: points earned this week }
}

# Tracks event attendance streaks: { user_id: consecutive_count }
event_streaks = {}

# RSN verification: { user_id: rsn }
verified_rsns = {}

# Verification timestamps: { user_id: ISO timestamp string }
verify_times = {}

# Referrals: { new_member_id: referrer_id }
referrals = {}
REFERRAL_BONUS = 5

# Active polls: { message_id: { question, options, votes: {user_id: option_index}, ends_at, channel_id } }
active_polls = {}


# ── Member Milestone Checker (runs every 10 minutes) ─────────

@tasks.loop(minutes=10)
async def check_member_milestones():
    for guild in bot.guilds:
        count = guild.member_count
        for milestone in MEMBER_MILESTONES:
            if count >= milestone and milestone not in announced_milestones:
                announced_milestones.add(milestone)
                channel = bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
                if channel:
                    embed = discord.Embed(
                        title=f"🎉 {milestone} Members!",
                        description=(
                            f"**Avera has reached {milestone} members!** 🏰\n\n"
                            f"This is a huge milestone for our clan and it wouldn\'t be possible "
                            f"without every single one of you. Thank you for being part of something special.\n\n"
                            + (f"🎯 **Reminder:** Skill of the Week & Boss of the Week events kick off at **20 members** — we\'re getting close!" if milestone < 20
                               else f"⚔️ **Skill of the Week & Boss of the Week are now active!** Watch <#1479471419577602199> for updates." if milestone == 20
                               else f"The clan keeps growing and so do the adventures ahead. Here\'s to {milestone} more! ⚔️")
                        ),
                        color=discord.Color.gold()
                    )
                    embed.set_footer(text="Avera Clan • Growing stronger every day")
                    embed.timestamp = datetime.now()
                    await channel.send("@everyone", embed=embed)


# ── Weekly Recap (runs every Monday at 9AM) ──────────────────

@tasks.loop(hours=24)
async def weekly_recap():
    now = datetime.now()
    if now.weekday() != 0:  # 0 = Monday
        return

    channel = bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    if not channel:
        return

    # Top earner this week
    top_name = "No one yet"
    top_pts = 0
    if weekly_stats["weekly_points"]:
        top_id = max(weekly_stats["weekly_points"], key=weekly_stats["weekly_points"].get)
        top_pts = weekly_stats["weekly_points"][top_id]
        for guild in bot.guilds:
            member = guild.get_member(int(top_id))
            if member:
                top_name = member.display_name
                break

    embed = discord.Embed(
        title="📊 Avera Weekly Recap",
        description=f"Here\'s a look at what the clan got up to this week! 💪",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎯 Bounties Completed", value=str(weekly_stats["bounties_completed"]), inline=True)
    embed.add_field(name="🏆 Points Awarded", value=str(weekly_stats["points_awarded"]), inline=True)
    embed.add_field(name="📅 Events Held", value=str(weekly_stats["events_held"]), inline=True)
    embed.add_field(
        name="⭐ Top Earner of the Week",
        value=f"**{top_name}** — {top_pts} pts" if top_pts > 0 else "No points awarded this week",
        inline=False
    )
    embed.set_footer(text="Avera Clan • Weekly Recap — see you next week!")
    embed.timestamp = datetime.now()

    await channel.send(embed=embed)

    # Reset weekly stats
    weekly_stats["bounties_completed"] = 0
    weekly_stats["points_awarded"] = 0
    weekly_stats["events_held"] = 0
    weekly_stats["weekly_points"] = {}


# ── Poll System ───────────────────────────────────────────────

@bot.command(name="poll")
@commands.has_permissions(manage_guild=True)
async def create_poll(ctx, duration: int = None, *, details: str = None):
    """Create a poll. Admin only.
    Usage: !poll <duration in minutes> <question> | <option1> | <option2> | ...
    Example: !poll 60 Which boss should we mass? | Zulrah | Vorkath | Cox"""
    if duration is None or not details or "|" not in details:
        await ctx.send(
            "❌ Usage: `!poll <duration in minutes> <question> | <option1> | <option2> ...`\n"
            "Example: `!poll 60 Which boss should we mass? | Zulrah | Vorkath | Cox`"
        )
        return

    parts = [p.strip() for p in details.split("|")]
    question = parts[0]
    options = parts[1:]

    if len(options) < 2:
        await ctx.send("❌ Please provide at least 2 options.")
        return
    if len(options) > 5:
        await ctx.send("❌ Maximum 5 options per poll.")
        return

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    options_text = "\n".join([f"{number_emojis[i]} {opt}" for i, opt in enumerate(options)])

    embed = discord.Embed(
        title=f"📊 Poll — {question}",
        description=(
            f"{options_text}\n\n"
            f"*React with the number to vote! Poll closes in {duration} minute(s).*"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"Poll by {ctx.author.display_name} • {duration} min")
    embed.timestamp = datetime.now()

    msg = await ctx.send(embed=embed)

    for i in range(len(options)):
        await msg.add_reaction(number_emojis[i])

    active_polls[msg.id] = {
        "question": question,
        "options": options,
        "channel_id": ctx.channel.id,
        "duration": duration
    }

    # Close poll after duration
    await asyncio.sleep(duration * 60)

    # Fetch updated message to get reaction counts
    try:
        msg = await ctx.channel.fetch_message(msg.id)
    except discord.NotFound:
        return

    results = []
    for i, option in enumerate(options):
        reaction = discord.utils.get(msg.reactions, emoji=number_emojis[i])
        count = (reaction.count - 1) if reaction else 0  # subtract bot's own reaction
        results.append((option, count))

    results.sort(key=lambda x: x[1], reverse=True)
    winner = results[0]

    result_text = "\n".join([
        f"{number_emojis[i]} **{opt}** — {count} vote(s) {'👑' if i == 0 else ''}"
        for i, (opt, count) in enumerate(results)
    ])

    result_embed = discord.Embed(
        title=f"📊 Poll Closed — {question}",
        description=(
            f"{result_text}\n\n"
            f"🏆 **Winner: {winner[0]}** with {winner[1]} vote(s)!"
            if winner[1] > 0 else f"{result_text}\n\n*No votes were cast.*"
        ),
        color=discord.Color.green()
    )
    result_embed.set_footer(text=f"Poll by {ctx.author.display_name}")
    result_embed.timestamp = datetime.now()

    await ctx.send(embed=result_embed)
    active_polls.pop(msg.id, None)


# ── Streak Rewards ────────────────────────────────────────────

def update_streak(user_id, display_name):
    """Call when a member attends an event. Returns bonus points if streak hit."""
    event_streaks[user_id] = event_streaks.get(user_id, 0) + 1
    streak = event_streaks[user_id]
    if streak % STREAK_THRESHOLD == 0:
        points_data[user_id] = points_data.get(user_id, 0) + STREAK_BONUS
        return streak, STREAK_BONUS
    return streak, 0


@bot.command(name="streak")
async def check_streak(ctx, member: discord.Member = None):
    """Check your event attendance streak. Usage: !streak [@member]"""
    target = member or ctx.author
    streak = event_streaks.get(str(target.id), 0)
    next_bonus = STREAK_THRESHOLD - (streak % STREAK_THRESHOLD)

    embed = discord.Embed(
        title=f"🔥 {target.display_name}\'s Event Streak",
        description=(
            f"**Current Streak:** {streak} event(s) in a row\n"
            f"**Next bonus in:** {next_bonus} more event(s) *(+{STREAK_BONUS} pts)*"
        ),
        color=discord.Color.orange()
    )
    embed.set_footer(text="Attend events consecutively to earn streak bonuses!")
    await ctx.send(embed=embed)


# ── RSN Verification ──────────────────────────────────────────

@bot.command(name="verify")
async def verify_rsn(ctx, *, rsn: str = None):
    """Link your OSRS username to your Discord account. Usage: !verify <username>
    Example: !verify Zezima"""
    if not rsn:
        msg = await ctx.send("❌ Usage: `!verify <your OSRS username>`\nExample: `!verify Zezima`")
        if ctx.channel.id == WELCOME_PANEL_CHANNEL_ID:
            await asyncio.sleep(10)
            try:
                await msg.delete()
            except discord.NotFound:
                pass
        return

    # Check the username exists on OSRS hiscores
    checking_msg = await ctx.send(f"🔍 Checking **{rsn}** on the OSRS hiscores...")
    url = f"https://secure.runescape.com/m=hiscore_oldschool/index_lite.ws?player={rsn.replace(' ', '%20')}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 404 or response.status != 200:
                    await checking_msg.delete()
                    err_msg = await ctx.send(f"❌ **{rsn}** was not found on the OSRS hiscores. Double check the spelling and try again!")
                    if ctx.channel.id == WELCOME_PANEL_CHANNEL_ID:
                        await asyncio.sleep(10)
                        try:
                            await err_msg.delete()
                        except discord.NotFound:
                            pass
                    return
    except Exception:
        await checking_msg.delete()
        err_msg = await ctx.send("❌ Could not reach the OSRS hiscores right now. Try again in a moment.")
        if ctx.channel.id == WELCOME_PANEL_CHANNEL_ID:
            await asyncio.sleep(10)
            try:
                await err_msg.delete()
            except discord.NotFound:
                pass
        return

    # Delete the checking message now that we're done with it
    try:
        await checking_msg.delete()
    except discord.NotFound:
        pass

    user_id = str(ctx.author.id)
    old_rsn = verified_rsns.get(user_id)
    verified_rsns[user_id] = rsn

    # Record verify time only on first verification
    if user_id not in verify_times:
        verify_times[user_id] = datetime.now().isoformat()

    # Attempt to rename them in the server
    rename_text = ""
    try:
        await ctx.author.edit(nick=rsn)
        rename_text = f"\n📝 Your server nickname has been updated to **{rsn}**!"
    except discord.Forbidden:
        rename_text = "\n*(Could not update your nickname — you may be the server owner or have a higher role than the bot.)*"

    # Delete the original !verify message if sent in the welcome channel
    if ctx.channel.id == WELCOME_PANEL_CHANNEL_ID:
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

    embed = discord.Embed(
        title="✅ RSN Verified!",
        description=(
            f"{ctx.author.mention} is now verified as **{rsn}** on OSRS!"
            + (f"\n*(Previously linked to: {old_rsn})*" if old_rsn and old_rsn != rsn else "")
            + rename_text
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text="Use !whois @member to look up anyone\'s RSN")

    save_data()

    # Auto-assign rank role on verify
    total_level, ehp = await fetch_osrs_stats(rsn)
    points = points_data.get(user_id, 0)
    new_rank = get_rank(points, user_id, total_level, ehp)
    await assign_rank_role(ctx.guild, ctx.author, new_rank)

    # If in welcome channel, send confirmation then delete it after 10s so channel stays clean
    if ctx.channel.id == WELCOME_PANEL_CHANNEL_ID:
        confirm_msg = await ctx.send(embed=embed)
        await asyncio.sleep(10)
        try:
            await confirm_msg.delete()
        except discord.NotFound:
            pass
    else:
        await ctx.send(embed=embed)


@bot.command(name="whois")
async def whois(ctx, member: discord.Member = None):
    """Look up a member\'s verified OSRS username. Usage: !whois @member"""
    target = member or ctx.author
    rsn = verified_rsns.get(str(target.id))

    if not rsn:
        await ctx.send(f"❌ **{target.display_name}** hasn\'t verified their RSN yet. They can use `!verify <username>` to link it.")
        return

    embed = discord.Embed(
        title=f"🔍 {target.display_name}\'s RSN",
        description=(
            f"**OSRS Username:** {rsn}\n"
            f"[View Hiscores](https://secure.runescape.com/m=hiscore_oldschool/hiscorepersonal.ws?user1={rsn.replace(' ', '+')})"
        ),
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target.display_avatar.url)
    await ctx.send(embed=embed)


@bot.command(name="whoami")
async def whoami(ctx):
    """Check your own verified RSN. Usage: !whoami"""
    rsn = verified_rsns.get(str(ctx.author.id))
    if not rsn:
        await ctx.send(f"❌ You haven\'t verified your RSN yet. Use `!verify <username>` to link it.")
        return
    await ctx.send(f"✅ You are verified as **{rsn}** on OSRS!")


@bot.command(name="referral")
async def referral(ctx, referrer: discord.Member = None):
    """Credit a member for referring you to Avera. Usage: !referral @member
    Can only be used once. Must have verified your RSN first."""
    user_id = str(ctx.author.id)

    if not referrer:
        await ctx.send("❌ Please tag the member who referred you. Example: `!referral @Jerzi`")
        return

    if referrer.id == ctx.author.id:
        await ctx.send("❌ You can\'t refer yourself!")
        return

    if user_id in referrals:
        referrer_id = referrals[user_id]
        existing = ctx.guild.get_member(int(referrer_id))
        name = existing.display_name if existing else "someone"
        await ctx.send(f"❌ You\'ve already submitted a referral — credited to **{name}**.")
        return

    if user_id not in verified_rsns:
        await ctx.send("❌ Please verify your RSN first with `!verify <username>` before submitting a referral.")
        return

    # Award referrer
    referrer_id = str(referrer.id)
    referrals[user_id] = referrer_id
    points_data[referrer_id] = points_data.get(referrer_id, 0) + REFERRAL_BONUS
    weekly_stats["points_awarded"] += REFERRAL_BONUS
    weekly_stats["weekly_points"][referrer_id] = weekly_stats["weekly_points"].get(referrer_id, 0) + REFERRAL_BONUS
    new_total = points_data[referrer_id]

    embed = discord.Embed(
        title="🌱 Referral Logged!",
        description=(
            f"**{ctx.author.display_name}** has credited **{referrer.display_name}** for bringing them to Avera!\n\n"
            f"🎉 {referrer.mention} — **+{REFERRAL_BONUS} pts** awarded! *(New total: {new_total})*\n\n"
            f"Thanks for growing the clan! ⚔️"
        ),
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)


# ============================================================
#  FAQ PANEL
# ============================================================

FAQ_CHANNEL_ID = 1479961124949721158


@bot.command(name="faqpanel")
@commands.has_permissions(manage_guild=True)
async def faq_panel(ctx):
    """Post the permanent FAQ panel. Admin only. Usage: !faqpanel"""
    channel = bot.get_channel(FAQ_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the FAQ channel.")
        return

    # ── Embed 1: Clan Commands ─────────────────────────────
    embed1 = discord.Embed(
        title="❓ Avera FAQ & Helpful Commands",
        description=(
            "Everything you need to know about getting started in Avera and making the most of the clan bot. "
            "Use `!help` at any time for a full command list."
        ),
        color=discord.Color.gold()
    )

    embed1.add_field(
        name="👤 Getting Started",
        value=(
            f"`!verify <rsn>` — Link your OSRS username to your Discord account\n"
            f"`!whoami` — Check which RSN is linked to your account\n"
            f"`!referral @member` — Credit the person who referred you to Avera *(one time only, grants them +5 pts)*\n"
            f"`!points` — Check your current clan point balance\n"
            f"`!leaderboard` — See the top point earners in the clan"
        ),
        inline=False
    )

    embed1.add_field(
        name="🎖️ Ranks",
        value=(
            "Avera ranks are based on **time in the clan** and **in-game stats** pulled directly from the OSRS hiscores.\n\n"
            "**Automatic ranks:**\n"
            f"{RANK_EMOJIS['Recruit']} **Recruit** — Just joined\n"
            f"{RANK_EMOJIS['Corporal']} **Corporal** — Verified 1+ month\n"
            f"{RANK_EMOJIS['Sergeant']} **Sergeant** — 3+ months & Total Level 1750+ or EHP 300+\n"
            f"{RANK_EMOJIS['Noble']} **Noble** — 6+ months & Total Level 2000+ or EHP 600+\n"
            f"{RANK_EMOJIS['Legionnaire']} **Legionnaire** — 12+ months & Total Level 2200+ or EHP 1000+\n\n"
            "**Staff ranks** (Lieutenant, Captain, General) are assigned by admins only.\n\n"
            "Use `!rankcheck` to update your rank at any time, or open a **Rank Promotion** ticket from the support panel!"
        ),
        inline=False
    )

    embed1.add_field(
        name="🎯 Bounties",
        value=(
            f"`!bounties` — View all currently active bounties\n"
            f"`!claim <id>` — Claim a bounty *(attach a timestamped screenshot as proof!)*\n"
            f"📌 Head to <#1479471419577602199> to see active bounties and learn more"
        ),
        inline=False
    )

    embed1.add_field(
        name="🛒 Clan Shop",
        value=(
            f"`!shop` — Browse what you can spend your points on\n"
            f"`!redeem <#>` — Redeem a shop item with your points\n"
            f"📌 Head to <#1479472183221682298> to view the full shop panel\n\n"
            f"**💰 How to earn points:**\n"
            f"🎯 Complete a bounty and get it approved — *points vary per bounty*\n"
            f"📅 Use `!attend` during an active event — **+5 pts**\n"
            f"🔥 Attend 3 events in a row — **+3 bonus pts** streak reward\n"
            f"🌟 Host a clan event — **variable pts** *(set by admin per event)*\n"
            f"🥇 Finish 1st in a competition — **+10 pts**\n"
            f"🥈 Finish 2nd in a competition — **+5 pts**\n"
            f"🥉 Finish 3rd in a competition — **+3 pts**\n"
            f"🌱 Refer a new member who joins and verifies — **+5 pts**"
        ),
        inline=False
    )

    embed1.add_field(
        name="📅 Events",
        value=(
            f"`!events` — View upcoming clan events\n"
            f"`!attend` — Check in to an active event and earn **+5 points**\n"
            f"`!streak` — Check your consecutive event attendance streak\n"
            f"🔥 Attend **3 events in a row** to earn a streak bonus of **+3 points**"
        ),
        inline=False
    )

    embed1.add_field(
        name="🏦 Clan Coffer",
        value=(
            f"`!cofferbalance` — Check the current clan coffer balance\n"
            f"📌 Donations and payouts are tracked live on the <#1479551190189736199>"
        ),
        inline=False
    )

    embed1.add_field(
        name="🔍 Player Lookup",
        value=(
            f"`!stats <rsn>` — View a player's OSRS stats\n"
            f"`!kc <rsn>` — View a player's boss kill counts\n"
            f"`!whois @member` — See a clan member's verified OSRS username"
        ),
        inline=False
    )

    embed1.add_field(
        name="📊 Polls",
        value=(
            "Keep an eye on <#1459412856146624643> for polls posted by staff.\n"
            "React with the number emoji to cast your vote — results post automatically when the poll closes!"
        ),
        inline=False
    )

    embed1.add_field(
        name="🌱 Referral System",
        value=(
            "Did someone bring you to Avera? Give them credit!\n\n"
            "Once you've verified your RSN with `!verify <rsn>`, use `!referral @member` to credit whoever referred you. "
            "They'll receive **+5 clan points** as a thank you for growing the community.\n\n"
            "*Each member can only submit one referral, so make it count!*"
        ),
        inline=False
    )

    embed1.set_footer(text="Avera Clan • Use !help for the full command list")

    # ── Embed 2: Helpful Websites ──────────────────────────
    embed2 = discord.Embed(
        title="🌐 Helpful OSRS Websites",
        description="A collection of the most useful tools and resources for OSRS players.",
        color=discord.Color.blue()
    )

    embed2.add_field(
        name="📖 OSRS Wiki",
        value="The go-to for everything in the game — quests, bosses, items, mechanics.\n🔗 https://oldschool.runescape.wiki",
        inline=False
    )

    embed2.add_field(
        name="🏆 OSRS Hiscores",
        value="Look up any player's stats and rankings.\n🔗 https://secure.runescape.com/m=hiscore_oldschool/overall",
        inline=False
    )

    embed2.add_field(
        name="📈 GE Tracker",
        value="Track Grand Exchange prices, flipping margins, and item price history.\n🔗 https://www.ge-tracker.com",
        inline=False
    )

    embed2.add_field(
        name="👥 Wise Old Man",
        value="Track your gains, group progress, and compete with friends. Great for clan tracking!\n🔗 https://wiseoldman.net",
        inline=False
    )

    embed2.add_field(
        name="⚔️ DPS Calculator",
        value="Calculate your max hit, DPS, and optimal gear setups for any boss.\n🔗 https://dps.osrs.wiki",
        inline=False
    )

    embed2.add_field(
        name="💬 Official OSRS Discord",
        value="The official Old School RuneScape Discord server.\n🔗 https://discord.gg/osrs",
        inline=False
    )

    embed2.set_footer(text="Avera Clan • Happy scaping! 🍀")

    await channel.send(embed=embed1)
    await channel.send(embed=embed2)

    if ctx.channel.id != FAQ_CHANNEL_ID:
        await ctx.send(f"✅ FAQ panel posted in <#{FAQ_CHANNEL_ID}>!")


# ============================================================
#  VERIFY PANEL
# ============================================================

@bot.command(name="verifypanel")
@commands.has_permissions(manage_guild=True)
async def verify_panel(ctx):
    """Post the permanent verification panel. Admin only. Usage: !verifypanel"""
    channel = bot.get_channel(WELCOME_PANEL_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the verification channel.")
        return

    embed = discord.Embed(
        title="⚔️ Welcome to Avera!",
        description=(
            "You\'ve just taken the first step into something great.\n\n"
            "**Avera** is an Old School RuneScape clan built around community, "
            "progression, and good vibes. No elitism, no toxicity — just a group "
            "of players who love the game and want to experience it together.\n\n"
            "To get started and unlock the rest of the server, you\'ll need to "
            "verify your OSRS username below. 👇"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="✅ How to Verify",
        value=(
            "Type the following command in this channel:\n\n"
            "```!verify <your OSRS username>```\n"
            "**Example:** `!verify Zezima`\n\n"
            "The bot will check your username on the OSRS hiscores and link it to your Discord account. "
            "Your server nickname will automatically be updated to match your RSN."
        ),
        inline=False
    )

    embed.add_field(
        name="❓ What if I have multiple accounts?",
        value=(
            "Verify with your **main** account. You can always update your RSN later "
            "by running `!verify <new username>` again."
        ),
        inline=False
    )

    embed.add_field(
        name="❓ My username isn\'t being found?",
        value=(
            "Make sure your spelling is exact — RSNs are case-sensitive on the hiscores. "
            "If your account is brand new it may not appear yet. "
            "Open a ticket or ask a staff member for help."
        ),
        inline=False
    )

    embed.add_field(
        name="🌍 Once Verified",
        value=(
            "You\'ll gain access to the full server! From there:\n"
            f"🎭 Grab your roles in <#1459413079438917672>\n"
            f"📜 Read the rules in <#1479886542771323012>\n"
            f"❓ Check the FAQ in <#1479961124949721158>\n"
            f"🎯 Jump into bounties in <#1479471419577602199>\n\n"
            "We\'re glad you\'re here. Welcome home! ⚔️"
        ),
        inline=False
    )

    embed.set_footer(text="Avera Clan • Only !verify commands work in this channel • discord.gg/Avera")
    embed.timestamp = datetime.now()

    await channel.send(embed=embed)

    if ctx.channel.id != WELCOME_PANEL_CHANNEL_ID:
        await ctx.send(f"✅ Verification panel posted in <#{WELCOME_PANEL_CHANNEL_ID}>!")


# ============================================================
#  AUTO-SAVE TASK (every 5 minutes)
# ============================================================

@tasks.loop(minutes=5)
async def auto_save():
    save_data()


# ============================================================
#  AUTO-DASHBOARD REFRESH (every 30 minutes)
# ============================================================

@tasks.loop(minutes=30)
async def auto_dashboard_refresh():
    """Silently refresh the dashboard every 30 minutes."""
    for guild in bot.guilds:
        channel = bot.get_channel(DASHBOARD_CHANNEL_ID)
        if not channel:
            return
        try:
            embed = build_dashboard_embed(guild)
            if dashboard_message_id:
                try:
                    msg = await channel.fetch_message(dashboard_message_id)
                    await msg.edit(embed=embed)
                except discord.NotFound:
                    pass
        except Exception as e:
            print(f"Auto-dashboard refresh error: {e}")


# ============================================================
#  GIVEAWAY SYSTEM
# ============================================================

GIVEAWAY_CHANNEL_ID = 1459413281616822335

# active_giveaways_live: { message_id: { prize, host_id, end_time, channel_id } }
active_giveaways_live = {}


def parse_duration(duration_str):
    """Parse a duration string like 1h30m, 2h, 45m into seconds."""
    import re
    total = 0
    matches = re.findall(r"(\d+)([hmd])", duration_str.lower())
    for value, unit in matches:
        value = int(value)
        if unit == "h":
            total += value * 3600
        elif unit == "m":
            total += value * 60
        elif unit == "d":
            total += value * 86400
    return total


@bot.command(name="giveaway")
@commands.has_permissions(manage_guild=True)
async def start_giveaway(ctx, duration: str = None, *, prize: str = None):
    """Start a giveaway. Admin only.
    Usage: !giveaway <duration> <prize>
    Duration format: 1h, 30m, 1h30m, 2d
    Example: !giveaway 1h 10m GP"""
    if not duration or not prize:
        await ctx.send(
            "❌ Usage: `!giveaway <duration> <prize>`\n"
            "Duration examples: `1h`, `30m`, `2h30m`, `1d`\n"
            "Example: `!giveaway 1h 10m GP`"
        )
        return

    seconds = parse_duration(duration)
    if seconds == 0:
        await ctx.send("❌ Invalid duration. Use format like `1h`, `30m`, `2h30m`, `1d`.")
        return

    channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the giveaway channel.")
        return

    end_time = datetime.now().timestamp() + seconds
    end_dt = datetime.fromtimestamp(end_time)
    end_str = end_dt.strftime("%d %b %Y at %I:%M %p")

    embed = discord.Embed(
        title="🎉 GIVEAWAY!",
        description=(
            f"**Prize:** {prize}\n\n"
            f"React with 🎉 to enter!\n\n"
            f"**Ends:** {end_str}\n"
            f"**Hosted by:** {ctx.author.display_name}"
        ),
        color=discord.Color.gold()
    )
    embed.set_footer(text="Giveaway • React with 🎉 to enter")
    embed.timestamp = datetime.now()

    msg = await channel.send("@everyone", embed=embed)
    await msg.add_reaction("🎉")

    active_giveaways_live[msg.id] = {
        "prize": prize,
        "host_id": str(ctx.author.id),
        "host_name": ctx.author.display_name,
        "end_time": end_time,
        "channel_id": channel.id,
        "message_id": msg.id
    }

    if ctx.channel.id != GIVEAWAY_CHANNEL_ID:
        await ctx.send(f"✅ Giveaway started in <#{GIVEAWAY_CHANNEL_ID}>! Ends at **{end_str}**.")

    # Wait for duration then pick winner
    await asyncio.sleep(seconds)

    # Re-fetch message to get updated reactions
    try:
        msg = await channel.fetch_message(msg.id)
    except discord.NotFound:
        return

    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if not reaction:
        await channel.send(f"❌ Giveaway for **{prize}** ended with no entries!")
        active_giveaways_live.pop(msg.id, None)
        return

    # Collect entrants excluding the bot
    users = []
    async for user in reaction.users():
        if not user.bot:
            users.append(user)

    if not users:
        await channel.send(f"❌ Giveaway for **{prize}** ended with no valid entries!")
        active_giveaways_live.pop(msg.id, None)
        return

    winner = random.choice(users)

    # Edit original embed to show it ended
    ended_embed = discord.Embed(
        title="🎉 GIVEAWAY ENDED!",
        description=(
            f"**Prize:** {prize}\n\n"
            f"**Winner:** {winner.mention} 🏆\n\n"
            f"**Hosted by:** {ctx.author.display_name}"
        ),
        color=discord.Color.green()
    )
    ended_embed.set_footer(text="Giveaway ended")
    ended_embed.timestamp = datetime.now()

    try:
        await msg.edit(embed=ended_embed)
    except discord.NotFound:
        pass

    await channel.send(
        f"🎉 Congratulations {winner.mention}! You won **{prize}**! Please contact a staff member to claim your prize. ⚔️"
    )

    active_giveaways_live.pop(msg.id, None)


@bot.command(name="rerollgiveaway")
@commands.has_permissions(manage_guild=True)
async def reroll_giveaway(ctx, message_id: int = None):
    """Reroll a giveaway winner. Admin only.
    Usage: !rerollgiveaway <message_id>"""
    if not message_id:
        await ctx.send("❌ Usage: `!rerollgiveaway <message_id>`")
        return

    channel = bot.get_channel(GIVEAWAY_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the giveaway channel.")
        return

    try:
        msg = await channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("❌ Could not find that message. Make sure you're using the correct message ID.")
        return

    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    if not reaction:
        await ctx.send("❌ No reactions found on that message.")
        return

    users = []
    async for user in reaction.users():
        if not user.bot:
            users.append(user)

    if not users:
        await ctx.send("❌ No valid entries found.")
        return

    winner = random.choice(users)
    await ctx.send(
        f"🎉 Reroll! The new winner is {winner.mention}! Congratulations on winning! Please contact a staff member to claim your prize. ⚔️"
    )


# ============================================================
#  DINK SETUP PANEL
# ============================================================

DINK_CHANNEL_ID = 1479987507482464419


@bot.command(name="dinkpanel")
@commands.has_permissions(manage_guild=True)
async def dink_panel(ctx):
    """Post the permanent Dink setup guide. Admin only. Usage: !dinkpanel"""
    channel = bot.get_channel(DINK_CHANNEL_ID)
    if not channel:
        await ctx.send("❌ Could not find the Dink channel.")
        return

    embed1 = discord.Embed(
        title="🔔 How to Set Up Dink — Avera Clan",
        description=(
            "**Dink** is a free RuneLite plugin that automatically sends your in-game achievements "
            "directly to our Discord — drops, collection log slots, levels, quests, pets, PBs and more!\n\n"
            "We've already configured everything for you. Just follow the 3 steps below and you're done! ⚔️"
        ),
        color=discord.Color.gold()
    )

    embed1.add_field(
        name="Step 1️⃣ — Install Dink on RuneLite",
        value=(
            "1. Open **RuneLite**\n"
            "2. Click the 🧩 **Plugin Hub** icon on the right sidebar\n"
            "3. Search for **\"Dink\"** and click **Install**\n"
            "4. Once installed, open the **Dink plugin settings** by clicking the ⚙️ cog next to it"
        ),
        inline=False
    )

    embed1.add_field(
        name="Step 2️⃣ — Import Avera's Settings In-Game",
        value=(
            "We've pre-configured Dink with all the right webhooks and settings for Avera.\n\n"
            "1. Download the **📎 pinned export file** in this channel\n"
            "2. Open it and copy the entire contents\n"
            "3. Log into OSRS\n"
            "4. In the chat box, type `::dinkimport ` *(with a space after it)* then paste the string\n"
            "5. Hit **Enter** — Dink will import everything automatically!\n\n"
            "*This sets your minimum drop value to 500k, enables levels (60+), "
            "collection log, pets, quests, diaries, PKs and more.*"
        ),
        inline=False
    )

    embed1.add_field(
        name="Step 3️⃣ — Test It",
        value=(
            "Once imported, scroll to the top of Dink settings and click **\"Send Test Notification\"**.\n"
            "You should see a test message appear in the relevant Discord channel.\n\n"
            "If anything doesn't work, open a ticket in <#1479619326368551005> and staff will help!"
        ),
        inline=False
    )

    embed1.set_footer(text="Avera Clan • Dink Plugin — RuneLite Plugin Hub")

    # Embed 2 — the export string (split into chunks if needed — Discord field limit is 1024 chars)
    export_string = '{"killCountInterval":1000,"combatTaskEnabled":true,"gambleRareNotifMessage":"%USERNAME% has received rare loot at gamble count %COUNT%: \\n\\n%LOOT%","speedrunEnabled":false,"questEnabled":true,"deathNotifMessage":"%USERNAME% has died...","collectionNotifMessage":"%USERNAME% has added %ITEM% to their collection","levelNotifyVirtual":true,"questNotifMessage":"%USERNAME% has completed a quest: %QUEST%","killCountEnabled":false,"petWebhook":"https://discord.com/api/webhooks/1479985983763251442/dWiKCjf-N6sz_kyhQ1WuC84MRkdL90qCvYE9Q4I2jL2WHu_dM7TJyhiQFulxrFUMmwpn","slayerNotifMessage":"%USERNAME% has completed a slayer task: %TASK%, getting %POINTS% points and making that %TASKCOUNT% tasks completed","levelInterval":5,"notifyTrades":false,"speedrunMessage":"%USERNAME% has just finished a speedrun of %QUEST% with a time of %TIME% (their PB is %BEST%)","sendDiscordUser":true,"clueSendImage":true,"chatNotifyMessage":"%USERNAME% received a chat message:\\n\\n```\\n%MESSAGE%\\n```","slayerEnabled":false,"deathEnabled":false,"combatTaskUnlockMessage":"%USERNAME% has unlocked the rewards for the %COMPLETED% tier, by completing the combat task: %TASK%","deathMinValue":0,"deniedAccountTypes":[],"lootIncludeClueScrolls":true,"pkIncludeLocation":true,"lootIcons":false,"collectionWebhook":"https://discord.com/api/webhooks/1479985983763251442/dWiKCjf-N6sz_kyhQ1WuC84MRkdL90qCvYE9Q4I2jL2WHu_dM7TJyhiQFulxrFUMmwpn","lootEnabled":true,"petNotifMessage":"%USERNAME% %GAME_MESSAGE%","nameFilterMode":"DENY","lootRarityThreshold":0,"diaryWebhook":"https://discord.com/api/webhooks/1479986361695076543/0JoQ4Fyi4WLQNX7lKk_Zp4lioyCpPB2FcrrdNkv45-Nq-wpI02jnuH8vg7tMCKeuV8Nn","maxRetries":3,"embedFooterText":"Powered by goblin wisdom.","speedrunPBOnly":true,"includeLocation":true,"groupStorageNotifyMessage":"%USERNAME% has deposited:\\n%DEPOSITED%\\n\\n%USERNAME% has withdrawn:\\n%WITHDRAWN%","deathEmbedProtected":false,"useSlayerWidgetKc":true,"diarySendImage":true,"killCountWebhook":"https://discord.com/api/webhooks/1479986361695076543/0JoQ4Fyi4WLQNX7lKk_Zp4lioyCpPB2FcrrdNkv45-Nq-wpI02jnuH8vg7tMCKeuV8Nn","questSendImage":true,"killCountSendImage":true,"sendGroupIronClanName":true,"speedrunSendImage":true,"lootRarityValueIntersection":false,"levelEnabled":true,"speedrunWebhook":"https://discord.com/api/webhooks/1479986361695076543/0JoQ4Fyi4WLQNX7lKk_Zp4lioyCpPB2FcrrdNkv45-Nq-wpI02jnuH8vg7tMCKeuV8Nn","petEnabled":true,"chatMessageTypes":["GAME","COMMAND"],"tradeMinValue":0,"externalSendImage":"REQUESTED","slayerPointThreshold":0,"petSendImage":true,"groupStorageMinValue":0,"embedFooterIcon":"https://i.imgur.com/8ekC72P.jpeg","levelWebhook":"https://discord.com/api/webhooks/1479986361695076543/0JoQ4Fyi4WLQNX7lKk_Zp4lioyCpPB2FcrrdNkv45-Nq-wpI02jnuH8vg7tMCKeuV8Nn","killCountInitial":true,"combatTaskSendImage":true,"lootSendImage":true,"pkSendImage":true,"deathNotifPvpEnabled":true,"gambleInterval":100,"combatTaskMessage":"%USERNAME% has completed %TIER% combat task: %TASK%","notifyExternal":false,"collectionLogEnabled":true,"grandExchangeSendImage":true,"speedrunPBMessage":"%USERNAME% has just beat their personal best in a speedrun of %QUEST% with a time of %TIME%","collectionDenylist":"Dwarf remains\\n","deathSendImage":true,"diaryMinDifficulty":"EASY","lootImageMinValue":500000,"clueMinTier":"BEGINNER","pkNotifyMessage":"%USERNAME% has PK\\u0027d %TARGET%","baseRetryDelay":2000,"killCountPenanceQueen":true,"clueImageMinValue":500000,"lootIncludeGambles":false,"deathIgnoreSafe":true,"levelMinValue":60,"includeClientFrame":false,"levelIntervalOverride":0,"grandExchangeProgressSpacingMinutes":-1,"gambleSendImage":true,"pkEnabled":true,"imageWriteTimeout":30,"gambleNotifMessage":"%USERNAME% has reached %COUNT% high gambles","clueNotifMessage":"%USERNAME% has completed a %CLUE% clue, they have completed %COUNT%.\\nThey obtained:\\n\\n%LOOT%","lootSourceDenylist":"Einar\\n","gambleRareLoot":true,"clueEnabled":true,"lootWebhook":"https://discord.com/api/webhooks/1479985983763251442/dWiKCjf-N6sz_kyhQ1WuC84MRkdL90qCvYE9Q4I2jL2WHu_dM7TJyhiQFulxrFUMmwpn","clueMinValue":500000,"embedColor":"#FFF40098","levelSendImage":true,"chatPrivacy":"HIDE_SPLIT_PM","deathIgnoredRegions":"123, 456, 789","chatSendImage":true,"groupStorageIncludeClan":true,"levelMinScreenshotValue":60,"pkSkipSafe":true,"levelNotifyCombat":false,"sendClanName":true,"playerLookupService":"OSRS_HISCORE","threadNameTemplate":"[%TYPE%] %MESSAGE%","tradeNotifyMessage":"%USERNAME% traded with %COUNTERPARTY%","lootIncludePlayer":true,"combatTaskMinTier":"EASY","seasonalPolicy":"FORWARD_TO_LEAGUES","grandExchangeIncludeCancelled":false,"deathSafeExceptions":["FIGHT_CAVE","INFERNO"],"groupStorageSendImage":true,"levelNotifMessage":"%USERNAME% has levelled %SKILL%","killCountBestTimeMessage":"%USERNAME% has defeated %BOSS% with a new personal best time of %TIME% and a completion count of %COUNT%","pkWebhook":"https://discord.com/api/webhooks/1479986607795863724/5i-aKkZgkKA2njyDumXUuboMVrP2xe36nqQvSYGwicRjLofHTcWXxrvtYySB3exSnYNE","collectionSendImage":true,"screenshotScale":100,"notifyChat":false,"diaryEnabled":true,"lootNotifMessage":"%USERNAME% has looted: \\n\\n%LOOT%\\nFrom: %SOURCE%","chatPatterns":"You\\u0027ve unlocked an emote: *\\nYou\\u0027ve completed the * event*\\nYou have accepted * into *.\\nYou will be logged out in approximately 30 minutes.*\\nYou will be logged out in approximately 10 minutes.*\\n::TriggerDink\\n","deathNotifPvpMessage":"%USERNAME% has just been PKed by %PKER% for %VALUELOST% gp...","groupStorageEnabled":false,"combatTaskWebhook":"https://discord.com/api/webhooks/1479986361695076543/0JoQ4Fyi4WLQNX7lKk_Zp4lioyCpPB2FcrrdNkv45-Nq-wpI02jnuH8vg7tMCKeuV8Nn","diaryMessage":"%USERNAME% has completed the %DIFFICULTY% %AREA% Achievement Diary, for a total of %TOTAL% diaries completed","minLootValue":500000,"pkMinValue":1000000,"notifyGrandExchange":false,"grandExchangeNotifyMessage":"%USERNAME% %TYPE% %ITEM% on the GE","killCountPB":true,"discordRichEmbeds":true,"questWebhook":"https://discord.com/api/webhooks/1479986361695076543/0JoQ4Fyi4WLQNX7lKk_Zp4lioyCpPB2FcrrdNkv45-Nq-wpI02jnuH8vg7tMCKeuV8Nn","slayerSendImage":true,"tradeSendImage":true,"grandExchangeMinValue":100000,"xpInterval":5,"clueShowItems":false,"killCountMessage":"%USERNAME% has defeated %BOSS% with a completion count of %COUNT%","groupStorageIncludePrice":true,"pkSkipFriendly":false,"lootRedirectPlayerKill":true,"gambleEnabled":false}'


    # Split export string into chunks under 1900 chars each for plain messages
    chunk_size = 1900
    chunks = [export_string[i:i+chunk_size] for i in range(0, len(export_string), chunk_size)]

    # Embed 3 — what gets posted where
    embed3 = discord.Embed(
        title="📢 What Gets Posted & Where",
        description="Here's exactly what Dink will send to our Discord based on the imported settings:",
        color=discord.Color.dark_gold()
    )

    embed3.add_field(
        name="💰 Valuable Drops & Collection Log & Pets",
        value="Drops worth **500k+ gp**, new collection log slots, and pet drops.",
        inline=False
    )

    embed3.add_field(
        name="⬆️ Levels, Quests, Diaries & Combat Tasks",
        value="Level ups **(60+)**, quest completions, achievement diary completions, and combat task unlocks.",
        inline=False
    )

    embed3.add_field(
        name="⚔️ PKs",
        value="PK kills worth **1m+ gp**. Show off those big kills!",
        inline=False
    )

    embed3.add_field(
        name="🔕 Not Enabled by Default",
        value=(
            "Deaths, slayer tasks, kill counts, and trades are **off** in the imported settings to keep things clean. "
            "You can enable these yourself in your Dink settings after importing if you'd like them!"
        ),
        inline=False
    )

    embed3.set_footer(text="Avera Clan • Happy scaping! 🍀")

    await channel.send(embed=embed1)
    await channel.send(embed=embed3)

    if ctx.channel.id != DINK_CHANNEL_ID:
        await ctx.send(f"✅ Dink setup guide posted in <#{DINK_CHANNEL_ID}>!")

# ============================================================
#  RUN THE BOT
# ============================================================

TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERROR: DISCORD_TOKEN environment variable not set!")
    print("   Set your bot token in Railway/Replit environment variables.")
else:
    bot.run(TOKEN)
