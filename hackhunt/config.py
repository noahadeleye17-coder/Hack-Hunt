import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "settings.json"


class ConfigError(Exception):
    pass


@dataclass
class Settings:
    online_only: bool = True
    min_days_left: int = 5
    urgent_days: int = 3
    top_n: int = 10
    country: str = "Nigeria"
    exclude_phrases: list[str] = field(default_factory=list)
    interests: dict[str, list[str]] = field(default_factory=dict)
    request_delay_seconds: float = 1.0
    state_path: str = "state/seen.json"

    @property
    def state_file(self) -> Path:
        return ROOT / self.state_path


@dataclass
class MailConfig:
    user: str
    password: str = field(repr=False)
    to: list[str] = field(default_factory=list)


def load_settings(path: Path = SETTINGS_PATH) -> Settings:
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ConfigError(f"couldn't read {path}: {e}") from e
    unknown = sorted(set(raw) - {f.name for f in fields(Settings)})
    if unknown:
        raise ConfigError(f"unknown keys in {path.name}: {', '.join(unknown)}")
    return Settings(**raw)


def load_mail_config() -> MailConfig:
    names = ("GMAIL_USER", "GMAIL_APP_PASSWORD", "DIGEST_TO")
    env = {k: os.environ.get(k, "").strip() for k in names}
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise ConfigError(f"missing environment variables: {', '.join(missing)}")
    return MailConfig(
        user=env["GMAIL_USER"],
        # Gmail shows app passwords in groups of four; the spaces aren't part of it.
        password=env["GMAIL_APP_PASSWORD"].replace(" ", ""),
        to=[a.strip() for a in env["DIGEST_TO"].split(",") if a.strip()],
    )
