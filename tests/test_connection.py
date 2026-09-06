"""update_dotenv() — merge keys into .env without touching anything else.

Offline: operates on a tmp file, no robot or cloud involved.
"""

from dreame_mcp.server import update_dotenv


def test_update_dotenv_replaces_and_appends(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "# comment\nDREAME_IP=192.168.0.178\nDREAME_USER=old@example.com\n\nDREAME_COUNTRY=eu\n",
        encoding="utf-8",
    )
    update_dotenv({"DREAME_USER": "new@example.com", "DREAME_PASSWORD": "s3cret"}, path=env)
    text = env.read_text(encoding="utf-8")
    assert "DREAME_USER=new@example.com" in text
    assert "old@example.com" not in text
    assert "DREAME_PASSWORD=s3cret" in text
    assert "# comment" in text
    assert "DREAME_IP=192.168.0.178" in text
    assert "DREAME_COUNTRY=eu" in text


def test_update_dotenv_creates_backup(tmp_path):
    env = tmp_path / ".env"
    env.write_text("DREAME_IP=192.168.0.178\n", encoding="utf-8")
    update_dotenv({"DREAME_IP": "192.168.0.190"}, path=env)
    backups = list(tmp_path.glob(".env.*.bak"))
    assert len(backups) == 1
    assert "192.168.0.178" in backups[0].read_text(encoding="utf-8")
    assert "DREAME_IP=192.168.0.190" in env.read_text(encoding="utf-8")


def test_update_dotenv_missing_file(tmp_path):
    env = tmp_path / ".env"
    update_dotenv({"DREAME_IP": "192.168.0.190"}, path=env)
    assert "DREAME_IP=192.168.0.190" in env.read_text(encoding="utf-8")
