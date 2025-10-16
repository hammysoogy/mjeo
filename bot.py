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
STOCK_FILE = "account_stock.json"
VERIFIED_USERS_FILE = "verified_users.json"
CLAIMED_USERS_FILE = "claimed_users.json"
GAMEPASS_POOL_FILE = "gamepass_pool.json"

ADMIN_IDS = [1418891812713795706]
LOG_CHANNEL_ID = 1428374269179461704  # Replace with your actual channel ID

def load_keys():
    if not os.path.exists(KEYS_FILE):
        return []
    with open(KEYS_FILE, "r") as f:
        try:
            return json.load(f)
        except JSONDecodeError:
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
        except JSONDecodeError:
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
        except JSONDecodeError:
            return []

def save_stock(stock):
    with open(STOCK_FILE, "w") as f:
        json.dump(stock, f, indent=4)

def load_verified_users():
    if not os.path.exists(VERIFIED_USERS_FILE):
        return {}
    with open(VERIFIED_USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except JSONDecodeError:
            return {}

def save_verified_users(verified):
    with open(VERIFIED_USERS_FILE, "w") as f:
        json.dump(verified, f, indent=4)

def load_claimed_users():
    if not os.path.exists(CLAIMED_USERS_FILE):
        return {}
    with open(CLAIMED_USERS_FILE, "r") as f:
        try:
            return json.load(f)
        except JSONDecodeError:
            return {}

def save_claimed_users(claimed):
    with open(CLAIMED_USERS_FILE, "w") as f:
        json.dump(claimed, f, indent=4)

def load_gamepass_pool():
    if not os.path.exists(GAMEPASS_POOL_FILE):
        return {"active": [], "used": []}
    with open(GAMEPASS_POOL_FILE, "r") as f:
        try:
            return json.load(f)
        except JSONDecodeError:
            return {"active": [], "used": []}

def save_gamepass_pool(pool):
    with open(GAMEPASS_POOL_FILE, "w") as f:
        json.dump(pool, f, indent=4)

def is_admin(user_id):
    return user_id in ADMIN_IDS

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
    def __init__(self, roblox_username: str, gamepass_id: int):
        super().__init__(timeout=180)
        self.roblox_username = roblox_username
        self.gamepass_id = gamepass_id

    @discord.ui.button(label="Validate Purchase", style=discord.ButtonStyle.success, emoji="✅")
    async def validate_purchase(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)

        user_id = await get_roblox_user_id(self.roblox_username)
        if not user_id:
            embed = discord.Embed(
                title="Error",
                description="user doesnt exist",
                color=0xFF0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        owns_gamepass = await check_user_owns_gamepass(user_id, self.gamepass_id)

        if owns_gamepass:
            stock = load_stock()

            if not stock:
                no_stock_embed = discord.Embed(
                    title="No Stock Available",
                    description="no stock rn!",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=no_stock_embed, ephemeral=True)
                return

            account = stock.pop(0)
            save_stock(stock)

            # Mark user as claimed
            claimed_users = load_claimed_users()
            discord_user_id = str(interaction.user.id)
            claimed_users[discord_user_id] = {
                "roblox_username": self.roblox_username,
                "claimed_at": datetime.now().isoformat(),
                "gamepass_id": self.gamepass_id
            }
            save_claimed_users(claimed_users)

            # Mark gamepass as used
            gamepass_pool = load_gamepass_pool()
            if self.gamepass_id in gamepass_pool["active"]:
                gamepass_pool["active"].remove(self.gamepass_id)
                gamepass_pool["used"].append(self.gamepass_id)
                save_gamepass_pool(gamepass_pool)

                # Notify admin if no active gamepasses left
                if not gamepass_pool["active"]:
                    for admin_id in ADMIN_IDS:
                        try:
                            admin_user = await bot.fetch_user(admin_id)
                            notify_embed = discord.Embed(
                                title="⚠️ Restock Needed",
                                description="all gamepasses used! use /restock to add 3 new ones",
                                color=0xFF0000
                            )
                            await admin_user.send(embed=notify_embed)
                        except:
                            pass

            try:
                dm_embed = discord.Embed(
                    title="✅ got ur acc",
                    description="heres ur lvl 20 acc:",
                    color=0x00FF00
                )
                dm_embed.add_field(name="Username", value=f"`{account['username']}`", inline=False)
                dm_embed.add_field(name="Password", value=f"`{account['password']}`", inline=False)
                dm_embed.set_footer(text="keep this safe")
                await interaction.user.send(embed=dm_embed)

                success_embed = discord.Embed(
                    title="validated",
                    description="check dms for acc info",
                    color=0x00FF00
                )
                await interaction.followup.send(embed=success_embed, ephemeral=True)

                # Log to channel
                if LOG_CHANNEL_ID:
                    log_channel = bot.get_channel(LOG_CHANNEL_ID)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="📦 Account Distributed",
                            color=0x00FF00,
                            timestamp=datetime.now()
                        )
                        log_embed.add_field(name="User", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
                        log_embed.add_field(name="Username", value=f"`{account['username']}`", inline=True)
                        log_embed.add_field(name="Stock Remaining", value=f"{len(stock)} accounts", inline=True)
                        await log_channel.send(embed=log_embed)
            except discord.Forbidden:
                stock.insert(0, account)
                save_stock(stock)

                error_embed = discord.Embed(
                    title="cant dm u",
                    description="enable dms and try again",
                    color=0xFF0000
                )
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="failed",
                description="u didnt buy it",
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

@bot.tree.command(name="addstock", description="hi")
@app_commands.describe(username="Account username", password="Account password")
async def addstock(interaction: discord.Interaction, username: str, password: str):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="Permission Denied",
            description="Only admins can use this command.",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    stock = load_stock()
    stock.append({
        "username": username,
        "password": password,
        "added_by": str(interaction.user.id),
        "added_at": datetime.now().isoformat()
    })
    save_stock(stock)

    embed = discord.Embed(
        title="Stock Added",
        description=f"Account added to stock!\n**Current Stock:** {len(stock)} accounts",
        color=0x00FF00,
        timestamp=datetime.now()
    )
    embed.add_field(name="Username", value=f"`{username}`", inline=False)
    embed.set_footer(text="Stock updated successfully")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log to channel
    if LOG_CHANNEL_ID:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="➕ Stock Added",
                color=0x0099FF,
                timestamp=datetime.now()
            )
            log_embed.add_field(name="Added By", value=f"{interaction.user.mention}", inline=False)
            log_embed.add_field(name="Username", value=f"`{username}`", inline=True)
            log_embed.add_field(name="Total Stock", value=f"{len(stock)} accounts", inline=True)
            await log_channel.send(embed=log_embed)

@bot.tree.command(name="verify", description="Verify your Roblox username")
@app_commands.describe(roblox_username="Your Roblox username")
async def verify(interaction: discord.Interaction, roblox_username: str):
    verified_users = load_verified_users()
    user_id = str(interaction.user.id)

    verification_code = str(uuid.uuid4())[:8].upper()

    verified_users[user_id] = {
        "username": roblox_username,
        "code": verification_code,
        "verified": False
    }
    save_verified_users(verified_users)

    embed = discord.Embed(
        title="very u own the roblox acc",
        description=f"To verify you own the account `{roblox_username}` so i know your not scamming me, follow these steps:",
        color=0x0099FF
    )
    embed.add_field(
        name="Step 1",
        value=f"Go to your Roblox profile and add this code to your About/Description:\n```{verification_code}```",
        inline=False
    )
    embed.add_field(
        name="Step 2",
        value="After adding the code, use `/confirmverify` to complete verification.",
        inline=False
    )
    embed.set_footer(text="This code expires in 10 btw")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="confirmverify", description="Confirm your Roblox verification")
