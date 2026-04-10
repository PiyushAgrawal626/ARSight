import os
import asyncio
import base64
import json
import logging
from io import BytesIO

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from PIL import Image
import numpy as np

import easyocr
from deep_translator import GoogleTranslator
import pyttsx3

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Mount the static directory for the frontend
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Expose video folder directly
VIDEO_DIR = r"c:\Users\Piyush\Desktop\WS\video"
app.mount("/video", StaticFiles(directory=VIDEO_DIR), name="video")

# Initialize OCR and TTS
print("Initializing OCR Reader (may take a moment to download models)...")
# Using en and de for languages; using GPU as requested.
reader = easyocr.Reader(['en', 'de'], gpu=True)

import queue
import threading
import subprocess

# Initialize TTS in a dedicated thread to avoid concurrency crashes
speech_queue = queue.Queue()
def tts_worker():
    while True:
        text = speech_queue.get()
        if text is None: break
        try:
            # Use subprocess to completely isolate the Windows COM TTS engine and avoid frozen threads
            script = f'import pyttsx3; e=pyttsx3.init(); e.say("""{text}"""); e.runAndWait()'
            subprocess.run(['python', '-c', script], creationflags=0x08000000)
        except Exception as e:
            logger.error(f"TTS Error: {e}")
        speech_queue.task_done()

threading.Thread(target=tts_worker, daemon=True).start()

TEXT_LOG_FILE = "extracted_text.txt"

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

@app.websocket("/ws/process")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected for processing frames.")
    
    last_detected_text = ""
    last_translated_text = ""
    
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_text()
            message = json.loads(data)
            frame_data = message.get("image")
            
            if frame_data and frame_data.startswith("data:image"):
                # Decode base64
                header, encoded = frame_data.split(",", 1)
                image_bytes = base64.b64decode(encoded)
                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                image_np = np.array(image)
                
                # Run OCR in background thread
                def _run_ocr():
                    return reader.readtext(image_np)
                
                results = await asyncio.to_thread(_run_ocr)
                
                # Filter results by confidence
                detected_text = " ".join([res[1] for res in results if res[2] > 0.3])
                
                if detected_text.strip():
                    if detected_text == last_detected_text:
                        continue
                    
                    last_detected_text = detected_text
                    
                    # Translate German to English
                    def _translate():
                        return GoogleTranslator(source='auto', target='en').translate(detected_text)
                    translated = await asyncio.to_thread(_translate)
                    
                    if translated == last_translated_text:
                        continue
                    
                    last_translated_text = translated
                    
                    logger.info(f"Detected Text: {detected_text}")
                    logger.info(f"Translated to English: {translated}")
                    
                    # Store in txt
                    with open(TEXT_LOG_FILE, "a", encoding="utf-8") as f:
                        f.write(f"Original: {detected_text}\nTranslated (EN): {translated}\n---\n")
                        
                    # Send result back to frontend
                    await websocket.send_json({
                        "original": detected_text,
                        "translated": translated
                    })
                    
                    # Queue the text to be read aloud sequentially and safely
                    speech_queue.put(translated)
                    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as e:
        logger.error(f"Error in websocket loop: {e}")
