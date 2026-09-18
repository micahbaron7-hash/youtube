from flask import Flask, request, render_template, jsonify
import requests
import os
import random
import psycopg2
from psycopg2.extras import RealDictCursor
import subprocess
import threading

app = Flask(
    __name__,
    template_folder="hNwRt"
)

API_KEY = os.environ.get("VIDEO_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")
ADMIN_INDEX_CODE = os.environ.get("ADMIN_INDEX_CODE")

indexer_running = False


def get_db():
    return psycopg2.connect(
        DATABASE_URL
    )


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
                to_tsvector(
                    'english',
                    title || ' ' || channel
                )
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS videos_views_index
            ON videos (views DESC)
        """)

        conn.commit()

        cur.close()
        conn.close()

        print("Database ready")

    except Exception as e:

        print(
            "Database setup error:",
            e
        )


setup_database()


def save_videos(videos):

    if not videos:
        return 0

    if not DATABASE_URL:
        return 0

    try:

        conn = get_db()

        cur = conn.cursor()

        saved = 0

        for video in videos:

            cur.execute("""
                INSERT INTO videos
                (
                    id,
                    title,
                    channel,
                    thumbnail,
                    views
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )

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
                video.get(
                    "views",
                    0
                )
            ))

            saved += 1

        conn.commit()

        cur.close()
        conn.close()

        print(
            "Saved",
            saved,
            "videos"
        )

        return saved

    except Exception as e:

        print(
            "Database save error:",
            e
        )

        return 0


