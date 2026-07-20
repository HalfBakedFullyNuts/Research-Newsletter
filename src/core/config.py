import os
from pathlib import Path

ENV_PATH = Path(__file__).parent.parent / ".env"
def _load_env():
    if ENV_PATH.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(str(ENV_PATH))
        except ImportError:
            # Fallback: parse manually
            for line in ENV_PATH.read_text().splitlines():
                if '=' in line and not line.startswith('#'):
                    k, v = line.strip().split('=', 1)
                    os.environ.setdefault(k, v)
_load_env()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "arbeitspsychologe@gmail.com")
GOOGLE_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "/opt/data/.hermes/google_token.json")
GOOGLE_CLIENT_SECRET_PATH = os.getenv("GOOGLE_CLIENT_SECRET_PATH", "/opt/data/.hermes/google_client_secret.json")

DB_PATH = os.getenv("DB_PATH", "/opt/data/Research-Newsletter/cache/subscribers.db")
OPENALEX_DELAY = float(os.getenv("OPENALEX_DELAY", "0.5"))
