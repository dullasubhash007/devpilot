"""Azure credential provider — Managed Identity in prod, DefaultAzureCredential locally."""
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import os

_credential = None


def get_credential():
    global _credential
    if _credential is None:
        if os.getenv("WEBSITE_INSTANCE_ID"):  # running inside Azure Functions
            _credential = ManagedIdentityCredential()
        else:
            _credential = DefaultAzureCredential()
    return _credential