def database_search(
    query,
    limit=24,
    offset=0
):

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
            ORDER BY
                views DESC,
                id
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

        return [
            dict(row)
            for row in rows
        ]

    except Exception as e:

        print(
            "Database search error:",
            e
        )

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
        """, (
            query,
        ))

        count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return count

    except Exception as e:

        print(
            "Database count error:",
            e
        )

        return 0


def get_recommendations(
    seen_ids,
    limit=24
):

    if not DATABASE_URL:
        return []

    try:

        conn = get_db()

        cur = conn.cursor(
            cursor_factory=RealDictCursor
        )

        if seen_ids:

            cur.execute("""
                SELECT
                    id,
                    title,
                    channel,
                    thumbnail,
                    views
                FROM videos
                WHERE
                    views >= 1000000
                    AND NOT (
                        id = ANY(%s)
                    )
                ORDER BY RANDOM()
                LIMIT %s
            """, (
                list(seen_ids),
                limit
            ))

        else:

            cur.execute("""
                SELECT
                    id,
                    title,
                    channel,
                    thumbnail,
                    views
                FROM videos
                WHERE
                    views >= 1000000
                ORDER BY RANDOM()
                LIMIT %s
            """, (
                limit,
            ))

        rows = cur.fetchall()

        cur.close()
        conn.close()

        return [
            dict(row)
            for row in rows
        ]

    except Exception as e:

        print(
            "Recommendation error:",
            e
        )

        return []


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

    if page < 0:
        page = 0

    if not query:

        return jsonify({
            "videos": [],
            "next_page": None,
            "total": 0
        })

    offset = page * 24

    videos = database_search(
        query,
        24,
        offset
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
        "next_page": next_page,
        "total": total
    })


@app.route("/recommendations")
def recommendations():

    seen_text = request.args.get(
        "seen",
        ""
    )

    seen = set(
        x.strip()
        for x in seen_text.split(",")
        if x.strip()
    )

    videos = get_recommendations(
        seen,
        24
    )

    return jsonify({
        "videos": videos
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

        cur.execute("""
            SELECT COUNT(*)
            FROM videos
            WHERE views >= 1000000
        """)

        million_count = cur.fetchone()[0]

        cur.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "videos": count,
            "million_view_videos": million_count
        })

    except Exception as e:

        return jsonify({
            "status": "error",
            "message": str(e)
        })


@app.route(
    "/vibe-admin-index",
    methods=["GET", "POST"]
)
def vibe_admin_index():

    global indexer_running

    if request.method == "GET":

        return """
        <!DOCTYPE html>
        <html>

        <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>Vibe Admin</title>

        <style>

        * {
            box-sizing:border-box;
        }

        body {
            margin:0;
            min-height:100vh;
            display:flex;
            justify-content:center;
            align-items:center;
            background:#0f0f0f;
            color:white;
            font-family:Arial,sans-serif;
        }

        .box {
            width:90%;
            max-width:430px;
            background:#191919;
            border:1px solid #333;
            border-radius:15px;
            padding:30px;
        }

        h1 {
            margin-top:0;
        }

        p {
            color:#999;
        }

        input {
            width:100%;
            padding:14px;
            margin-top:15px;
            background:#0f0f0f;
            color:white;
            border:1px solid #444;
            border-radius:8px;
            font-size:16px;
            outline:none;
        }

        button {
            width:100%;
            padding:14px;
            margin-top:15px;
            background:#292929;
            color:white;
            border:none;
            border-radius:8px;
            cursor:pointer;
            font-size:16px;
        }

        button:hover {
            background:#383838;
        }

        </style>

        </head>

        <body>

        <div class="box">

        <h1>Vibe Admin</h1>

        <p>
        Enter the administrator code to start indexing videos.
        </p>

        <form method="POST">

        <input
            type="password"
            name="code"
            placeholder="Admin code"
            autocomplete="off"
            required
        >

        <button type="submit">
        Run Indexer
        </button>

        </form>

        </div>

        </body>

        </html>
        """

    code = request.form.get(
        "code",
        ""
    ).strip()

    if (
        not ADMIN_INDEX_CODE
        or code != ADMIN_INDEX_CODE
    ):

        return """
        <!DOCTYPE html>
        <html>

        <body style="
            margin:0;
            background:#0f0f0f;
            color:white;
            font-family:Arial;
            padding:40px;
        ">

        <h2>
        Invalid admin code.
        </h2>

        </body>

        </html>
        """, 403

    if indexer_running:

        return """
        <!DOCTYPE html>
        <html>

        <body style="
            margin:0;
            background:#0f0f0f;
            color:white;
            font-family:Arial;
            padding:40px;
        ">

        <h2>
        Indexer is already running.
        </h2>

        <p>
        Wait for the current indexing run to finish.
        </p>

        </body>

        </html>
        """

    if not os.path.exists(
        "indexer.py"
    ):

        return """
        <!DOCTYPE html>
        <html>

        <body style="
            margin:0;
            background:#0f0f0f;
            color:white;
            font-family:Arial;
            padding:40px;
        ">

        <h2>
        indexer.py was not found.
        </h2>

        <p>
        Make sure indexer.py is in the root of your GitHub repository.
        </p>

        </body>

        </html>
        """, 500

    indexer_running = True

    def run_indexer():

        global indexer_running

        try:

            print(
                "Admin started indexer."
            )

            result = subprocess.run(
                [
                    "python",
                    "indexer.py"
                ],
                capture_output=True,
                text=True
            )

            print(
                "Indexer output:"
            )

            print(
                result.stdout
            )

            if result.stderr:

                print(
                    "Indexer errors:"
                )

                print(
                    result.stderr
                )

            print(
                "Indexer finished with code:",
                result.returncode
            )

        except Exception as e:

            print(
                "Indexer execution error:",
                e
            )

        finally:

            indexer_running = False

    thread = threading.Thread(
        target=run_indexer,
        daemon=True
    )

    thread.start()

    return """
    <!DOCTYPE html>
    <html>

    <head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>Vibe Admin</title>

    </head>

    <body style="
        margin:0;
        background:#0f0f0f;
        color:white;
        font-family:Arial;
        padding:40px;
    ">

    <h2>
    Indexer started.
    </h2>

    <p>
    Videos are now being added to the database.
    </p>

    <p>
    Check your Render logs for progress.
    </p>

    <p>
    You can close this page.
    </p>

    </body>

    </html>
    """


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
