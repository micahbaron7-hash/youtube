```python
from flask import Flask, request, render_template, jsonify
import requests
import os
import random
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__, template_folder="hNwRt")

API_KEY = os.environ.get("VIDEO_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_db():
    return psycopg2.connect(DATABASE_URL)


def setup_database():

    if not DATABASE_URL:
        print("DATABASE_URL is missing")
        return

    try:

        conn = get_db()

        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                channel TEXT NOT NULL,
                thumbnail TEXT NOT NULL,
                views BIGINT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS videos_title_search
            ON videos USING GIN (
                to_tsvector('english', title)
            )
        """)

        conn.commit()

        cur.close()
        conn.close()

        print("Database ready")

    except Exception as e:

        print("Database setup error:", e)


setup_database()


def save_videos(videos):

    if not videos:
        return

    if not DATABASE_URL:
        return

    try:

        conn = get_db()

        cur = conn.cursor()

        for video in videos:

            cur.execute("""
                INSERT INTO videos
                (id, title, channel, thumbnail, views)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    title = EXCLUDED.title,
                    channel = EXCLUDED.channel,
                    thumbnail = EXCLUDED.thumbnail,
                    views = EXCLUDED.views
            """, (
                video["id"],
                video["title"],
                video["channel"],
                video["thumbnail"],
                video.get("views", 0)
            ))

        conn.commit()

        cur.close()
        conn.close()

        print("Saved", len(videos), "videos")

    except Exception as e:

        print("Database save error:", e)


def database_search(query, limit=24, offset=0):

    if not DATABASE_URL:
        return []

    try:

        conn = get_db()

        cur = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cur.execute("""
            SELECT
                id,
                title,
                channel,
                thumbnail,
                views
            FROM videos
            WHERE
                to_tsvector(
                    'english',
                    title || ' ' || channel
                )
                @@ plainto_tsquery(
                    'english',
                    %s
                )
            ORDER BY views DESC
            LIMIT %s
            OFFSET %s
        """, (
            query,
            limit,
            offset
        ))

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [dict(row) for row in rows]

    except Exception as e:

        print("Database search error:", e)

        return []


def database_count(query):

    if not DATABASE_URL:
        return 0

    try:

        conn = get_db()

        cur = conn.cursor()

        cur.execute("""
            SELECT COUNT(*)
            FROM videos
            WHERE
                to_tsvector(
                    'english',
                    title || ' ' || channel
                )
                @@ plainto_tsquery(
                    'english',
                    %s
                )
        """, (query,))

        count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return count

    except Exception as e:

        print("Database count error:", e)

        return 0


def youtube_request(endpoint, params):

    try:

        response = requests.get(
            endpoint,
            params=params,
            timeout=15
        )

        print(
            "YouTube:",
            response.status_code
        )

        return response

    except Exception as e:

        print(
            "YouTube request error:",
            e
        )

        return None


def youtube_search(query):

    if not API_KEY:
        return []

    response = youtube_request(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": 50,
            "relevanceLanguage": "en",
            "regionCode": "US",
            "key": API_KEY
        }
    )

    if response is None:
        return []

    if not response.ok:

        print(
            "YouTube search error:",
            response.text
        )

        return []

    try:

        data = response.json()

    except Exception:

        return []

    videos = []

    for item in data.get("items", []):

        video_id = item.get(
            "id",
            {}
        ).get("videoId")

        if not video_id:
            continue

        thumbnails = item["snippet"].get(
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
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "thumbnail": thumbnail,
            "views": 0
        })

    return videos


def get_video_details(video_ids):

    if not video_ids:
        return []

    if not API_KEY:
        return []

    videos = []

    for i in range(
        0,
        len(video_ids),
        50
    ):

        batch = video_ids[i:i + 50]

        response = youtube_request(
            "https://www.googleapis.com/youtube/v3/videos",
            {
                "part": "snippet,statistics",
                "id": ",".join(batch),
                "key": API_KEY
            }
        )

        if response is None:
            continue

        if not response.ok:
            continue

        try:

            data = response.json()

        except Exception:

            continue

        for item in data.get(
            "items",
            []
        ):

            try:

                views = int(
                    item.get(
                        "statistics",
                        {}
                    ).get(
                        "viewCount",
                        0
                    )
                )

            except Exception:

                views = 0

            thumbnails = item["snippet"].get(
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
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "thumbnail": thumbnail,
                "views": views
            })

    return videos


@app.route("/")
def home():

    return render_template(
        "bYxQc.html",
        query=""
    )


@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()

    try:

        page = int(
            request.args.get(
                "page",
                "0"
            )
        )

    except Exception:

        page = 0

    if not query:

        return jsonify({
            "videos": [],
            "next_page": None
        })


    offset = page * 24


    videos = database_search(
        query,
        24,
        offset
    )


    total = database_count(query)


    if not videos and page == 0:

        new_videos = youtube_search(
            query
        )

        if new_videos:

            details = get_video_details(
                [
                    video["id"]
                    for video in new_videos
                ]
            )

            if details:

                save_videos(details)

                videos = database_search(
                    query,
                    24,
                    0
                )

                total = database_count(
                    query
                )


    next_page = None

    if offset + len(videos) < total:

        next_page = str(
            page + 1
        )


    return jsonify({
        "videos": videos,
        "next_page": next_page
    })


@app.route("/recommendations")
def recommendations():

    seen_text = request.args.get(
        "seen",
        ""
    )

    seen = set(
        x for x in seen_text.split(",")
        if x
    )


    if not DATABASE_URL:

        return jsonify({
            "videos": []
        })


    try:

        conn = get_db()

        cur = conn.cursor(
            cursor_factory=RealDictCursor
        )

        cur.execute("""
            SELECT
                id,
                title,
                channel,
                thumbnail,
                views
            FROM videos
            WHERE views >= 1000000
            ORDER BY RANDOM()
            LIMIT 24
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()

        videos = []

        for row in rows:

            video = dict(row)

            if video["id"] in seen:
                continue

            videos.append(video)

        return jsonify({
            "videos": videos
        })

    except Exception as e:

        print(
            "Recommendation error:",
            e
        )

        return jsonify({
            "videos": []
        })


@app.route("/view/<video_id>")
def view(video_id):

    return render_template(
        "bYxQc.html",
        query="",
        watch_id=video_id
    )


@app.route("/database-status")
def database_status():

    if not DATABASE_URL:

        return jsonify({
            "status": "error",
            "message": "DATABASE_URL is missing"
        })


    try:

        conn = get_db()

        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(*) FROM videos"
        )

        count = cur.fetchone()[0]

        cur.close()

        conn.close()

        return jsonify({
            "status": "ok",
            "videos": count
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        })


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
```
