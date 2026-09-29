"""Pytest bootstrap.

main.py calls load_dotenv() at import time, so without this the suite would
collect or fail depending on whatever sits in the developer's local bot/.env.
That file holds real secrets, and the placeholder copy crashes the import
(discord.Object() rejects a non-numeric id), so pin the environment first.

load_dotenv() does not override variables that already exist, so these win.
"""

import os

os.environ["GUILD"] = "0"
os.environ["TOKEN"] = ""
os.environ["RIMDC_TOKEN"] = "test-token"
