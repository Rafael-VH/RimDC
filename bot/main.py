import os
import threading
from pathlib import Path

import discord
import random
import requests
import json
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
server = "http://localhost:9891/"

# Per-user pawn mappings. Anchored to this file so the bot behaves the same
# regardless of the directory it was launched from.
DATA_DIR = Path(__file__).parent / "characters"

intents = discord.Intents.all()
intents.message_content = True


def create_embed_message(text: str) -> discord.Embed:
    return discord.Embed(title="Log", description=text, color=discord.Color.blue())


def send_request(method: str, params: dict) -> None:
    requests.get(server + method, params=params)


def request_wrapper(method: str, params: dict = {}, player_id: int = 0) -> None:
    f = os.path.isfile(DATA_DIR / str(player_id))

    if not f:
        return

    with open(DATA_DIR / str(player_id), "r") as f:
        content = f.read()

    params["pawn"] = content
    print(params)

    thread = threading.Thread(target=send_request, args=(method, params))
    thread.start()


GUILD = discord.Object(os.getenv("GUILD") or 0)


class MainBot(commands.Bot):
    async def setup_hook(self) -> None:
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)


bot = MainBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("Connected as {}".format(bot.user))


@app_commands.choices(
    priority=[
        app_commands.Choice(name="Cleaning", value="cleaning"),
        app_commands.Choice(name="Hauling", value="hauling"),
        app_commands.Choice(name="Childcare", value="childcare"),
        app_commands.Choice(name="Construction", value="construction"),
        app_commands.Choice(name="Crafting", value="crafting"),
        app_commands.Choice(name="Dark Study", value="darkstudy"),
        app_commands.Choice(name="Doctor", value="doctor"),
        app_commands.Choice(name="Firefighter", value="firefighter"),
        app_commands.Choice(name="Fishing", value="fishing"),
        app_commands.Choice(name="Growing", value="growing"),
        app_commands.Choice(name="Handling", value="handling"),
        app_commands.Choice(name="Mining", value="mining"),
        app_commands.Choice(name="Plants cutting", value="plantcutting"),
        app_commands.Choice(name="Research", value="research"),
        app_commands.Choice(name="Smithing", value="smithing"),
        app_commands.Choice(name="Warden", value="warden"),
        app_commands.Choice(name="Hunting", value="hunting"),
    ],
)
@bot.tree.command(guild=GUILD, description="Set work priority")
async def set_priority(
    interaction: discord.Interaction, priority: app_commands.Choice[str], value: int
):
    total_value = max(min(value, 3), 1)
    request_wrapper(
        "priority",
        {"data": priority.value, "complement": total_value},
        interaction.user.id,
    )

    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Unequip current weapon")
async def unequip_weapon(interaction: discord.Interaction):
    request_wrapper("unequip_weapon", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="uwu")
