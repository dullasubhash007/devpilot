"""Azure credential provider — Managed Identity in prod, DefaultAzureCredential locally."""
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
import os

_credential = None


def get_credential():
    global _credential
    if _credential is None:
        # IDENTITY_ENDPOINT is set in Azure Container Apps and Azure Functions
        if os.getenv("IDENTITY_ENDPOINT") or os.getenv("WEBSITE_INSTANCE_ID"):
            _credential = ManagedIdentityCredential()
        else:
            _credential = DefaultAzureCredential()
    return _credential
