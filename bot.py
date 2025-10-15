import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
from flask import Flask
from threading import Thread
import os
import json
import uuid
import aiohttp

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is alive!"

def _run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

def keep_alive():
    t = Thread(target=_run_flask, daemon=True)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

KEYS_FILE = "keys.json"
REDEMPTIONS_FILE = "redemptions.json"
STOCK_FILE = "stock.json"

ADMIN_IDS = [1418891812713795706]
GAMEPASS_ID = 1462417519

def load_keys():
    if not os.path.exists(KEYS_FILE):
        return []
    with open(KEYS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)

def load_redemptions():
    if not os.path.exists(REDEMPTIONS_FILE):
        return {}
    with open(REDEMPTIONS_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_redemptions(redemptions):
    with open(REDEMPTIONS_FILE, "w") as f:
        json.dump(redemptions, f, indent=4)

def load_stock():
    if not os.path.exists(STOCK_FILE):
        return []
    with open(STOCK_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_stock(stock):
    with open(STOCK_FILE, "w") as f:
        json.dump(stock, f, indent=4)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def has_redeemed_key(user_id):
    redemptions = load_redemptions()
    return str(user_id) in redemptions

async def get_roblox_user_id(username: str):
    try:
        username = username.strip()
        async with aiohttp.ClientSession() as session:
            payload = {"usernames": [username], "excludeBannedUsers": False}
            async with session.post("https://users.roblox.com/v1/usernames/users", json=payload) as resp:
                print(f"Roblox API Status: {resp.status}")
                text = await resp.text()
                print(f"Roblox API Response: {text}")
                
                if resp.status == 200:
                    data = await resp.json()
                    if data and data.get("data") and len(data["data"]) > 0:
                        user_id = str(data["data"][0]["id"])
                        print(f"Found user ID: {user_id}")
                        return user_id
                return None
    except Exception as e:
        print(f"Error getting Roblox user ID: {e}")
        return None

async def check_user_owns_gamepass(user_id: str, gamepass_id: int):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://inventory.roblox.com/v1/users/{user_id}/items/GamePass/{gamepass_id}"
            async with session.get(url) as resp:
                print(f"Gamepass check status: {resp.status}")
                text = await resp.text()
                print(f"Gamepass check response: {text}")
                
                if resp.status == 200:
                    data = await resp.json()
                    has_gamepass = len(data.get('data', [])) > 0
                    print(f"User owns gamepass: {has_gamepass}")
                    return has_gamepass
                return False
    except Exception as e:
        print(f"Error checking gamepass: {e}")
        return False

class ValidatePurchaseView(View):
    def __init__(self, roblox_username: str):
        super().__init__(timeout=180)
        self.roblox_username = roblox_username
    
    @discord.ui.button(label="Validate Purchase", style=discord.ButtonStyle.success, emoji="✅")
    async def validate_purchase(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        
        stock = load_stock()
        if not stock:
            embed = discord.Embed(description="No stock available", color=0xFF0000)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        user_id = await get_roblox_user_id(self.roblox_username)
        if not user_id:
            embed = discord.Embed(description="Roblox user not found", color=0xFF0000)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        owns_gamepass = await check_user_owns_gamepass(user_id, GAMEPASS_ID)
        
        if owns_gamepass:
            account = stock.pop(0)
            save_stock(stock)
            
            try:
                dm_embed = discord.Embed(
                    title="Account Details",
                    color=0x00FF00
                )
                dm_embed.add_field(name="Username", value=f"`{account['username']}`", inline=False)
                dm_embed.add_field(name="Password", value=f"`{account['password']}`", inline=False)
                await interaction.user.send(embed=dm_embed)
                
                success_embed = discord.Embed(description="Check your DMs", color=0x00FF00)
                await interaction.followup.send(embed=success_embed, ephemeral=True)
            except discord.Forbidden:
                stock.insert(0, account)
                save_stock(stock)
                error_embed = discord.Embed(description="Enable DMs to receive account", color=0xFF0000)
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            embed = discord.Embed(description="You don't own the gamepass", color=0xFF0000)
            await interaction.followup.send(embed=embed, ephemeral=True)

class PanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Check Stock", style=discord.ButtonStyle.primary, emoji="📦")
    async def check_stock(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(description="Coming soon", color=0xFFA500)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.primary, emoji="✅")
    async def get_role(self, interaction: discord.Interaction, button: Button):
        if not has_redeemed_key(interaction.user.id):
            embed = discord.Embed(description="Redeem a key first", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        redemptions = load_redemptions()
        user_data = redemptions.get(str(interaction.user.id))
        if not user_data:
            embed = discord.Embed(description="No redemption found", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role_id = user_data.get("role_id")
        
        if not role_id:
            embed = discord.Embed(description="No role configured", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not interaction.guild:
            embed = discord.Embed(description="Use in a server", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role = interaction.guild.get_role(int(role_id))
        if not role:
            embed = discord.Embed(description="Role not found", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not isinstance(interaction.user, discord.Member):
            embed = discord.Embed(description="Can't assign role", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await interaction.user.add_roles(role)
            embed = discord.Embed(description=f"Given {role.mention}", color=0x00FF00)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(description="No permission", color=0xFF0000)
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is ready")
    print(f"Synced commands")

@bot.tree.command(name="panel", description="Display the control panel (Admin only)")
async def panel(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(description="Admin only", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Relay Autojoiner | Control Panel",
        description="Control panel for **Relay-AJ**\nBuyers: click buttons below to redeem key and get role",
        color=0xFFA500
    )
    embed.set_footer(text=f"{interaction.user.name} • {datetime.now().strftime('%m/%d/%Y %H:%M')}")
    
    await interaction.response.send_message(embed=embed, view=PanelView())

@bot.tree.command(name="genauthkey", description="Generate an authentication key (Admin only)")
@app_commands.describe(role_id="The role ID to assign when this key is redeemed")
async def genauthkey(interaction: discord.Interaction, role_id: str):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(description="Admin only", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    key = str(uuid.uuid4())
    keys = load_keys()
    keys.append({
        "key": key,
        "role_id": role_id,
        "generated_by": str(interaction.user.id),
        "generated_at": datetime.now().isoformat(),
        "redeemed": False
    })
    save_keys(keys)
    
    embed = discord.Embed(
        title="Key Generated",
        description=f"Key: `{key}`\nRole: `{role_id}`",
        color=0x00FF00
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="redeemkey", description="Redeem an authentication key")
@app_commands.describe(key="The authentication key to redeem")
async def redeemkey(interaction: discord.Interaction, key: str):
    if has_redeemed_key(interaction.user.id):
        embed = discord.Embed(description="Already redeemed a key", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    keys = load_keys()
    key_data = None
    key_index = -1
    
    for idx, k in enumerate(keys):
        if k["key"] == key and not k["redeemed"]:
            key_data = k
            key_index = idx
            break
    
    if not key_data or key_index == -1:
        embed = discord.Embed(description="Invalid or used key", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    keys[key_index]["redeemed"] = True
    keys[key_index]["redeemed_by"] = str(interaction.user.id)
    keys[key_index]["redeemed_at"] = datetime.now().isoformat()
    save_keys(keys)
    
    redemptions = load_redemptions()
    redemptions[str(interaction.user.id)] = {
        "key": key,
        "role_id": key_data["role_id"],
        "redeemed_at": datetime.now().isoformat()
    }
    save_redemptions(redemptions)
    
    embed = discord.Embed(description="Key redeemed! Use the Get Role button", color=0x00FF00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="buy", description="Buy an item")
@app_commands.describe(roblox_username="Your Roblox username")
async def buy(interaction: discord.Interaction, roblox_username: str):
    embed = discord.Embed(
        title="Purchase",
        description=f"Roblox: `{roblox_username}`\nGamepass: `{GAMEPASS_ID}`\n\nBuy the gamepass then click validate",
        color=0x0099FF
    )
    embed.add_field(name="Link", value=f"https://www.roblox.com/game-pass/{GAMEPASS_ID}", inline=False)
    
    await interaction.response.send_message(
        embed=embed, 
        view=ValidatePurchaseView(roblox_username),
        ephemeral=True
    )

@bot.tree.command(name="addstock", description="Add account to stock")
@app_commands.describe(username="Account username", password="Account password")
async def addstock(interaction: discord.Interaction, username: str, password: str):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(description="Admin only", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    stock = load_stock()
    stock.append({
        "username": username,
        "password": password,
        "added_at": datetime.now().isoformat()
    })
    save_stock(stock)
    
    embed = discord.Embed(description=f"Added account to stock\nTotal: {len(stock)}", color=0x00FF00)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stock", description="View stock")
async def stock_cmd(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(description="Admin only", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    stock = load_stock()
    
    if not stock:
        embed = discord.Embed(description="No stock", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(title=f"Stock ({len(stock)} accounts)", color=0x0099FF)
    
    for idx, account in enumerate(stock[:25], 1):
        embed.add_field(
            name=f"#{idx}",
            value=f"User: `{account['username']}`\nPass: `{account['password']}`",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="removestock", description="Remove account from stock")
@app_commands.describe(index="Account number to remove (1, 2, 3...)")
async def removestock(interaction: discord.Interaction, index: int):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(description="Admin only", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    stock = load_stock()
    
    if index < 1 or index > len(stock):
        embed = discord.Embed(description="Invalid index", color=0xFF0000)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    removed = stock.pop(index - 1)
    save_stock(stock)
    
    embed = discord.Embed(
        description=f"Removed: `{removed['username']}`\nRemaining: {len(stock)}",
        color=0x00FF00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables")
        exit(1)
    bot.run(TOKEN)
