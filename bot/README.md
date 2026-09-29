# How To Use
1. In the .env file, set your Discord server ID for the "GUILD" parameter and your bot token for the "TOKEN" parameter. Copy `.env.example` to get started; `SERVER` only needs changing if you moved the mod off port 9891.

2. Set `RIMDC_TOKEN` to a long random string. It is the shared secret between
   this bot and the mod: the bot sends it as an `Authorization: Bearer` header
   and the mod keeps its port closed when the variable is missing on its side.
   The value in this `.env` only configures the bot -- RimWorld reads
   `RIMDC_TOKEN` from its own environment, so set it there too (see the root
   README) and make sure both are byte-for-byte identical.

3. Use the command `pip install -r requirements.txt` (you need to have Python installed) to install all the dependencies required to run the project, and then `python3 main.py` to execute it.

4. Once configured, users on Discord will need to use the "create_character" command in the character creation interface to create a character linked to them (the name used during creation defines the character they can control; if another character is renamed to match that original name, they will then control the character bearing that new name).

5. Use the "clear_characters" command after finishing a run to remove old characters from the internal files and create new ones. It is admin-only.

# Bot-only commands

Two slash commands never reach the RimWorld server:

- `/generate_random_race` picks a random name from a hardcoded list of RimWorld xenotypes and replies with it. It does not generate anything in the game.
- `/clear_characters` deletes the bot's own Discord-user-to-pawn-name mapping files. It is not an HTTP route and the mod knows nothing about it.

# Development

```sh
pip install -r requirements-dev.txt
python -m pytest
```

The suite pins the defects found in the audit under `docs/`: mutable default
arguments, mappings written before the request succeeded, truncation running
after the duplicate check, and a smoke test that calls every handler (a typo in
one of them once shipped unnoticed).

The C# mod has no equivalent suite -- it cannot be exercised without launching
RimWorld.
