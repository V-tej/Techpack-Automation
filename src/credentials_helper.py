import os
import base64
from pathlib import Path
# pyrefly: ignore [missing-import]
from loguru import logger

def init_credentials():
    """
    Decodes credentials stored as Base64 environment variables
    and writes them to the credentials/ folder.
    This ensures that Google API credentials aren't checked into GitHub,
    but are dynamically available during production deployment on Render.
    """
    credentials_dir = Path(__file__).parent.parent / "credentials"
    credentials_dir.mkdir(exist_ok=True)

    # 1. Google Service Account Credentials
    sa_b64 = os.environ.get("SERVICE_ACCOUNT_JSON_B64")
    if sa_b64:
        try:
            logger.info("Decoding Google Service Account credentials from environment variable...")
            sa_data = base64.b64decode(sa_b64)
            sa_path = credentials_dir / "service_account.json"
            sa_path.write_bytes(sa_data)
            logger.info(f"Successfully generated Google Service Account credentials: {sa_path}")
        except Exception as e:
            logger.error(f"Failed to decode SERVICE_ACCOUNT_JSON_B64: {e}")

    # 2. Token JSON Credentials (for OAuth user flow)
    token_b64 = os.environ.get("TOKEN_JSON_B64")
    if token_b64:
        try:
            logger.info("Decoding token.json credentials from environment variable...")
            token_data = base64.b64decode(token_b64)
            token_path = credentials_dir / "token.json"
            token_path.write_bytes(token_data)
            logger.info(f"Successfully generated token.json credentials: {token_path}")
        except Exception as e:
            logger.error(f"Failed to decode TOKEN_JSON_B64: {e}")

    # 3. Client Secret JSON (for OAuth registration)
    secret_b64 = os.environ.get("CLIENT_SECRET_JSON_B64")
    if secret_b64:
        try:
            logger.info("Decoding client_secret.json credentials from environment variable...")
            secret_data = base64.b64decode(secret_b64)
            secret_path = credentials_dir / "client_secret.json"
            secret_path.write_bytes(secret_data)
            logger.info(f"Successfully generated client_secret.json credentials: {secret_path}")
        except Exception as e:
            logger.error(f"Failed to decode CLIENT_SECRET_JSON_B64: {e}")
