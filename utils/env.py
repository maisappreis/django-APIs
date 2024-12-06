import os
import sys

def is_test() -> bool:
    """
    Returns true if is a test environment
    """
    return "test" in sys.argv


environment = os.environ.get("ENVIROMENT", "dev") if not is_test() else "test"


def is_development() -> bool:
    """
    Returns true if is a development environment
    """
    return environment == "dev"