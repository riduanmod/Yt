# ------------------------------------------------------------
# YouTube Advanced Info API — Refactored for Production & Vercel
# Purpose: Get full YouTube channel info + latest video + live status
# ------------------------------------------------------------

import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# JSON এর কি-গুলো যেন অটোমেটিক সাজিয়ে না যায় এবং আমাদের সিরিয়াল ঠিক থাকে
app.config['JSON_SORT_KEYS'] = False
if hasattr(app, 'json'):
    app.json.sort_keys = False

# প্রোডাকশনের জন্য Environment Variable ব্যবহার করা ভালো, না পেলে ডিফল্টটা ব্যবহার করবে
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "AIzaSyAAgbg_JXUaB711YdQBBJ_CdPmFpdpGf2o")
TIMEOUT_SECONDS = 10

def get_channel_id(name_or_id):
    """Detect if input is ID or Name and return valid channel ID"""
    if name_or_id.startswith("UC"):
        return name_or_id

    search_url = f"https://www.googleapis.com/youtube/v3/search?part=id&type=channel&q={name_or_id}&key={YOUTUBE_API_KEY}"
    resp = requests.get(search_url, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    data = resp.json()
    
    if data.get("items"):
        return data["items"][0]["id"].get("channelId")
    return None

def get_channel_info(channel_id):
    """Fetch channel details"""
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&id={channel_id}&key={YOUTUBE_API_KEY}"
    r = requests.get(url, timeout=TIMEOUT_SECONDS)
    r.raise_for_status()
    return r.json()

def get_recent_videos(channel_id):
    """Fetch latest 8 videos"""
    url = (
        f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}"
        f"&channelId={channel_id}&part=snippet,id&order=date&maxResults=8"
    )
    r = requests.get(url, timeout=TIMEOUT_SECONDS)
    r.raise_for_status()
    return r.json()

def check_live_status(channel_id):
    """Check if channel is currently live"""
    url = (
        f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}"
        f"&eventType=live&type=video&key={YOUTUBE_API_KEY}"
    )
    r = requests.get(url, timeout=TIMEOUT_SECONDS)
    r.raise_for_status()
    data = r.json()
    
    if data.get("items"):
        live_vid = data["items"][0]
        vid = live_vid["id"].get("videoId")
        return {
            "status": "LIVE 🔴",
            "video_id": vid,
            "title": live_vid["snippet"].get("title"),
            "url": f"https://youtu.be/{vid}"
        }
    return {"status": "OFFLINE ⚫"}

@app.route("/api/yt", methods=["GET"])
def yt_api():
    query = request.args.get("channel")
    if not query:
        return jsonify({"error": "Missing parameter 'channel'"}), 400

    try:
        channel_id = get_channel_id(query)
        if not channel_id:
            return jsonify({"error": "Channel not found"}), 404

        info = get_channel_info(channel_id)
        if not info.get("items"):
            return jsonify({"error": "No channel data available"}), 404

        ch = info["items"][0]
        snippet = ch.get("snippet", {})
        stats = ch.get("statistics", {})

        # Live status check
        live_data = check_live_status(channel_id)
        live_status = live_data["status"]

        # Recent uploads
        recents = get_recent_videos(channel_id)
        vids = []
        last_video_date = None
        
        for v in recents.get("items", []):
            vid = v.get("id", {}).get("videoId")
            if not vid:
                continue
            sn = v.get("snippet", {})
            published_at = sn.get("publishedAt")
            
            vids.append({
                "video_id": vid,
                "title": sn.get("title"),
                "published_at": published_at,
                "thumbnail": sn.get("thumbnails", {}).get("high", {}).get("url"),
                "url": f"https://youtu.be/{vid}"
            })

            if not last_video_date:
                last_video_date = published_at

        # ডাটাগুলো আপনার চাওয়া নির্দিষ্ট সিরিয়ালে সাজানো হয়েছে
        out = {
            "channel_name": snippet.get("title"),
            "username": snippet.get("customUrl"),  # Username added
            "total_videos": stats.get("videoCount"),
            "subscribers": stats.get("subscriberCount"),
            "views": stats.get("viewCount"),
            "live_status": live_status,
            "channel_id": channel_id,
            "creation_date": snippet.get("publishedAt"),
            "description": snippet.get("description"),
            "country": snippet.get("country"),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "last_video_date": last_video_date,
            "recent_videos": vids
        }

        # যদি লাইভ থাকে, তাহলে লাইভ ভিডিওর ডিটেইলস অ্যাড হবে
        if live_status == "LIVE 🔴":
            out["live_video"] = {
                "video_id": live_data.get("video_id"),
                "title": live_data.get("title"),
                "url": live_data.get("url")
            }

        return jsonify(out)

    except requests.exceptions.RequestException as e:
        # API কল ফেইল করলে প্রপার রেসপন্স
        return jsonify({"error": "Third-party API request failed", "details": str(e)}), 502
    except Exception as e:
        # ইন্টারনাল কোনো এরর হলে
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

# Vercel-এর জন্য নিচের অংশটুকু ম্যান্ডেটরি নয়, তবে লোকাল টেস্টিংয়ের জন্য রাখা হলো
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"[🚀] Starting API on port {port} ...")
    app.run(host='0.0.0.0', port=port, debug=False)
