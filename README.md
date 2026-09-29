# RimDC

Drive a RimWorld colony from Discord. A RimWorld mod exposes your colonists over
HTTP; a Discord bot turns slash commands into requests against it.

The mod is called **RimServer** in RimWorld's mod list (that is the name in
`About.xml`). The repository is **RimDC**. They are the same thing.

```
   Discord                    HTTP                      RimWorld
  /fastfetch  ──┐                                    ┌─ selectedPawn
  /eat         ─┼──►  bot (Python)  ──── GET ────►  mod (C#) ──┤ workSettings
  /priority    ─┘    discord.py      localhost:9891  HttpListener  └─ actionQueue
                        │                                  │            │
                    .env token                    RIMDC_TOKEN env     game thread
                                                          │         (Update)
                                                    Authorization:       │
                                                        Bearer ────┘
```

Two processes, one shared secret, `localhost` only. The mod never binds anything
but the loopback interface.

## Requirements

| | |
|---|---|
| RimWorld | 1.6 |
| **Biotech** | **required** — see below |
| .NET SDK | any version that can target `netstandard2.1` |
| Python | 3 |
| Discord | a bot application and its token, invited to your server |

**Biotech is not optional.** `/create_character` calls
`ModsConfig.BiotechActive` and picks a `XenotypeDef`; without Biotech it logs
`Biotech is not active...` and returns nothing. It is the first thing every
user does, so install it before blaming the mod. `About.xml` does not declare
the dependency, so RimWorld will not warn you.

Anomaly is optional but recommended. Two of the accepted work types,
`darkstudy` and `plantcutting`, are Anomaly work types, so they are only
meaningful with that DLC enabled.

## Install the mod

### 1. Build

The mod compiles against RimWorld's own assemblies, so the build needs a path to
them. The default points at a Linux Steam install:

```sh
dotnet build -c Release
```

Anywhere else, pass your own path. The data folder is named after the game
executable, which differs per platform:

```sh
# Windows
dotnet build -c Release /p:RimWorldManagedDir="C:\Program Files (x86)\Steam\steamapps\common\RimWorld\RimWorldWin64_Data\Managed"

# macOS
dotnet build -c Release /p:RimWorldManagedDir="~/Library/Application Support/Steam/steamapps/common/RimWorld/RimWorldMac_Data/Managed"
```

If the path is wrong the build fails with `RimWorld assemblies not found at ...`
rather than a wall of missing-type errors. That check is deliberate.

### 2. Install

Copy everything from `bin/Release/` into your RimWorld `Assemblies/` folder,
next to `Assembly-CSharp.dll`. Then enable **RimServer** in the mod list.

### 3. Set the shared token

This is the step people get wrong, and getting it wrong looks like a broken
mod. Both processes must see the **identical string**.

The mod reads `RIMDC_TOKEN` from its own environment, and if that variable is
missing or blank it **does not open the port at all** — it fails closed rather
than serving an unauthenticated port. You will find this in the log:

```
[ Server Mod ] RIMDC_TOKEN is not set, so the server was not started.
```

Set it as a user environment variable:

```sh
# Windows (PowerShell or cmd)
setx RIMDC_TOKEN "pick-something-long-and-random"

# Linux / macOS, add to ~/.bashrc, ~/.zshrc, etc.
export RIMDC_TOKEN="pick-something-long-and-random"
```

> **Restart RimWorld afterwards.** `setx` writes to the registry for *future*
> processes only. A RimWorld instance that was already running will not see the
> new value, and you will get `401 Unauthorized` against code that is working
> perfectly.

The bot gets the same value from its own `.env` file — see
[bot/README.md](bot/README.md). The `.env` value configures the bot only; the
mod never reads it.

## Set up the bot

```sh
cd bot
cp .env.example .env      # then fill in TOKEN, GUILD, and RIMDC_TOKEN
pip install -r requirements.txt
python main.py
```

See [bot/README.md](bot/README.md) for the Discord side: creating the
application, enabling Developer Mode to get your server ID, and the
`/create_character` → `/clear_characters` character lifecycle.

## HTTP API

The server listens on `http://localhost:9891/`. Every request needs the shared
token:

```sh
curl -H "Authorization: Bearer $RIMDC_TOKEN" \
     "http://localhost:9891/eat?pawn=Ana"
```

Without the header you get `401 Unauthorized`. With a wrong one:

```
Unauthorized: RIMDC_TOKEN does not match.
```

All requests are `GET`. Actions are named in the path; extra arguments go in
query parameters.

| Parameter | Required | Meaning |
|---|---|---|
| `pawn` | yes | Nickname of the colonist to act on. Matched case-insensitively. |
| `data` | depends | The argument for routes that take one. See below. |
| `complement` | `/priority` only | The priority number to set. |

If the pawn is not found, is dead, or is not a free colonist, the mod replies
`Pawn dead or doesn't exists!!!` and does nothing.

### Actions

