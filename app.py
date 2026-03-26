from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, Response
import yt_dlp
import requests

app = FastAPI()

def get_video_info(url):
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return info
    except Exception as e:
        return {"error": str(e)}

def get_video_id(url):
    if "youtu.be" in url:
        return url.split("/")[-1].split("?")[0]
    else:
        return url.split("v=")[1].split("&")[0]

@app.get("/video")
def video(url: str = Query(...)):
    info = get_video_info(url)

    if "error" in info:
        return JSONResponse({"error": info["error"]}, status_code=500)

    return {
        "title": info.get("title"),
        "description": info.get("description"),
        "tags": info.get("tags")
    }

@app.get("/thumbnail")
def thumbnail(url: str = Query(...)):
    vid = get_video_id(url)
    thumb_url = f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"

    img = requests.get(thumb_url).content
    return Response(content=img, media_type="image/jpeg")
