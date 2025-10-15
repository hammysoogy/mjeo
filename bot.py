import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
from flask import Flask
from threading import Thread
import os

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

class PanelView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Check Stock", style=discord.ButtonStyle.primary, emoji="📦")
    async def check_stock(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="Stock Information",
            description="Stock information will be displayed here.",
            color=0xFFA500
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.primary, emoji="✅")
    async def get_role(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="Role Assignment",
            description="Your role has been assigned!",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} is ready")
    print(f"Synced commands")

@bot.tree.command(name="panel", description="Display the control panel")
async def panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Relay Autojoiner | Control Panel",
        description="This control panel is for the project: **Relay-AJ**\nIf you're a buyer, click on the buttons below to redeem your key, get the script or get your role",
        color=0xFFA500
    )
    embed.set_footer(text=f"Sent by {interaction.user.name} • {datetime.now().strftime('%m/%d/%Y %H:%M')}")
    
    await interaction.response.send_message(embed=embed, view=PanelView())

@bot.tree.command(name="buy", description="Buy an item")
async def buy(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Purchase",
        description="Thank you for your purchase!",
        color=0x00FF00
    )
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_TOKEN not found in environment variables")
        exit(1)
    bot.run(TOKEN)
