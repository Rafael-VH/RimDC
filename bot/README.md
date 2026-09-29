# How To Use
1. In the .env file, set your Discord server ID for the "GUILD" parameter and your bot token for the "TOKEN" parameter.

2. Use the command `pip install -r requirements.txt` (you need to have Python installed) to install all the dependencies required to run the project, and then `python3 main.py` to execute it.

2. Once configured, users on Discord will need to use the "create_character" command in the character creation interface to create a character linked to them (the name used during creation defines the character they can control; if another character is renamed to match that original name, they will then control the character bearing that new name).

3. Use the "clear_characters" command after finishing a run to remove old characters from the internal files and create new ones.
