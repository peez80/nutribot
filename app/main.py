import os
import tempfile
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from .agy_client import agy_client
from .storage import init_storage, save_entry, DATA_DIR

app = FastAPI(title="AI Nutrition Diary App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage on startup
init_storage()

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount uploads directory
uploads_dir = os.path.join(DATA_DIR, "uploads")
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# In-memory history for simplicity in this demo. 
# A real app might store this in a database or session.
chat_history = []
MAX_CONTEXT_MESSAGES = 5

class ChatMessage(BaseModel):
    text: str
    is_user: bool
    image_urls: List[str] = []

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/history", response_model=List[ChatMessage])
async def get_history():
    return chat_history

@app.post("/api/chat")
async def chat_endpoint(
    message: str = Form(""),
    images: List[UploadFile] = File([])
):
    global chat_history
    
    valid_images = [img for img in images if img.filename]
    if len(valid_images) > 5:
        return JSONResponse(status_code=400, content={"error": "Maximal 5 Bilder erlaubt"})
        
    display_msg = message
    image_paths = []
    image_urls = []
    
    if valid_images:
        for img in valid_images:
            # Save uploaded image permanently
            ext = os.path.splitext(img.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            img_path = os.path.join(DATA_DIR, "uploads", filename)
            
            contents = await img.read()
            with open(img_path, "wb") as f:
                f.write(contents)
                
            image_paths.append(img_path)
            image_urls.append(f"/uploads/{filename}")
            
        if not display_msg:
            display_msg = f"[{len(valid_images)} Bild(er) gesendet]"
        else:
            display_msg += f" [{len(valid_images)} Bild(er) angehängt]"
            
    # Save the user's message to history
    chat_history.append({
        "text": display_msg, 
        "is_user": True,
        "image_urls": image_urls
    })

    # Get the context (last N messages, excluding the current one)
    context = chat_history[-(MAX_CONTEXT_MESSAGES+1):-1]
    
    # Process via agy
    parsed_response = agy_client.process_message(context, message, image_paths)
        
    # Extract data
    entry_type = parsed_response.get("type", "unknown")
    extracted_data = parsed_response.get("data", {})
    ai_reply = parsed_response.get("reply", "Entschuldigung, ich habe das nicht verstanden.")
    
    # Save the structured data
    if entry_type in ["meal", "symptom"]:
        save_entry(entry_type, message, extracted_data)
        
    # Append AI reply to history
    chat_history.append({"text": ai_reply, "is_user": False})
    
    return JSONResponse(content={"reply": ai_reply, "parsed": parsed_response})

class AuthCodeRequest(BaseModel):
    code: str

@app.get("/api/auth/status")
async def auth_status():
    is_auth = agy_client.is_authenticated()
    return {"authenticated": is_auth}

@app.post("/api/auth/start")
async def auth_start():
    url = agy_client.get_login_url()
    return {"url": url}

@app.post("/api/auth/verify")
async def auth_verify(req: AuthCodeRequest):
    success = agy_client.submit_auth_code(req.code)
    return {"success": success}
