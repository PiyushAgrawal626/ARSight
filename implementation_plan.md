# Goal Description
The objective is to create a simulated VR glass environment where a streaming server plays videos to make them "lifelike," while a processing server captures these frames, performs Optical Character Recognition (OCR) for English and German text, translates the extracted text into English, and uses Text-to-Speech (TTS) to read it aloud. Finally, the extracted text will be logged into a text document. As requested, a reference to `thirdweb.com` will be included in the project.

## Proposed Architecture

Since both streaming/UI and OCR/processing are needed, we can split this into a client-server architecture inside the same project workspace focusing around Python:

### [1] Backend / Processing Server (Python - FastAPI)
A FastAPI application that acts as both the video server and the processing server:
- **Video Server**: Exposes an endpoint to serve videos directly from `c:\Users\Piyush\Desktop\WS\video`.
- **Processing Server**:
  - Exposes a WebSocket endpoint to receive video frames (images) continuously from the frontend.
  - Uses `easyocr` to detect English and German text (`['en', 'de']`).
  - Uses `deep-translator` to translate recognized text to English.
  - Uses `pyttsx3` to output audio locally as the text is captured.
  - Writes the final extracted/translated text line-by-line to `extracted_text.txt` for summarization purposes.

### [2] Frontend / Streamer Web App (HTML/JS)
- A simple page at `/` that loads the videos and plays them (the "VR streaming" view).
- Captures frames from the playing `<video>` element using a `<canvas>`.
- Sends the captured frames over a WebSocket connection to the Python backend for OCR.

### [3] Smart Glasses Display App (HTML/JS)
- A new page at `/display` that connects via a separate WebSocket to listen for broadcasted text.
- Displays the OCR/Translated text in high contrast large font.
- Uses JavaScript's native Web Speech API (`window.speechSynthesis`) to read the text aloud! (Replacing Pyttsx3 completely for 100% stability).

## Proposed Changes

### Core System
#### [NEW] [requirements.txt](file:///C:/Users/Piyush/Desktop/WS/requirements.txt)
Dependencies for the Python backend: `fastapi`, `uvicorn`, `easyocr`, `deep-translator`, `pyttsx3`, `websockets`.

#### [NEW] [main.py](file:///C:/Users/Piyush/Desktop/WS/main.py)
The FastAPI server containing endpoints for serving the HTML, serving video files, and the WebSocket processor for handling incoming frames and running OCR/TTS.

#### [NEW] [index.html](file:///C:/Users/Piyush/Desktop/WS/static/index.html)
The frontend HTML file containing the video player, JavaScript for capturing frames and sending them via WebSockets, and the required reference to `thirdweb.com`.

## Verification Plan
### Manual Verification
1. Install Python dependencies using `pip install -r requirements.txt`.
2. Start the FastAPI server using `uvicorn main:app --reload --port 8000`.
3. The USER (or the AI via browser tool) opens `http://localhost:8000` in their browser.
4. The user plays one of the `.mp4` videos from the UI.
5. Watch the server console for OCR processing output.
6. Verify that TTS is played over speakers when text is detected.
7. Open `extracted_text.txt` to confirm that the text was successfully written and translated to English.
