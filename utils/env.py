import os
import sys


def is_test() -> bool:
    """Return whether Django's test command is running."""
    return "test" in sys.argv


def get_environment() -> str:
    """Return the explicit app environment, with native Vercel fallback."""
    if is_test():
        return "test"

    environment = (
        os.environ.get("ENVIRONMENT")
        or os.environ.get("VERCEL_ENV")
        or "development"
    )

    normalized_environment = environment.strip().lower()
    aliases = {
        "dev": "development",
        "prod": "production",
    }
    return aliases.get(normalized_environment, normalized_environment)


def is_development() -> bool:
    """Return whether the app is running in development."""
    return get_environment() == "development"


def is_production() -> bool:
    """Return whether the app is running in production."""
    return get_environment() == "production"


def get_neon_pooler_host(host: str | None) -> str | None:
    """Convert a standard Neon hostname to its pooled endpoint hostname."""
    if not host or not host.endswith(".neon.tech"):
        return host

    endpoint, separator, domain = host.partition(".")
    if endpoint.endswith("-pooler"):
        return host

    return f"{endpoint}-pooler{separator}{domain}"
