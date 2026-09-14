from flask import Flask, request, render_template
import requests
import os
import random

app = Flask(__name__, template_folder="hNwRt")

API_KEY = os.environ.get("VIDEO_API_KEY")

def get_random_videos():
    if not API_KEY:
        return []

    response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "type": "video",
            "maxResults": 50,
            "order": "viewCount",
            "key": API_KEY
        },
        timeout=10
    )

    if not response.ok:
        return []

    data = response.json()

    ids = []

    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")

        if video_id:
            ids.append(video_id)

    if not ids:
        return []

    stats_response = requests.get(
        "https://www.googleapis.com/youtube/v3/videos",
        params={
            "part": "statistics,snippet",
            "id": ",".join(ids),
            "key": API_KEY
        },
        timeout=10
    )

    if not stats_response.ok:
        return []

    videos = []

    for item in stats_response.json().get("items", []):
        try:
            views = int(item["statistics"].get("viewCount", 0))
        except:
            views = 0

        if views >= 1000000:
            videos.append({
                "id": item["id"],
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"]
            })

    random.shuffle(videos)

    return videos[:24]

@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    videos = []

    if query and API_KEY:
        response = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": 24,
                "key": API_KEY
            },
            timeout=10
        )

        if response.ok:
            data = response.json()

            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")

                if video_id:
                    videos.append({
                        "id": video_id,
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"]
                    })

    else:
        videos = get_random_videos()

    return render_template(
        "bYxQc.html",
        videos=videos,
        query=query,
        watch_id=None
    )

@app.route("/view/<video_id>")
def view(video_id):
    return render_template(
        "bYxQc.html",
        videos=[],
        query="",
        watch_id=video_id
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
