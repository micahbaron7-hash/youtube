import os
import requests
import psycopg2

API_KEY = os.environ.get("VIDEO_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

TOPICS = [
    "music",
    "gaming",
    "minecraft",
    "roblox",
    "fortnite",
    "sports",
    "basketball",
    "football",
    "soccer",
    "funny",
    "science",
    "technology",
    "movies",
    "animation",
    "news",
    "history",
    "cooking",
    "fitness",
    "cars",
    "travel"
]

SEARCHES_PER_RUN = 5


def get_db():
    return psycopg2.connect(DATABASE_URL)


def search_youtube(query):
    response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 50,
            "relevanceLanguage": "en",
            "regionCode": "US",
            "key": API_KEY
        },
        timeout=15
    )

    if not response.ok:
        print("YouTube search error:", response.text)
        return []

    data = response.json()

    videos = []

    for item in data.get("items", []):

        video_id = item.get(
            "id",
            {}
        ).get("videoId")

        if not video_id:
            continue

        snippet = item.get(
            "snippet",
            {}
        )

        thumbnails = snippet.get(
            "thumbnails",
            {}
        )

        thumbnail = (
            thumbnails.get(
                "high",
                {}
            ).get("url")
            or thumbnails.get(
                "medium",
                {}
            ).get("url")
            or thumbnails.get(
                "default",
                {}
            ).get("url")
        )

        if not thumbnail:
            continue

        videos.append({
            "id": video_id,
            "title": snippet.get(
                "title",
                ""
            ),
            "channel": snippet.get(
                "channelTitle",
                ""
            ),
            "thumbnail": thumbnail
        })

    return videos


def get_details(video_ids):

    if not video_ids:
        return []

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "snippet,statistics",
            "id": ",".join(video_ids),
            "key": API_KEY
        },
        timeout=15
    )

    if not response.ok:
        print("YouTube details error:", response.text)
        return []

    data = response.json()

    videos = []

    for item in data.get("items", []):

        statistics = item.get(
            "statistics",
            {}
        )

        try:
            views = int(
                statistics.get(
                    "viewCount",
                    0
                )
            )
        except Exception:
            views = 0

        snippet = item.get(
            "snippet",
            {}
        )

        thumbnails = snippet.get(
            "thumbnails",
            {}
        )

        thumbnail = (
            thumbnails.get(
                "high",
                {}
            ).get("url")
            or thumbnails.get(
                "medium",
                {}
            ).get("url")
            or thumbnails.get(
                "default",
                {}
            ).get("url")
        )

        if not thumbnail:
            continue

        videos.append({
            "id": item["id"],
            "title": snippet.get(
                "title",
                ""
            ),
            "channel": snippet.get(
                "channelTitle",
                ""
            ),
            "thumbnail": thumbnail,
            "views": views
        })

    return videos


def save_videos(videos):

    if not videos:
        return 0

    conn = get_db()
    cur = conn.cursor()

    saved = 0

    for video in videos:

        cur.execute(
            """
            INSERT INTO videos
            (id, title, channel, thumbnail, views)
            VALUES (%s, %s, %s, %s, %s)

            ON CONFLICT (id)
            DO UPDATE SET
                title = EXCLUDED.title,
                channel = EXCLUDED.channel,
                thumbnail = EXCLUDED.thumbnail,
                views = EXCLUDED.views
            """,
            (
                video["id"],
                video["title"],
                video["channel"],
                video["thumbnail"],
                video["views"]
            )
        )

        saved += 1

    conn.commit()

    cur.close()
    conn.close()

    return saved


def main():

    if not API_KEY:
        print("VIDEO_API_KEY is missing")
        return

    if not DATABASE_URL:
        print("DATABASE_URL is missing")
        return

    print("Starting Vibe indexer...")

    topics = TOPICS[:SEARCHES_PER_RUN]

    total = 0

    for topic in topics:

        print()
        print("Searching:", topic)

        results = search_youtube(topic)

        print(
            "Found:",
            len(results)
        )

        ids = [
            video["id"]
            for video in results
        ]

        videos = get_details(ids)

        print(
            "Got details:",
            len(videos)
        )

        saved = save_videos(videos)

        print(
            "Saved:",
            saved
        )

        total += saved

    print()
    print("Indexer finished.")
    print("Total processed:", total)


if __name__ == "__main__":
    main()
