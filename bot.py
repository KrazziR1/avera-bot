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

1. **Be Respectful** — Treat all clan members with respect. No harassment, bullying, or hate speech.
2. **No Begging** — Do not beg for items, GP, or boosts from other members.
3. **Activity** — Stay reasonably active. Inactivity of 30+ days without notice may result in removal.
4. **Clan Events** — Participation in clan events is encouraged! Show up and have fun.
5. **Represent the Clan** — Wear the clan cape when online. Represent Avera with pride.
6. **No Drama** — Keep personal drama out of clan chat. Sort disputes privately.
7. **Have Fun!** — This is a game. Enjoy it! 🎮

*For questions, contact a Clan Admin.*
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
    embed.add_field(name="🎯 Bounties", value=(
        f"`{PREFIX}bounties` — View all active bounties\n"
        f"`{PREFIX}claim <id>` — Claim a bounty (attach screenshot!)\n"
        f"`{PREFIX}bounty <target> <points> <desc>` — Create bounty *(Admin only)*\n"
        f"`{PREFIX}approveclaim <id>` — Approve a claim *(Admin only)*\n"
        f"`{PREFIX}denyclaim <id>` — Deny a claim *(Admin only)*\n"
        f"`{PREFIX}cancelbounty <id>` — Cancel a bounty *(Admin only)*"
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

    # Delete the member's message so the screenshot stays private
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

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

    # Remove this claim from pending list and close all other open claims for this bounty
    bounty["pending_claims"] = []
    bounty["active"] = False
    bounty["claimed_by"] = claimer.display_name
    # Close all review channels for this bounty
    all_channel_ids = claim_channels.pop(bounty_id, [])

    new_total = points_data[user_id]
    rank = get_rank(new_total)

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
