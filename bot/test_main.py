"""Tests for the RimDC Discord bot.

Every test here pins one audited defect from docs/03-auditoria.md. They were
written before the fixes, so a red run is the bug report. The C# mod has no
equivalent suite: it cannot be tested without launching RimWorld.
"""

import asyncio
import http.server
import threading

import pytest

import main


def run(coro):
    """Drive a command handler to completion."""
    return asyncio.run(coro)


def handler(name):
    """Unwrap the app_commands.Command that @bot.tree.command returns."""
    return getattr(main, name).callback


class FakePermissions:
    administrator = True


class FakeUser:
    def __init__(self, user_id):
        self.id = user_id
        self.guild_permissions = FakePermissions()


class FakeResponse:
    def __init__(self, owner):
        self._owner = owner

    async def send_message(self, embed=None, **kwargs):
        self._owner.replies.append(embed)


class FakeInteraction:
    """Stands in for discord.Interaction so handlers can be called directly."""

    def __init__(self, user_id):
        self.user = FakeUser(user_id)
        self.replies = []
        self.response = FakeResponse(self)

    @property
    def description(self):
        return [r.description for r in self.replies if r is not None]


@pytest.fixture(autouse=True)
def fake_server(monkeypatch):
    """Point the bot at a live local server.

    send_request hands the blocking call to a worker thread, so every test needs
    main.server to resolve to something -- otherwise the call races the teardown.
    """
    seen = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen.append(self.path)
            payload = b"sent"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(main, "server", "http://127.0.0.1:{}/".format(httpd.server_port))
    yield seen
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture
def dead_server(monkeypatch):
    """RimWorld not running. Port 1 is reserved, nothing listens on it."""
    monkeypatch.setattr(main, "server", "http://127.0.0.1:1/")


@pytest.fixture
def data_dir(monkeypatch, tmp_path):
    d = tmp_path / "characters"
    monkeypatch.setattr(main, "DATA_DIR", d)
    return d


# --- M3: mutable default argument ------------------------------------------


def test_request_wrapper_does_not_mutate_caller_params(data_dir):
    """M3: `params: dict = {}` was mutated in place by every call.

    The bug never fired because "pawn" is always overwritten, so there is no
    observable request to assert on. The observable part is the caller's dict.
    """
    data_dir.mkdir(parents=True)
    (data_dir / "1").write_text("Ana")

    params = {}
    run(main.request_wrapper("eat", params, player_id=1))

    assert params == {}, "request_wrapper must not inject pawn into the caller's dict"
    assert main.request_wrapper.__defaults__[0] is None


# --- A3: truncation ran after the duplicate check --------------------------


def test_second_user_collapsing_to_same_pawn_is_refused(data_dir):
    """A3: "Alexandria" and "Alexandr" both truncate to "Alexan".

    The duplicate check ran on the full name, so both passed it and both were
    truncated afterwards -- two Discord users controlling one colonist.
    """
    data_dir.mkdir(parents=True)
    (data_dir / "1").write_text("Alexan")  # user 1 already holds "Alexan"

    fake = FakeInteraction(user_id=2)
    run(handler("create_character")(fake, "Alexandr"))

    assert not (data_dir / "2").exists(), "user 2 was given user 1's pawn"
    assert "ya existe" in " ".join(fake.description)


def test_duplicate_check_uses_the_truncated_name(data_dir):
    """A3, second half: the refusal must survive the longer spelling too."""
    data_dir.mkdir(parents=True)
    (data_dir / "1").write_text("Alexan")

    fake = FakeInteraction(user_id=2)
    run(handler("create_character")(fake, "Alexandria"))

    assert "ya existe" in " ".join(fake.description)


# --- N1: bot/characters/ was never created --------------------------------


def test_create_character_works_without_preexisting_data_dir(data_dir):
    """N1: a fresh clone has no bot/characters/ and os.listdir raised FileNotFoundError.

    The directory used to be in the repo because one mapping was tracked by
    accident; once it was gitignored, every new clone hit this.
    """
    assert not data_dir.exists()

    fake = FakeInteraction(user_id=1)
    run(handler("create_character")(fake, "Ana"))

    assert fake.replies, "handler raised instead of replying"
    assert (data_dir / "1").read_text() == "Ana"


def test_clear_characters_works_without_preexisting_data_dir(data_dir):
    """N1, second half: the admin command had the same problem."""
    assert not data_dir.exists()

    fake = FakeInteraction(user_id=1)
    run(handler("clear_characters")(fake))

    assert fake.replies, "handler raised instead of replying"


# --- A1: the bot threw away every response --------------------------------


def test_send_request_reports_failure_instead_of_raising(dead_server):
    """A1: send_request had no timeout and no error handling.

    A dead RimWorld raised ConnectionError on a background thread, which the
    bot never saw -- so every command reported "Request sent" no matter what.
    """
    result = run(main.send_request("eat", {"pawn": "Ana"}))

    assert result is not None, "send_request must return something the bot can show"
    assert "error" in result.lower()


# --- A2: the mapping was persisted before the request succeeded ------------


def test_create_character_does_not_persist_when_rimworld_is_down(data_dir, dead_server):
    """A2: the mapping file was written before the request was even sent.

    That left a mapping pointing at a pawn that never existed, and because the
    file then existed, /create_character refused to retry -- corrupt with no way out.
    """
    fake = FakeInteraction(user_id=1)
    run(handler("create_character")(fake, "Ana"))

    assert not (data_dir / "1").exists()


# --- C2: a typo in one handler shipped unnoticed ---------------------------


class Choice:
    """Stand-in for app_commands.Choice, which needs a Discord client."""

    def __init__(self, value):
        self.value = value


@pytest.mark.parametrize(
    "name,args",
    [
        ("set_priority", (Choice("cleaning"), 2)),
        ("unequip_weapon", ()),
        ("strip", ()),
        ("threat_response", (Choice("flee"),)),
        ("equip_weapon", ()),
        ("equip_clothes", ()),
        ("eat", ()),
        ("rest", ()),
        ("kill", ("Ana",)),
        ("incapacite", ("Ana",)),
        ("rescue", ("Ana",)),
        ("shoot", ("Ana",)),
        ("arrest", ("Ana",)),
        ("fastfetch", ()),
        ("clear_characters", ()),
        ("generate_random_race", ()),
    ],
)
def test_action_handlers_reply(data_dir, name, args):
    """C2: /equip_weapon crashed on `interaction.resppobresonse`.

    Nothing invoked the handlers, so a typo in any of them reached main and only
    surfaced when a user ran that exact command. Every action handler must answer.
    """
    data_dir.mkdir(parents=True)
    (data_dir / "1").write_text("Ana")

    fake = FakeInteraction(user_id=1)
    run(handler(name)(fake, *args))

    assert fake.replies, "{} never replied to its user".format(name)
