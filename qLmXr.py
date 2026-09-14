
from flask import Flask, request, render_template
import requests
import os

app = Flask(__name__, template_folder="hNwRt")

API_KEY = os.environ.get("VIDEO_API_KEY")

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