async def strip(interaction: discord.Interaction):
    request_wrapper("strip", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@app_commands.choices(
    response=[
        app_commands.Choice(name="Attack", value="attack"),
        app_commands.Choice(name="Flee", value="flee"),
        app_commands.Choice(name="Ignore", value="ignore"),
    ]
)
@bot.tree.command(guild=GUILD, description="Change character response to threats")
async def threat_response(
    interaction: discord.Interaction, response: app_commands.Choice[str]
):
    request_wrapper("threat_response", {"data": response.value}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Equip random available weapon")
async def equip_weapon(interaction: discord.Interaction):
    request_wrapper("equip_weapon", {}, interaction.user.id)
    await interaction.resppobresonse.send_message(
        embed=create_embed_message("Request sent")
    )


@bot.tree.command(guild=GUILD, description="Equip random available clothes")
async def equip_clothes(interaction: discord.Interaction):
    request_wrapper("equip_clothes", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Eat random available food")
async def eat(interaction: discord.Interaction):
    request_wrapper("eat", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Mimimi")
async def rest(interaction: discord.Interaction):
    request_wrapper("rest", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Kill")
async def kill(interaction: discord.Interaction, target: str):
    request_wrapper("kill", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="uwunya")
async def incapacite(interaction: discord.Interaction, target: str):
    request_wrapper("incapacite", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Rescue another pawn")
async def rescue(interaction: discord.Interaction, target: str):
    request_wrapper("rescue", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Shoot to another pawn")
async def shoot(interaction: discord.Interaction, target: str):
    request_wrapper("shoot", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Arrest another pawn")
async def arrest(interaction: discord.Interaction, target: str):
    request_wrapper("arrest", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message("Request sent"))


@bot.tree.command(guild=GUILD, description="Generate random race")
async def generate_random_race(interaction: discord.Interaction):
    await interaction.response.send_message(
        embed=create_embed_message(
            random.choice(
                [
                    "Baseliner",
                    "Dirtmole",
                    "Genie",
                    "Hussar",
                    "Neanderthal",
                    "Pigskin",
                    "Impid",
                    "Waster",
                    "Yttakin",
                    "Highmate",
                    "Starjack",
                    "Insector",
                    "Guaranlenkin",
                    "Animakin",
                    "Poluxkin",
                    "Boarskin",
                    "Wolfman",
                    "Lycan",
                    "Archon",
                    "Fungoid",
                    "Lowmate",
                    "Uhlan",
                    "Mycomorph",
                    "Ocularkin",
                    "Fleetkind",
                    "Helixan",
                    "Animusen",
                    "Lapis",
                    "Wretch",
                    "Taukai",
                    "Hiveling",
                    "Mind devourer",
                    "Efreet",
                    "Drakonori",
                    "Nereid",
                    "Forsaken",
                    "Ratkin",
                    "Cinder",
                    "Malachai",
                    "MoeLotls",
                ]
            )
        )
    )


@bot.tree.command(guild=GUILD, description="Create new character")
async def create_character(interaction: discord.Interaction, nickname: str):
    registered_nicknames = []

    for x in os.listdir(DATA_DIR):
        if os.path.isfile(DATA_DIR / x):
            with open(DATA_DIR / x, "r") as f:
                registered_nicknames.append(f.read())

    if nickname in registered_nicknames:
        await interaction.response.send_message(
            embed=create_embed_message("Este nombre ya existe vro")
        )
        return

    if nickname == "":
        await interaction.response.send_message(
            embed=create_embed_message("Empty name?!?!?!")
        )
        return

    if len(nickname) > 6:
        nickname = nickname[:6]

    print("Nickname: " + nickname)

    if not os.path.isfile(DATA_DIR / str(interaction.user.id)):
        with open(DATA_DIR / str(interaction.user.id), "w+") as f:
            f.write(nickname)

        request_wrapper("create_character", {}, interaction.user.id)
        await interaction.response.send_message(
            embed=create_embed_message("Request sent")
        )
    else:
        await interaction.response.send_message(
            embed=create_embed_message("Request sent")
        )


@bot.tree.command(guild=GUILD, description="Clear all characters")
async def clear_characters(interaction: discord.Interaction):
    if interaction.user.guild_permissions.administrator:
        for x in os.listdir(DATA_DIR):
            path = str(DATA_DIR / x)

            if os.path.isfile(path):
                os.remove(path)

        await interaction.response.send_message(embed=create_embed_message("ok"))
    else:
        await interaction.response.send_message(embed=create_embed_message("nouwu"))


@bot.tree.command(guild=GUILD, description="Get character stats")
async def fastfetch(interaction: discord.Interaction):
    character = os.path.isfile(DATA_DIR / str(interaction.user.id))

    if not character:
        await interaction.response.send_message(
            embed=create_embed_message("You need to create character")
        )
        return

    with open(DATA_DIR / str(interaction.user.id), "r") as f:
        pawn = f.read()

    skills = requests.get(url=server + "getskills", params={"pawn": pawn}).json()
    needs = requests.get(url=server + "getneeds", params={"pawn": pawn}).json()
    health = requests.get(url=server + "gethealth", params={"pawn": pawn}).json()

    embed = discord.Embed(
        title="Fastfetch",
        description="Character name: {}".format(pawn),
        color=discord.Color.purple(),
    )

    embed.add_field(
        name="Skills",
        value="**Shooting:** {}\n**Melee:** {}\n**Construction:** {}\n**Mining:** {}\n**Cooking:** {}\n**Plants:** {}\n**Animals:** {}\n**Crafting:** {}\n**Artistic:** {}\n**Medical:** {}\n**Social:** {}\n**Intellectual:** {}\n".format(
            skills["shooting"],
            skills["melee"],
            skills["construction"],
            skills["mining"],
            skills["cooking"],
            skills["plants"],
            skills["animals"],
            skills["crafting"],
            skills["artistic"],
            skills["medical"],
            skills["social"],
            skills["intellectual"],
        ),
        inline=True,
    )

    embed.add_field(
        name="Needs",
        value="Mood: {}\nRest: {}\nFood: {}".format(
            float(needs["mood"]) * 100,
            float(needs["rest"]) * 100,
            float(needs["food"]) * 100,
        ),
        inline=True,
    )

    embed.add_field(name="Health", value="{}".format(health), inline=True)

    await interaction.response.send_message(embed=embed)


if __name__ == "__main__":
    bot.run(TOKEN)  # type: ignore
