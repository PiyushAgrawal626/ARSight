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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

print("Initializing OCR Reader on GPU...")
reader = easyocr.Reader(['en', 'de'], gpu=True)

class ConnectionManager:
    def __init__(self):
        self.active_displays: list[WebSocket] = []

    async def connect_display(self, websocket: WebSocket):
        await websocket.accept()
        self.active_displays.append(websocket)

    def disconnect_display(self, websocket: WebSocket):
        self.active_displays.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_displays:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/")
async def get_display():
    with open("static/display.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

@app.websocket("/ws/display")
async def websocket_display(websocket: WebSocket):
    await manager.connect_display(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_display(websocket)

@app.websocket("/ws/process")
async def websocket_process(websocket: WebSocket):
    await websocket.accept()
    logger.info("Video Streamer connected for frame processing.")
    
    import datetime
    with open("extracted_text.txt", "a", encoding="utf-8") as f:
        f.write(f"\n===== NEW SESSION: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    
    last_detected_text = ""
    last_translated_text = ""
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            frame_data = message.get("image")
            
            if frame_data and frame_data.startswith("data:image"):
                header, encoded = frame_data.split(",", 1)
                image_bytes = base64.b64decode(encoded)
                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                image_np = np.array(image)
                
                def _run_ocr():
                    return reader.readtext(image_np)
                
                results = await asyncio.to_thread(_run_ocr)
                
                detected_text = " ".join([res[1] for res in results if res[2] > 0.3])
                
                if detected_text.strip():
                    if detected_text == last_detected_text:
                        continue
                    
                    last_detected_text = detected_text
                    
                    def _translate():
                        return GoogleTranslator(source='auto', target='en').translate(detected_text)
                    translated = await asyncio.to_thread(_translate)
                    
                    if translated == last_translated_text:
                        continue
                        
                    last_translated_text = translated
                    logger.info(f"Broadcast: {translated}")
                    
                    with open("extracted_text.txt", "a", encoding="utf-8") as f:
                        f.write(f"Original: {detected_text}\nTranslated: {translated}\n---\n")
                        
                    await manager.broadcast({
                        "original": detected_text,
                        "translated": translated
                    })
                    
    except WebSocketDisconnect:
        logger.info("Video Streamer disconnected.")
    except Exception as e:
        logger.error(f"Error in processing loop: {e}")
