```python
from flask import Flask, request, render_template, jsonify
import requests
import os
import random

app = Flask(__name__, template_folder="hNwRt")

API_KEY = os.environ.get("VIDEO_API_KEY")


def youtube_request(endpoint, params):
    try:
        response = requests.get(
            endpoint,
            params=params,
            timeout=15
        )

        print("YouTube status:", response.status_code)
        print("YouTube response:", response.text[:2000])

        return response

    except Exception as e:
        print("YouTube request error:", str(e))
        return None


def get_video_details(video_ids):

    if not video_ids:
        return []

    videos = []

    for i in range(0, len(video_ids), 50):

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
            print("VIDEO DETAILS ERROR")
            print(response.text)
            continue

        try:
            data = response.json()
        except Exception:
            print("Could not read YouTube JSON")
            continue

        for item in data.get("items", []):

            try:
                views = int(
                    item.get("statistics", {}).get(
                        "viewCount",
                        0
                    )
                )
            except Exception:
                views = 0

            if views < 1000000:
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
                "id": item["id"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "thumbnail": thumbnail,
                "views": views
            })

    return videos


def get_recommendations(seen):

    if not API_KEY:
        print("ERROR: VIDEO_API_KEY is missing")
        return []

    terms = [
        "music",
        "gaming",
        "funny",
        "sports",
        "science",
        "technology",
        "animation",
        "movies",
        "entertainment",
        "popular videos",
        "viral videos",
        "interesting videos",
        "fun videos",
        "best videos"
    ]

    random.shuffle(terms)

    video_ids = []

    for term in terms[:6]:

        response = youtube_request(
            "https://www.googleapis.com/youtube/v3/search",
            {
                "part": "snippet",
                "q": term,
                "type": "video",
                "maxResults": 50,
                "relevanceLanguage": "en",
                "regionCode": "US",
                "key": API_KEY
            }
        )

        if response is None:
            continue

        if not response.ok:
            print("RECOMMENDATION SEARCH ERROR")
            print(response.text)
            continue

        try:
            data = response.json()
        except Exception:
            print("Could not read recommendation JSON")
            continue

        for item in data.get("items", []):

            video_id = item.get(
                "id",
                {}
            ).get("videoId")

            if not video_id:
                continue

            if video_id in video_ids:
                continue

            if video_id in seen:
                continue

            video_ids.append(video_id)

    random.shuffle(video_ids)

    videos = get_video_details(video_ids)

    random.shuffle(videos)

    return videos[:24]


def search_videos(query, page_token=None):

    if not API_KEY:
        print("ERROR: VIDEO_API_KEY is missing")
        return [], None

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 24,
        "relevanceLanguage": "en",
        "regionCode": "US",
        "key": API_KEY
    }

    if page_token:
        params["pageToken"] = page_token

    response = youtube_request(
        "https://www.googleapis.com/youtube/v3/search",
        params
    )

    if response is None:
        return [], None

    if not response.ok:

        print("SEARCH ERROR")
        print(response.text)

        return [], None

    try:
        data = response.json()
    except Exception:

        print("Could not read search JSON")

        return [], None

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
            "thumbnail": thumbnail
        })

    return videos, data.get("nextPageToken")


@app.route("/")
def home():

    return render_template(
        "bYxQc.html",
        query=request.args.get("q", "")
    )


@app.route("/recommendations")
def recommendations():

    seen_text = request.args.get(
        "seen",
        ""
    )

    seen = set()

    if seen_text:

        seen = set(
            video_id
            for video_id in seen_text.split(",")
            if video_id
        )

    videos = get_recommendations(seen)

    return jsonify({
        "videos": videos
    })


@app.route("/search")
def search():

    query = request.args.get(
        "q",
        ""
    ).strip()

    page_token = request.args.get(
        "page",
        ""
    ).strip()

    if not query:

        return jsonify({
            "videos": [],
            "next_page": None
        })

    videos, next_page = search_videos(
        query,
        page_token if page_token else None
    )

    return jsonify({
        "videos": videos,
        "next_page": next_page
    })


@app.route("/view/<video_id>")
def view(video_id):

    return render_template(
        "bYxQc.html",
        query="",
        watch_id=video_id
    )


@app.route("/debug")
def debug():

    if not API_KEY:

        return jsonify({
            "status": "ERROR",
            "message": "VIDEO_API_KEY is missing from Render environment variables."
        })

    response = youtube_request(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "part": "snippet",
            "q": "music",
            "type": "video",
            "maxResults": 1,
            "key": API_KEY
        }
    )

    if response is None:

        return jsonify({
            "status": "ERROR",
            "message": "Could not connect to YouTube."
        })

    if not response.ok:

        return jsonify({
            "status": "ERROR",
            "youtube_status": response.status_code,
            "youtube_response": response.text
        })

    return jsonify({
        "status": "OK",
        "message": "YouTube API is working."
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
