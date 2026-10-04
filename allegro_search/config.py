"""Configuration management module for Allegro MultiSearch."""

import os
import json
from dataclasses import dataclass
from typing import Optional

CONFIG_FILE_PATH = os.path.expanduser("~/.allegro_multisearch_config.json")
DEFAULT_USER_AGENT = "AllegroMultiSearch/1.0 (Windows NT 10.0; Win64; x64)"


@dataclass
class AllegroConfig:
    client_id: str = ""
    client_secret: str = ""
    user_agent: str = DEFAULT_USER_AGENT
    use_sandbox: bool = False
    user_access_token: str = ""
    user_refresh_token: str = ""

    @classmethod
    def load(cls) -> "AllegroConfig":
        """Load configuration from environment variables or local json file."""
        client_id = os.environ.get("ALLEGRO_CLIENT_ID", "")
        client_secret = os.environ.get("ALLEGRO_CLIENT_SECRET", "")
        user_agent = os.environ.get("ALLEGRO_USER_AGENT", DEFAULT_USER_AGENT)
        use_sandbox = os.environ.get("ALLEGRO_USE_SANDBOX", "false").lower() in ("true", "1", "yes")
        user_access_token = os.environ.get("ALLEGRO_USER_ACCESS_TOKEN", "")
        user_refresh_token = os.environ.get("ALLEGRO_USER_REFRESH_TOKEN", "")

        # Fallback to local config file if env vars are empty
        if os.path.exists(CONFIG_FILE_PATH):
            try:
                with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not client_id:
                        client_id = data.get("client_id", "")
                    if not client_secret:
                        client_secret = data.get("client_secret", "")
                    if not user_agent or user_agent == DEFAULT_USER_AGENT:
                        user_agent = data.get("user_agent", DEFAULT_USER_AGENT)
                    use_sandbox = data.get("use_sandbox", use_sandbox)
                    if not user_access_token:
                        user_access_token = data.get("user_access_token", "")
                    if not user_refresh_token:
                        user_refresh_token = data.get("user_refresh_token", "")
            except Exception:
                pass

        return cls(
            client_id=client_id.strip(),
            client_secret=client_secret.strip(),
            user_agent=user_agent.strip() or DEFAULT_USER_AGENT,
            use_sandbox=use_sandbox,
            user_access_token=user_access_token.strip(),
            user_refresh_token=user_refresh_token.strip()
        )

    def save(self):
        """Save configuration to local json file safely."""
        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "user_agent": self.user_agent,
                "use_sandbox": self.use_sandbox,
                "user_access_token": self.user_access_token,
                "user_refresh_token": self.user_refresh_token
            }
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise RuntimeError(f"Błąd zapisu konfiguracji: {e}")
