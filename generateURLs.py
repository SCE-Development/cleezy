import sqlite3
import requests

BASE_URL = "http://localhost:8000/create_url"

def create_url(url, alias):
    """Send a POST request to create a URL with an alias."""
    response = requests.post(f"{BASE_URL}", json={"url": url, "alias": alias})
    if response.status_code == 200:
        print(f"Successfully created {alias}: {url}")
    else:
        print(f"Failed to create {alias}: {url}. Status code: {response.status_code}")

def main():
    for i in range(1000):
        url = f"http://example.com/{i}"
        alias = f"alias{i}"
        create_url(url, alias)
if __name__ == "__main__":
    main()