| Route | `data` | Does |
|---|---|---|
| `/priority` | work type | Sets that work type's priority from `complement` |
| `/threat_response` | `attack`, `flee`, `ignore` | Sets how the colonist reacts to threats |
| `/eat` | — | Eats random available food |
| `/rest` | — | Rests |
| `/equip_weapon` | — | Equips a random available weapon |
| `/unequip_weapon` | — | Unequips the current weapon |
| `/equip_clothes` | — | Equips random available clothes |
| `/strip` | — | Removes apparel |
| `/kill` | target name | Kills another pawn |
| `/incapacite` | target name | Incapacitates another pawn |
| `/rescue` | target name | Rescues a downed pawn |
| `/shoot` | target name | Shoots another pawn |
| `/arrest` | target name | Arrests another pawn |
| `/equip_ranged_weapon` | — | Equips a random ranged weapon |
| `/equip_melee_weapon` | — | Equips a random melee weapon |

Valid `data` values for `/priority`:

```
cleaning  childcare  construction  crafting  darkstudy  doctor
firefighter  fishing  growing  handling  hauling  hunting  mining
plantcutting  research  smithing  warden
```

`/priority` needs **both** parameters. With a missing or non-numeric
`complement` the parse fails and the call is silently ignored — no error, no
log line, nothing happens:

```sh
# works
curl -H "Authorization: Bearer $RIMDC_TOKEN" \
     "http://localhost:9891/priority?pawn=Ana&data=mining&complement=1"

# silently does nothing: no complement
curl -H "Authorization: Bearer $RIMDC_TOKEN" \
     "http://localhost:9891/priority?pawn=Ana&data=mining"
```

### Reading data

These four return JSON. The other routes answer `Request sent` (or `sent` for
`/create_character`) once the action is queued — a receipt, not a result.

| Route | Returns |
|---|---|
| `/getskills` | the ten skill levels |
| `/getneeds` | the need levels |
| `/gethealth` | injuries and parts |
| `/getequipment` | what is equipped |

JSON is emitted culture-invariant, so a decimal comma on your machine does not
produce invalid JSON.

### Creating a character

`/create_character?pawn=NAME` only works on the character creation screen. If
that screen is not open yet, the mod queues the name and applies it when you
reach it. Requires Biotech.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Port never opens, log says `RIMDC_TOKEN is not set` | The variable is not visible to the RimWorld process. Set it, then **fully restart** the game. |
| `401 Unauthorized` on every call | The bot's `RIMDC_TOKEN` and the mod's differ, or RimWorld was running when you set it. Compare them byte for byte. |
| `Biotech is not active...` | Install Biotech. `/create_character` cannot work without it. |
| `Pawn dead or doesn't exists!!!` | The nickname does not match a living free colonist on the current map. Nicknames, not full names. |
| `/priority` does nothing | Missing or non-numeric `complement`. See above. |
| A request returns `Request sent` and nothing happens | The route name is misspelled, or not a real route. The switch has no `default:` case, so an unknown route is a silent no-op that still looks like success. Check the spelling against the tables above. |
| Commands visible in Discord but nothing happens in game | The mod is not running, or the token mismatches. Check the RimWorld log. |

## Development

```sh
# bot — 25 tests, no game required
cd bot
pip install -r requirements-dev.txt
python -m pytest

# mod
dotnet build -c Release /p:RimWorldManagedDir="<path to Managed>"
```

The bot suite reproduces the defects found in the audit and pins the
`Authorization` header end to end against a real fixture HTTP server. The mod
has no automated suite: its logic touches the game state directly and cannot be
exercised without launching RimWorld.

## Status

The mod and the bot have been hardened and covered by tests, but **none of it
has been observed running inside RimWorld.** The test suite proves the bot's
request contract, not the game's behaviour.

Known open items are tracked in [docs/05-implementacion.md](docs/05-implementacion.md):

- The five pawn-targeting routes (`/kill`, `/incapacite`, `/rescue`, `/shoot`,
  `/arrest`) only ever find colonists, because the lookup filters on
  `FreeColonists`. Deferred until the mod can be run.
- The bot's work-type choices do not yet expose `darkstudy` and `plantcutting`.
- A runtime verification checklist, including the token deployment step, is in
  [docs/04-plan-de-arreglo.md](docs/04-plan-de-arreglo.md).

## Documentation

| Document | What it covers |
|---|---|
| [docs/01-que-es-este-proyecto.md](docs/01-que-es-este-proyecto.md) | What the project does, end to end |
| [docs/02-arquitectura.md](docs/02-arquitectura.md) | How it is split, what talks to what, and why |
| [docs/03-auditoria.md](docs/03-auditoria.md) | Code audit: findings, severity, file and line |
| [docs/04-plan-de-arreglo.md](docs/04-plan-de-arreglo.md) | The remediation plan and the runtime checklist |
| [docs/05-implementacion.md](docs/05-implementacion.md) | What was actually implemented, and what remains |
| [bot/README.md](bot/README.md) | Discord bot setup and commands |

The documentation is in Spanish; this file and `bot/README.md` are in English.
