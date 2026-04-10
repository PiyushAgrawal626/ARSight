import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

app = FastAPI()

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

VIDEO_DIR = r"c:\Users\Piyush\Desktop\WS\video"
app.mount("/video", StaticFiles(directory=VIDEO_DIR), name="video")

@app.get("/")
async def get():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.get("/videos_list")
async def get_videos_list():
    if not os.path.exists(VIDEO_DIR):
        return {"videos": []}
    videos = [f for f in os.listdir(VIDEO_DIR) if f.endswith(('.mp4', '.webm', '.ogg'))]
    return {"videos": videos}