async def confirmverify(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    verified_users = load_verified_users()
    user_id = str(interaction.user.id)

    if user_id not in verified_users or verified_users[user_id].get("verified", False):
        return await interaction.followup.send(
            "You need to start verification with `/verify` first!",
            ephemeral=True
        )

    username = verified_users[user_id]["username"]
    code = verified_users[user_id]["code"]

    roblox_user_id = await get_roblox_user_id(username)
    if not roblox_user_id:
        return await interaction.followup.send(
            "Could not find that Roblox user. Try `/verify` again.",
            ephemeral=True
        )

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://users.roblox.com/v1/users/{roblox_user_id}"
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    description = data.get("description", "")

                    if code in description:
                        verified_users[user_id]["verified"] = True
                        save_verified_users(verified_users)

                        success_embed = discord.Embed(
                            title=Verified!!!11!11!!11!!!1!!1!",
                            description=f"Your Roblox account `{username}` is now verified!",
                            color=0x00FF00
                        )
                        await interaction.followup.send(embed=success_embed, ephemeral=True)
                    else:
                        fail_embed = discord.Embed(
                            title="❌",
                            description=f"Code not found in your profile description. Make sure you added:\n```{code}```",
                            color=0xFF0000
                        )
                        await interaction.followup.send(embed=fail_embed, ephemeral=True)
                else:
                    await interaction.followup.send("Error checking Roblox profile.", ephemeral=True)
    except Exception as e:
        print(f"Verification error: {e}")
        await interaction.followup.send("Error during verification.", ephemeral=True)

@bot.tree.command(name="buy", description="Buy an item")
async def buy(interaction: discord.Interaction):
    verified_users = load_verified_users()
    user_id = str(interaction.user.id)

    if user_id not in verified_users or not verified_users[user_id].get("verified", False):
        no_verify_embed = discord.Embed(
            title="Not verfieddddd",
            description="You need to verify your Roblox account first1!1!!!\nUse `/verify <your_roblox_username>` to get started",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=no_verify_embed, ephemeral=True)
        return

    roblox_username = verified_users[user_id]["username"]
    
    # Get the next available gamepass from the pool
    gamepass_pool = load_gamepass_pool()
    if not gamepass_pool["active"]:
        no_gamepass_embed = discord.Embed(
            title="gone",
            description="out of stock",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=no_gamepass_embed, ephemeral=True)
        return

    current_gamepass_id = gamepass_pool["active"][0]

    embed = discord.Embed(
        title="purchase",
        description=f"**Roblox Username:** {roblox_username}\n**Gamepass ID:** {current_gamepass_id}\n\nbuy this for lvl 20 rank",
        color=0x0099FF
    )
    embed.add_field(name="Gamepass Link", value=f"https://www.roblox.com/game-pass/{current_gamepass_id}/hi", inline=False)

    await interaction.response.send_message(
        embed=embed, 
        view=ValidatePurchaseView(roblox_username, current_gamepass_id),
        ephemeral=True
    )

@bot.tree.command(name="restock", description="Restock gamepasses")
@app_commands.describe(gp1="First gamepass ID", gp2="Second gamepass ID", gp3="Third gamepass ID")
async def restock(interaction: discord.Interaction, gp1: int, gp2: int, gp3: int):
    if not is_admin(interaction.user.id):
        embed = discord.Embed(
            title="Permission Denied",
            description="Only admins can use this command.",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    gamepass_pool = load_gamepass_pool()
    
    # Add new gamepasses to the active pool
    new_gamepasses = [gp1, gp2, gp3]
    for gp_id in new_gamepasses:
        if gp_id not in gamepass_pool["active"] and gp_id not in gamepass_pool["used"]:
            gamepass_pool["active"].append(gp_id)
    
    save_gamepass_pool(gamepass_pool)

    embed = discord.Embed(
        title="Gamepasses Restocked",
        description=f"Successfully added {len(new_gamepasses)} new gamepasses to the pool.",
        color=0x00FF00,
        timestamp=datetime.now()
    )
    embed.add_field(name="New Active Gamepasses", value=", ".join(map(str, gamepass_pool["active"])), inline=False)
    embed.set_footer(text="Gamepass pool updated")

    await interaction.response.send_message(embed=embed, ephemeral=True)

    # Log to channel
    if LOG_CHANNEL_ID:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="Gamepasses Restocked",
                color=0x0099FF,
                timestamp=datetime.now()
            )
            log_embed.add_field(name="Restocked By", value=f"{interaction.user.mention}", inline=False)
            log_embed.add_field(name="New Gamepasses Added", value=", ".join(map(str, new_gamepasses)), inline=True)
            log_embed.add_field(name="Total Active Gamepasses", value=f"{len(gamepass_pool['active'])}", inline=True)
            await log_channel.send(embed=log_embed)


if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: saibow")
        exit(1)
    bot.run(TOKEN)
