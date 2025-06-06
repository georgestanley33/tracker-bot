import discord
from discord.ext import commands
import re
import json
import os

# === CONFIG ===
TOKEN = os.environ["TOKEN"]
TICKET_CHANNEL_ID = 1380229712290385920
STATS_CHANNEL_ID = 1380285540804329695
PAYOUT_CHANNEL_ID = 1380299306568777812  # <-- Replace with your payout logs channel ID
STATS_FILE = "stats.json"
OWNER_ID = 866298421866397716  # <-- Replace with your Discord user ID

# === BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# === DATA HANDLING ===
if os.path.exists(STATS_FILE):
    with open(STATS_FILE, 'r') as f:
        data = json.load(f)
        user_id_count = data.get("user_id_count", 0)
        ticket_count = data.get("ticket_count", 0)
        current_group = data.get("current_group", [])
        last_message_id = data.get("last_message_id", None)
        stats_message_id = data.get("stats_message_id", None)
        welcome_message_ids = data.get("welcome_message_ids", [])
        original_message_id = data.get("original_message_id", None)
        payout_message_id = data.get("payout_message_id", None)
        total_gems_paid = data.get("total_gems_paid", 0)
else:
    user_id_count = 0
    ticket_count = 0
    current_group = []
    last_message_id = None
    stats_message_id = None
    welcome_message_ids = []
    original_message_id = None
    payout_message_id = None
    total_gems_paid = 0

def save_stats():
    with open(STATS_FILE, 'w') as f:
        json.dump({
            "user_id_count": user_id_count,
            "ticket_count": ticket_count,
            "current_group": current_group,
            "last_message_id": last_message_id,
            "stats_message_id": stats_message_id,
            "welcome_message_ids": welcome_message_ids,
            "original_message_id": original_message_id,
            "payout_message_id": payout_message_id,
            "total_gems_paid": total_gems_paid
        }, f)

# === BUTTONS ===
class ResetStatsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🗑️ Reset Stats", style=discord.ButtonStyle.danger, custom_id="reset_stats")

    async def callback(self, interaction: discord.Interaction):
        global user_id_count, current_group, last_message_id, ticket_count, welcome_message_ids
        user_id_count = 0
        ticket_count = 0
        current_group = []
        last_message_id = None
        welcome_message_ids = []
        await update_stats_panel()
        save_stats()
        await interaction.response.send_message("✅ Stats have been reset.", ephemeral=True)

class ResetPayoutButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🗑️ Reset Payouts", style=discord.ButtonStyle.danger, custom_id="reset_payout")

    async def callback(self, interaction: discord.Interaction):
        global total_gems_paid
        total_gems_paid = 0
        await update_payout_panel()
        save_stats()
        await interaction.response.send_message("✅ Payout total has been reset.", ephemeral=True)

class StatsPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ResetStatsButton())

class PayoutPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ResetPayoutButton())

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

# === MESSAGE BUILDERS ===
def build_welcome_message(ids):
    mention_line = ' '.join(f'<@{uid}>' for uid in ids)
    return f"""{mention_line}

I'm george and I'm going to be your Nexus manager. For the next 24 hours or so, this ticket is going to be open and it's gonna be your personal helpline. Feel free to ask any questions, queries, or anything else you may want to ask while you are new to the city!"""

def build_stats_message():
    gems = ticket_count * 10
    return f"""\U0001f4ca **Live Stats**
• Total IDs recorded: {user_id_count}
• Tickets handled: {ticket_count}
• Gems earned: {gems}"""

def build_payout_message():
    return f"\U0001f4b0 **Total Gems Paid Out:** {total_gems_paid}"

# === PANEL UPDATES ===
async def update_stats_panel():
    global stats_message_id
    channel = bot.get_channel(STATS_CHANNEL_ID)
    if not channel:
        return
    content = build_stats_message()
    try:
        if stats_message_id:
            msg = await channel.fetch_message(stats_message_id)
            await msg.edit(content=content, view=StatsPanelView())
        else:
            sent = await channel.send(content, view=StatsPanelView())
            stats_message_id = sent.id
            save_stats()
    except:
        sent = await channel.send(content, view=StatsPanelView())
        stats_message_id = sent.id
        save_stats()

async def update_payout_panel():
    global payout_message_id
    channel = bot.get_channel(PAYOUT_CHANNEL_ID)
    if not channel:
        return
    content = build_payout_message()
    try:
        if payout_message_id:
            msg = await channel.fetch_message(payout_message_id)
            await msg.edit(content=content, view=PayoutPanelView())
        else:
            sent = await channel.send(content, view=PayoutPanelView())
            payout_message_id = sent.id
            save_stats()
    except:
        sent = await channel.send(content, view=PayoutPanelView())
        payout_message_id = sent.id
        save_stats()

# === EVENTS ===
@bot.event
async def on_ready():
    global original_message_id
    print(f"✅ Bot is online as {bot.user}")
    bot.add_view(StatsPanelView())
    bot.add_view(TicketPanelView())
    bot.add_view(PayoutPanelView())

    ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
    if ticket_channel:
        if original_message_id:
            try:
                await ticket_channel.fetch_message(original_message_id)
            except:
                msg = await ticket_channel.send("📅 **Paste user IDs below:**", view=TicketPanelView())
                original_message_id = msg.id
                save_stats()
        else:
            msg = await ticket_channel.send("📅 **Paste user IDs below:**", view=TicketPanelView())
            original_message_id = msg.id
            save_stats()

    await update_stats_panel()
    await update_payout_panel()

@bot.event
async def on_message(message):
    global user_id_count, current_group, last_message_id, ticket_count, welcome_message_ids, total_gems_paid

    if message.author.bot:
        return

    if message.channel.id == PAYOUT_CHANNEL_ID and message.author.id == OWNER_ID:
        try:
            gems = int(message.content.strip())
            total_gems_paid += gems
            await update_payout_panel()
            save_stats()
            await message.delete()
        except ValueError:
            pass
        return

    if message.channel.id != TICKET_CHANNEL_ID:
        return

    content = message.content.strip().lower()

    if content == "new":
        if current_group:
            ticket_count += 1
            current_group = []
            last_message_id = None
            await update_stats_panel()
            save_stats()
        await message.delete()
        return

    if content == "clear" and message.author.id == OWNER_ID:
        channel = message.channel
        for msg_id in welcome_message_ids:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except:
                continue
        welcome_message_ids = []
        last_message_id = None
        save_stats()
        await message.delete()
        return

    ids = re.findall(r'\b\d{17,20}\b', message.content)
    if ids:
        user_id_count += len(ids)
        current_group.extend(ids)
        save_stats()

        channel = message.channel
        if len(current_group) <= 3:
            content = build_welcome_message(current_group)
            if last_message_id:
                try:
                    last_msg = await channel.fetch_message(last_message_id)
                    await last_msg.edit(content=content)
                except:
                    last_msg = await channel.send(content)
                    last_message_id = last_msg.id
                    welcome_message_ids.append(last_message_id)
            else:
                new_msg = await channel.send(content)
                last_message_id = new_msg.id
                welcome_message_ids.append(last_message_id)

        if len(current_group) == 3:
            ticket_count += 1
            current_group = []
            last_message_id = None
            save_stats()

        await update_stats_panel()
        await message.delete()
        return

    # Delete any unrelated messages
    if not (content == "new" or content == "clear"):
        if not re.match(r'^\d{17,20}$', content):
            await message.delete()

    await bot.process_commands(message)

bot.run(TOKEN)
