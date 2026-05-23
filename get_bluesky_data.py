import os
import sys
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_URL = "https://bsky.social"

BLUESKY_HANDLE = os.getenv("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.getenv("BLUESKY_APP_PASSWORD")

if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
    sys.exit(
        "Missing login details. Run these first:\n"
        'export BLUESKY_HANDLE="yourhandle.bsky.social"\n'
        'export BLUESKY_APP_PASSWORD="your-app-password"'
    )

# Login
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

# Helper: weekly date windows
def make_weekly_windows(start_date, end_date):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    windows = []
    current = start

    while current < end:
        next_date = min(current + timedelta(days=7), end)
        windows.append((
            current.strftime("%Y-%m-%dT00:00:00Z"),
            next_date.strftime("%Y-%m-%dT00:00:00Z")
        ))
        current = next_date

    return windows

date_windows = make_weekly_windows("2026-01-01", "2026-05-22")

# Query list
queries = [
    {"brand_focus": "Tesla", "query_type": "general", "q": "Tesla"},
    {"brand_focus": "BYD", "query_type": "general", "q": "BYD"},
    {"brand_focus": "Comparison", "query_type": "direct_comparison", "q": '"Tesla" "BYD"'},

    {"brand_focus": "Tesla", "query_type": "hashtag", "q": "#Tesla"},
    {"brand_focus": "BYD", "query_type": "hashtag", "q": "#BYD"},

    {"brand_focus": "Tesla", "query_type": "product", "q": '"Tesla Model Y"'},
    {"brand_focus": "Tesla", "query_type": "product", "q": '"Tesla Model 3"'},
    {"brand_focus": "Tesla", "query_type": "product", "q": "Cybertruck"},

    {"brand_focus": "BYD", "query_type": "product", "q": '"BYD Seal"'},
    {"brand_focus": "BYD", "query_type": "product", "q": '"BYD Dolphin"'},
    {"brand_focus": "BYD", "query_type": "product", "q": '"BYD Atto 3"'},

    {"brand_focus": "Comparison", "query_type": "ev_market", "q": '"Tesla" "BYD" EV'},
    {"brand_focus": "Comparison", "query_type": "ev_market", "q": '"Tesla" "Chinese EV"'},
    {"brand_focus": "Comparison", "query_type": "ev_market", "q": '"BYD" "electric vehicle"'}
]

all_posts = []

MAX_PAGES_PER_QUERY_WINDOW = 5
REQUEST_SLEEP_SECONDS = 1.2

# Data collection
for query_info in queries:
    for since_date, until_date in date_windows:
        q = query_info["q"]

        print(f"Collecting: {q} | {since_date} to {until_date}")

        cursor = None

        for page in range(MAX_PAGES_PER_QUERY_WINDOW):
            params = {
                "q": q,
                "limit": 100,
                "lang": "en",
                "since": since_date,
                "until": until_date
            }

            if cursor:
                params["cursor"] = cursor

            response = requests.get(
                f"{BASE_URL}/xrpc/app.bsky.feed.searchPosts",
                headers=headers,
                params=params,
                timeout=30
            )

            if response.status_code == 429:
                print("Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                continue

            if response.status_code != 200:
                print("Error:", response.status_code)
                print(response.text[:500])
                break

            data = response.json()
            posts = data.get("posts", [])

            if not posts:
                break

            for post in posts:
                record = post.get("record", {})
                author = post.get("author", {})

                all_posts.append({
                    "brand_focus": query_info["brand_focus"],
                    "query_type": query_info["query_type"],
                    "query": q,
                    "since_date": since_date,
                    "until_date": until_date,
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

            cursor = data.get("cursor")

            if not cursor:
                break

            time.sleep(REQUEST_SLEEP_SECONDS)

# Save dataset
df = pd.DataFrame(all_posts)

if len(df) > 0:
    before = len(df)
    df.drop_duplicates(subset=["post_uri"], inplace=True)
    after = len(df)

    print(f"Removed duplicates: {before - after}")

df.to_csv("bluesky_tesla_byd_posts.csv", index=False)

print("Saved:", len(df), "posts")
print(df.head())
print(df["brand_focus"].value_counts())
print(df["query_type"].value_counts())