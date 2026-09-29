"""Discord front-end for the RimDC RimWorld mod.

The mod answers every request with plain text: "sent" / "Request sent" when the
action went through, and a human-readable reason when it did not. Until recently
the bot discarded those replies and told every user "Request sent" no matter
what, so nothing was ever reported back.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path

import discord
import requests
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
server = os.getenv("SERVER", "http://localhost:9891/")

# Per-user pawn mappings. Anchored to this file so the bot behaves the same
# regardless of the directory it was launched from.
DATA_DIR = Path(__file__).parent / "characters"

# RimWorld identifies pawns by nickname, and the mod compares it verbatim, so the
# bot truncates to the same width the game displays.
MAX_NICK_LENGTH = 6

# The mod only speaks in these two acknowledgements. Anything else is a reason
# worth showing the user.
OK_RESPONSES = frozenset({"sent", "Request sent"})

REQUEST_TIMEOUT = 5

intents = discord.Intents.all()
intents.message_content = True


def load_guild() -> discord.Object:
    """Resolve the guild the slash commands are scoped to.

    Failing loudly at import beats a discord.Object(0), which silently registers
    the commands nowhere, or an opaque TypeError when the value is a placeholder.
    """
    raw = os.getenv("GUILD", "").strip()
    if not raw:
        raise SystemExit(
            "GUILD is not set. Copy .env.example to .env and fill in your server ID."
        )
    if not raw.isdigit():
        raise SystemExit("GUILD must be your numeric server ID, got {!r}".format(raw))
    return discord.Object(int(raw))


GUILD = load_guild()

# C1: shared with the mod, which reads the same variable from its own
# environment. The mod refuses to open its port when this is unset, so an empty
# value here means every command comes back "RimWorld did not answer".
RIMDC_TOKEN = os.getenv("RIMDC_TOKEN", "").strip()

if not RIMDC_TOKEN:
    raise SystemExit(
        "RIMDC_TOKEN is not set. It must match the RIMDC_TOKEN environment "
        "variable RimWorld sees; the mod keeps its port closed without it."
    )


def create_embed_message(text: str) -> discord.Embed:
    return discord.Embed(title="Log", description=text, color=discord.Color.blue())


def ensure_data_dir() -> Path:
    """Create the mapping dir if missing.

    It is per-deployment state and gitignored, so a fresh clone never has it.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR


def describe(response: str) -> str:
    """Turn the mod's raw reply into something worth putting in an embed."""
    text = response.strip()
    if not text or text in OK_RESPONSES:
        return "Done."
    return text


