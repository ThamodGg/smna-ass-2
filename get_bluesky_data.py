import requests
import pandas as pd
import time

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
        "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
        params=params
    )

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
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
df.drop_duplicates(subset=["post_uri"], inplace=True)

df.to_csv("bluesky_tesla_byd_posts.csv", index=False)

print("Saved:", len(df), "posts")
df.head()