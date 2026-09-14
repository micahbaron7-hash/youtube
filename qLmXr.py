from flask import Flask, request, render_template
import requests
import os
import random

app = Flask(__name__, template_folder="hNwRt")

API_KEY = os.environ.get("VIDEO_API_KEY")


def get_random_videos():
    if not API_KEY:
        return []

    search_terms = [
        "music",
        "gaming",
        "funny",
        "sports",
        "movies",
        "animation",
        "science",
        "technology",
        "tutorial",
        "entertainment"
    ]

    random.shuffle(search_terms)

    video_ids = []

    for term in search_terms[:5]:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": term,
                "type": "video",
                "maxResults": 50,
                "key": API_KEY
            },
            timeout=10
        )

        if response.ok:
            for item in response.json().get("items", []):
                video_id = item.get("id", {}).get("videoId")

                if video_id and video_id not in video_ids:
                    video_ids.append(video_id)

    if not video_ids:
        return []

    videos = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]

        response = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "statistics,snippet",
                "id": ",".join(batch),
                "key": API_KEY
            },
            timeout=10
        )

        if not response.ok:
            continue

        for item in response.json().get("items", []):
            try:
                views = int(
                    item.get("statistics", {}).get("viewCount", 0)
                )
            except:
                views = 0

            if views >= 1000000:
                thumbnails = item["snippet"].get("thumbnails", {})

                thumbnail = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url")
                )

                if thumbnail:
                    videos.append({
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "thumbnail": thumbnail
                    })

    random.shuffle(videos)

    return videos[:24]


def search_videos(query, page_token=None):
    if not API_KEY:
        return [], None

    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": 24,
        "key": API_KEY
    }

    if page_token:
        params["pageToken"] = page_token

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params=params,
        timeout=10
    )

    if not response.ok:
        return [], None

    data = response.json()

    videos = []

    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")

        if video_id:
            thumbnails = item["snippet"].get("thumbnails", {})

            thumbnail = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )

            if thumbnail:
                videos.append({
                    "id": video_id,
                    "title": item["snippet"]["title"],
                    "channel": item["snippet"]["channelTitle"],
                    "thumbnail": thumbnail
                })

    return videos, data.get("nextPageToken")


@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    page_token = request.args.get("page", "").strip()

    if query:
        videos, next_page = search_videos(query, page_token)
    else:
        videos = get_random_videos()
        next_page = None

    return render_template(
        "bYxQc.html",
        videos=videos,
        query=query,
        next_page=next_page,
        watch_id=None
    )


@app.route("/view/<video_id>")
def view(video_id):
    return render_template(
        "bYxQc.html",
        videos=[],
        query="",
        next_page=None,
        watch_id=video_id
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
