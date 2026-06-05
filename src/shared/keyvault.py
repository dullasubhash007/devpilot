"""Azure Key Vault secret client — fetches secrets via Managed Identity."""
import os
from functools import lru_cache

from azure.keyvault.secrets import SecretClient

from .credential import get_credential
from .logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=64)
def get_secret(secret_name: str) -> str:
    vault_uri = os.environ["AZURE_KEY_VAULT_URI"]
    client = SecretClient(vault_url=vault_uri, credential=get_credential())
    secret = client.get_secret(secret_name)
    logger.debug("Fetched secret %s from Key Vault", secret_name)
    return secret.value
