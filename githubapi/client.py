import os
import requests

GITHUB_API_TOKEN = os.environ.get("GITHUB_API_TOKEN")

# Default headers
HEADERS = {"Accept": "application/vnd.github.v3+json"}

# Add token if available
if GITHUB_API_TOKEN:
    HEADERS["Authorization"] = f"token {GITHUB_API_TOKEN}"

def fetch_user(username: str):
    """Fetch a GitHub user's profile info."""
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()  # raises error if GitHub responds with 4xx/5xx
    return response.json()
