import os
import sys
import time
import requests
import pandas as pd

BASE_URL = "https://bsky.social"

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")

if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
    sys.exit(
        "Missing login details. Run these first:\n"
        'export BLUESKY_HANDLE="yourhandle.bsky.social"\n'
        'export BLUESKY_APP_PASSWORD="your-app-password"'
    )

# 1. Login and get access token
login_response = requests.post(
    f"{BASE_URL}/xrpc/com.atproto.server.createSession",
    json={
        "identifier": BLUESKY_HANDLE,
        "password": BLUESKY_APP_PASSWORD
    },
    timeout=30
)

if login_response.status_code != 200:
    print("Login failed:")
    print(login_response.status_code)
    print(login_response.text)
    sys.exit()

session = login_response.json()
access_token = session["accessJwt"]

headers = {
    "Authorization": f"Bearer {access_token}"
}

queries = [
    'Tesla lang:en since:2026-04-01 until:2026-05-22',
    'BYD lang:en since:2026-04-01 until:2026-05-22',
    '"Tesla" "BYD" lang:en since:2026-04-01 until:2026-05-22',
    '#Tesla lang:en since:2026-04-01 until:2026-05-22',
    '#BYD lang:en since:2026-04-01 until:2026-05-22'
]

all_posts = []

for query in queries:
    print(f"Collecting: {query}")

    params = {
        "q": query,
        "limit": 100
    }

    response = requests.get(
        f"{BASE_URL}/xrpc/app.bsky.feed.searchPosts",
        headers=headers,
        params=params,
        timeout=30
    )

    if response.status_code != 200:
        print("Error:", response.status_code)
        print(response.text[:500])
        continue

    data = response.json()

    for post in data.get("posts", []):
        record = post.get("record", {})
        author = post.get("author", {})

        all_posts.append({
            "query": query,
            "post_uri": post.get("uri"),
            "post_cid": post.get("cid"),
            "author_handle": author.get("handle"),
            "author_display_name": author.get("displayName"),
            "text": record.get("text"),
            "created_at": record.get("createdAt"),
            "reply_count": post.get("replyCount"),
            "repost_count": post.get("repostCount"),
            "like_count": post.get("likeCount"),
            "quote_count": post.get("quoteCount")
        })

    time.sleep(1)

df = pd.DataFrame(all_posts)

if len(df) > 0:
    df.drop_duplicates(subset=["post_uri"], inplace=True)

df.to_csv("bluesky_tesla_byd_posts.csv", index=False)

print("Saved:", len(df), "posts")
print(df.head())