async def send_request(method: str, params: dict) -> str:
    """Ask the mod to do something and return whatever it said.

    The request runs off the event loop, and it never raises: a user command has
    to get an answer even when RimWorld is closed.
    """
    try:
        response = await asyncio.to_thread(
            requests.get,
            server + method,
            params=params,
            headers={"Authorization": "Bearer " + RIMDC_TOKEN},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return "Error: RimWorld did not answer ({}).".format(exc.__class__.__name__)
    return response.text


async def request_wrapper(
    method: str, params: dict | None = None, player_id: int = 0
) -> str:
    """Run an action against the pawn mapped to `player_id`."""
    mapping = DATA_DIR / str(player_id)
    if not mapping.is_file():
        return "You need to create a character first."

    # Built fresh every call: the old `params: dict = {}` was mutated in place.
    return await send_request(method, dict(params or {}, pawn=mapping.read_text()))


class MainBot(commands.Bot):
    async def setup_hook(self) -> None:
        self.tree.copy_global_to(guild=GUILD)
        await self.tree.sync(guild=GUILD)


bot = MainBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print("Connected as {}".format(bot.user))


@bot.tree.command(guild=GUILD, description="Create new character")
async def create_character(interaction: discord.Interaction, nickname: str):
    data_dir = ensure_data_dir()
    mapping = data_dir / str(interaction.user.id)

    nickname = nickname.strip()
    if not nickname:
        await interaction.response.send_message(
            embed=create_embed_message("Empty name?!?!?!")
        )
        return

    # Truncate before the duplicate check: the mod matches on the nickname, so
    # "Alexandria" and "Alexandr" both claim the same pawn.
    if len(nickname) > MAX_NICK_LENGTH:
        nickname = nickname[:MAX_NICK_LENGTH]

    if mapping.is_file():
        await interaction.response.send_message(
            embed=create_embed_message("You already have a character")
        )
        return

    registered = {path.read_text() for path in data_dir.iterdir() if path.is_file()}
    if nickname in registered:
        await interaction.response.send_message(
            embed=create_embed_message("Este nombre ya existe vro")
        )
        return

    reply = await send_request("create_character", {"pawn": nickname})
    if reply.strip() not in OK_RESPONSES:
        await interaction.response.send_message(
            embed=create_embed_message(describe(reply))
        )
        return

    # Persist only once RimWorld confirmed. Writing first left users holding a
    # mapping to a pawn that was never created, and no way to retry.
    mapping.write_text(nickname)
    await interaction.response.send_message(
        embed=create_embed_message("Created {}".format(nickname))
    )


@bot.tree.command(guild=GUILD, description="Clear all characters")
async def clear_characters(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(embed=create_embed_message("nouwu"))
        return

    removed = 0
    for path in ensure_data_dir().iterdir():
        if path.is_file():
            path.unlink()
            removed += 1

    await interaction.response.send_message(
        embed=create_embed_message("Removed {} mapping(s)".format(removed))
    )


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
    reply = await request_wrapper(
        "priority",
        {"data": priority.value, "complement": total_value},
        interaction.user.id,
    )
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Unequip current weapon")
async def unequip_weapon(interaction: discord.Interaction):
    reply = await request_wrapper("unequip_weapon", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="uwu")
async def strip(interaction: discord.Interaction):
    reply = await request_wrapper("strip", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


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
    reply = await request_wrapper(
        "threat_response", {"data": response.value}, interaction.user.id
    )
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Equip random available weapon")
async def equip_weapon(interaction: discord.Interaction):
    reply = await request_wrapper("equip_weapon", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Equip random available clothes")
async def equip_clothes(interaction: discord.Interaction):
    reply = await request_wrapper("equip_clothes", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Eat random available food")
async def eat(interaction: discord.Interaction):
    reply = await request_wrapper("eat", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Mimimi")
async def rest(interaction: discord.Interaction):
    reply = await request_wrapper("rest", {}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Kill")
async def kill(interaction: discord.Interaction, target: str):
    reply = await request_wrapper("kill", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="uwunya")
async def incapacite(interaction: discord.Interaction, target: str):
    reply = await request_wrapper("incapacite", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Rescue another pawn")
async def rescue(interaction: discord.Interaction, target: str):
    reply = await request_wrapper("rescue", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Shoot to another pawn")
async def shoot(interaction: discord.Interaction, target: str):
    reply = await request_wrapper("shoot", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


@bot.tree.command(guild=GUILD, description="Arrest another pawn")
async def arrest(interaction: discord.Interaction, target: str):
    reply = await request_wrapper("arrest", {"data": target}, interaction.user.id)
    await interaction.response.send_message(embed=create_embed_message(describe(reply)))


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


@bot.tree.command(guild=GUILD, description="Get character stats")
async def fastfetch(interaction: discord.Interaction):
    mapping = DATA_DIR / str(interaction.user.id)
    if not mapping.is_file():
        await interaction.response.send_message(
            embed=create_embed_message("You need to create character")
        )
        return

    pawn = mapping.read_text()

    # A dead pawn answers "Pawn dead or doesn't exists!!!" instead of JSON, so
    # parse defensively and show the reason rather than a decode traceback.
    stats = {}
    for field in ("skills", "needs", "health"):
        # One request per field. The old code called send_request a second time
        # inside the handler, so the error path -- the one a user actually hits
        # when the pawn is dead or the port is closed -- asked the mod twice for
        # the same data and showed a result from a second, possibly different,
        # call.
        reply = await send_request(field, {"pawn": pawn})

        try:
            stats[field] = json.loads(reply)
        except ValueError:
            await interaction.response.send_message(
                embed=create_embed_message(describe(reply))
            )
            return

    skills, needs, health = stats["skills"], stats["needs"], stats["health"]

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
