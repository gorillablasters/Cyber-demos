import os


def get_base_url() -> str:
    """
    Base URL for the backend FastAPI service.
    Uses env DOOMGS_BASE_URL if set, otherwise defaults to localhost:8000.
    """
    return os.getenv("DOOMGS_BASE_URL", "http://localhost:8000")
