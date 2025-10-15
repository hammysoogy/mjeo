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

def is_admin(user_id):
    return user_id in ADMIN_IDS

def has_redeemed_key(user_id):
    redemptions = load_redemptions()
    return str(user_id) in redemptions

async def get_roblox_user_id(username: str):
    async with aiohttp.ClientSession() as session:
        payload = {"usernames": [username], "excludeBannedUsers": False}
        async with session.post("https://users.roblox.com/v1/usernames/users", json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data and data.get("data") and len(data["data"]) > 0:
                    return str(data["data"][0]["id"])
            return None

async def check_user_owns_gamepass(user_id: str, gamepass_id: int):
    async with aiohttp.ClientSession() as session:
        url = f"https://inventory.roblox.com/v1/users/{user_id}/items/GamePass/{gamepass_id}"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return len(data.get('data', [])) > 0
            return False

class ValidatePurchaseView(View):
    def __init__(self, roblox_username: str):
        super().__init__(timeout=180)
        self.roblox_username = roblox_username
    
    @discord.ui.button(label="Validate Purchase", style=discord.ButtonStyle.success, emoji="✅")
    async def validate_purchase(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        
        user_id = await get_roblox_user_id(self.roblox_username)
        if not user_id:
            embed = discord.Embed(
                title="Error",
                description="Could not find Roblox user. Please check the username and try again.",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        owns_gamepass = await check_user_owns_gamepass(user_id, GAMEPASS_ID)
        
        if owns_gamepass:
            try:
                dm_embed = discord.Embed(
                    title="Purchase Validated!",
                    description="hi",
                    color=0x00FF00
                )
                await interaction.user.send(embed=dm_embed)
                
                success_embed = discord.Embed(
                    title="Success!",
                    description="Your purchase has been validated! Check your DMs.",
                    color=0x00FF00
                )
                await interaction.followup.send(embed=success_embed, ephemeral=True)
            except discord.Forbidden:
                error_embed = discord.Embed(
                    title="DM Failed",
                    description="I couldn't send you a DM. Please enable DMs from server members.",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="Purchase Failed",
                description="User does not own the gamepass!",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class PanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Check Stock", style=discord.ButtonStyle.primary, emoji="📦")
    async def check_stock(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="Stock Information",
            description="**COMING SOON**",
            color=0xFFA500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.primary, emoji="✅")
    async def get_role(self, interaction: discord.Interaction, button: Button):
        if not has_redeemed_key(interaction.user.id):
            embed = discord.Embed(
                title="Key Required",
                description="You must redeem a key first before getting the role!",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        redemptions = load_redemptions()
        user_data = redemptions.get(str(interaction.user.id))
        if not user_data:
            embed = discord.Embed(
                title="Error",
                description="Redemption data not found.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role_id = user_data.get("role_id")
        
        if not role_id:
            embed = discord.Embed(
                title="Error",
                description="No role configured for your key.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not interaction.guild:
            embed = discord.Embed(
                title="Error",
                description="This command must be used in a server.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        role = interaction.guild.get_role(int(role_id))
        if not role:
            embed = discord.Embed(
                title="Error",
                description="Role not found on this server.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not isinstance(interaction.user, discord.Member):
            embed = discord.Embed(
                title="Error",
                description="Cannot assign role in this context.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        try:
            await interaction.user.add_roles(role)
            embed = discord.Embed(
                title="Role Assigned",
                description=f"You have been given the {role.mention} role!",
                color=0x00FF00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = discord.Embed(
                title="Error",
                description="I don't have permission to assign roles.",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is ready")
    print(f"Synced commands")

@bot.tree.command(name="panel", description="Display the control panel (Admin only)")
async def panel(interaction: discord.Interaction):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="Permission Denied",
            description="Only admins can use this command.",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Relay Autojoiner | Control Panel",
        description="This control panel is for the project: **Relay-AJ**\nIf you're a buyer, click on the buttons below to redeem your key, get the script or get your role",
        color=0xFFA500
    )
    embed.set_footer(text=f"Sent by {interaction.user.name} • {datetime.now().strftime('%m/%d/%Y %H:%M')}")
    
    await interaction.response.send_message(embed=embed, view=PanelView())

@bot.tree.command(name="genauthkey", description="Generate an authentication key (Admin only)")
@app_commands.describe(role_id="The role ID to assign when this key is redeemed")
async def genauthkey(interaction: discord.Interaction, role_id: str):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="Permission Denied",
            description="Only admins can use this command.",
            color=0xFF0000
        )
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
        description=f"**Key:** `{key}`\n**Role ID:** `{role_id}`",
        color=0x00FF00,
        timestamp=datetime.now()
    )
    embed.set_footer(text="Keep this key safe and share it with your buyer")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="redeemkey", description="Redeem an authentication key")
@app_commands.describe(key="The authentication key to redeem")
async def redeemkey(interaction: discord.Interaction, key: str):
    if has_redeemed_key(interaction.user.id):
        embed = discord.Embed(
            title="Already Redeemed",
            description="You have already redeemed a key!",
            color=0xFF0000
        )
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
        embed = discord.Embed(
            title="Invalid Key",
            description="This key is invalid or has already been redeemed.",
            color=0xFF0000
        )
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
    
    embed = discord.Embed(
        title="Key Redeemed Successfully",
        description="Your key has been redeemed! You can now use the **Get Role** button in the control panel.",
        color=0x00FF00
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="buy", description="Buy an item")
@app_commands.describe(roblox_username="Your Roblox username")
async def buy(interaction: discord.Interaction, roblox_username: str):
    embed = discord.Embed(
        title="Purchase Gamepass",
        description=f"**Roblox Username:** {roblox_username}\n**Gamepass ID:** {GAMEPASS_ID}\n\nPlease purchase the gamepass first, then click the button below to validate your purchase.",
        color=0x0099FF
    )
    embed.add_field(name="Gamepass Link", value=f"https://www.roblox.com/game-pass/{GAMEPASS_ID}", inline=False)
    
    await interaction.response.send_message(
        embed=embed, 
        view=ValidatePurchaseView(roblox_username),
        ephemeral=True
    )

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN not found in environment variables")
        exit(1)
    bot.run(TOKEN)
