import os
import tempfile
import uuid
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from .agy_client import agy_client
from .storage import (
    init_storage, save_entry, DATA_DIR,
    create_session, get_sessions, get_session_history,
    save_session_message, update_session_title, delete_session,
    get_session_prompt, update_session_prompt
)

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
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

class ChatMessage(BaseModel):
    text: str
    is_user: bool
    image_urls: List[str] = []

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    with open(os.path.join(static_dir, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/sessions")
async def create_session_endpoint():
    session_id = create_session("Neuer Chat")
    return {"id": session_id, "title": "Neuer Chat"}

@app.get("/api/sessions")
async def get_sessions_endpoint():
    return get_sessions()

@app.get("/api/sessions/{session_id}/history", response_model=List[ChatMessage])
async def get_history_endpoint(session_id: str):
    history = get_session_history(session_id)
    return history

@app.delete("/api/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    sessions = get_sessions()
    session_metadata = next((s for s in sessions if s["id"] == session_id), None)
    if not session_metadata:
        raise HTTPException(status_code=404, detail="Session not found")
        
    delete_session(session_id)
    return {"success": True}

class SystemPromptRequest(BaseModel):
    prompt: str

@app.get("/api/sessions/{session_id}/prompt")
async def get_prompt_endpoint(session_id: str):
    prompt = get_session_prompt(session_id)
    return {"prompt": prompt}

@app.put("/api/sessions/{session_id}/prompt")
async def update_prompt_endpoint(session_id: str, req: SystemPromptRequest):
    update_session_prompt(session_id, req.prompt)
    return {"success": True}

@app.post("/api/sessions/{session_id}/chat")
async def chat_endpoint(
    session_id: str,
    message: str = Form(""),
    images: List[UploadFile] = File([])
):
    # Verify session exists
    sessions = get_sessions()
    session_metadata = next((s for s in sessions if s["id"] == session_id), None)
    if not session_metadata:
        raise HTTPException(status_code=404, detail="Session not found")

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
            
    # Auto-rename if this is the first message and title is default
    history = get_session_history(session_id)
    if not history and session_metadata.get("title") == "Neuer Chat" and message:
        # Use first 30 chars
        new_title = (message[:27] + "...") if len(message) > 30 else message
        update_session_title(session_id, new_title)

    # Save the user's message to history
    user_msg_data = {
        "text": display_msg, 
        "is_user": True,
        "image_urls": image_urls
    }
    save_session_message(session_id, user_msg_data)

    # Process via agy with FULL context
    session_prompt = get_session_prompt(session_id)
    parsed_response = agy_client.process_message(history, message, image_paths, session_prompt)
        
    # Extract data
    entry_type = parsed_response.get("type", "unknown")
    extracted_data = parsed_response.get("data", {})
    ai_reply = parsed_response.get("reply", "Entschuldigung, ich habe das nicht verstanden.")
    context_truncated = parsed_response.get("context_truncated", False)
    
    # Save the structured data
    if entry_type in ["meal", "symptom"]:
        save_entry(entry_type, message, extracted_data)
        
    # Append AI reply to history
    ai_msg_data = {"text": ai_reply, "is_user": False}
    save_session_message(session_id, ai_msg_data)
    
    return JSONResponse(content={"reply": ai_reply, "parsed": parsed_response, "context_truncated": context_truncated})

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
