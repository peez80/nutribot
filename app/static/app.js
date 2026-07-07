document.addEventListener("DOMContentLoaded", () => {
    const chatContainer = document.getElementById("chat-container");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");
    const imageUpload = document.getElementById("image-upload");
    const cameraUpload = document.getElementById("camera-upload");
    const imagePreviewContainer = document.getElementById("image-preview-container");
    const removeImageBtn = document.getElementById("remove-image-btn");
    const contextWarning = document.getElementById("context-warning");

    // Sidebar elements
    const sidebar = document.getElementById("sidebar");
    const menuBtn = document.getElementById("menu-btn");
    const closeSidebarBtn = document.getElementById("close-sidebar-btn");
    const sessionList = document.getElementById("session-list");
    const newChatBtn = document.getElementById("new-chat-btn");

    // Auth Modal elements
    const authModal = document.getElementById("auth-modal");
    const authUrlLink = document.getElementById("auth-url-link");
    const authForm = document.getElementById("auth-form");
    const authCodeInput = document.getElementById("auth-code-input");
    const verifyBtn = document.getElementById("verify-btn");

    // System Prompt elements
    const systemPromptBtn = document.getElementById("system-prompt-btn");
    const systemPromptModal = document.getElementById("system-prompt-modal");
    const systemPromptForm = document.getElementById("system-prompt-form");
    const systemPromptInput = document.getElementById("system-prompt-input");
    const closePromptBtn = document.getElementById("close-prompt-btn");
    const savePromptBtn = document.getElementById("save-prompt-btn");

    let selectedImageFiles = [];
    let currentSessionId = localStorage.getItem("currentSessionId");

    // Toggle Sidebar Mobile
    const toggleSidebar = () => {
        sidebar.classList.toggle("open");
    };
    menuBtn.addEventListener("click", toggleSidebar);
    closeSidebarBtn.addEventListener("click", toggleSidebar);

    // Scroll to bottom
    const scrollToBottom = () => {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    };

    // Append a message to the chat
    const appendMessage = (text, isUser, imageUrls = []) => {
        const msgDiv = document.createElement("div");
        msgDiv.className = `message ${isUser ? "user-message" : "ai-message"}`;
        
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";
        
        if (text) {
            const textDiv = document.createElement("div");
            textDiv.textContent = text;
            bubble.appendChild(textDiv);
        }
        
        if (imageUrls && imageUrls.length > 0) {
            const gridDiv = document.createElement("div");
            gridDiv.className = "chat-images-grid";
            imageUrls.forEach(url => {
                const img = document.createElement("img");
                img.src = url;
                img.alt = "Angehängtes Bild";
                img.className = "chat-image";
                gridDiv.appendChild(img);
            });
            bubble.appendChild(gridDiv);
        }
        
        msgDiv.appendChild(bubble);
        chatContainer.appendChild(msgDiv);
        scrollToBottom();
    };

    // Show initial greeting
    const showInitialGreeting = () => {
        chatContainer.innerHTML = '';
        const msgDiv = document.createElement("div");
        msgDiv.className = "message ai-message";
        msgDiv.innerHTML = `<div class="message-bubble">Hallo! Was hast du heute gegessen oder wie fühlst du dich?</div>`;
        chatContainer.appendChild(msgDiv);
    };

    // Show typing indicator
    const showTypingIndicator = () => {
        const typingDiv = document.createElement("div");
        typingDiv.className = "message ai-message typing-container";
        typingDiv.id = "typing-indicator";
        
        const bubble = document.createElement("div");
        bubble.className = "message-bubble typing-indicator";
        bubble.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
        
        typingDiv.appendChild(bubble);
        chatContainer.appendChild(typingDiv);
        scrollToBottom();
    };

    // Remove typing indicator
    const removeTypingIndicator = () => {
        const indicator = document.getElementById("typing-indicator");
        if (indicator) {
            indicator.remove();
        }
    };

    // Update preview UI
    const updatePreviewUI = () => {
        imagePreviewContainer.innerHTML = '';
        if (selectedImageFiles.length > 0) {
            imagePreviewContainer.style.display = "flex";
            selectedImageFiles.forEach((file, index) => {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const itemDiv = document.createElement("div");
                    itemDiv.className = "preview-item";
                    
                    const img = document.createElement("img");
                    img.src = event.target.result;
                    
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "remove-image-btn";
                    btn.innerHTML = '<i class="ph-bold ph-x"></i>';
                    btn.title = "Bild entfernen";
                    btn.onclick = () => {
                        selectedImageFiles.splice(index, 1);
                        updatePreviewUI();
                    };
                    
                    itemDiv.appendChild(img);
                    itemDiv.appendChild(btn);
                    imagePreviewContainer.appendChild(itemDiv);
                };
                reader.readAsDataURL(file);
            });
        } else {
            imagePreviewContainer.style.display = "none";
        }
    };

    // Handle Image Selection
    const handleImageSelection = (e, otherInputToClear) => {
        if (e.target.files && e.target.files.length > 0) {
            const newFiles = Array.from(e.target.files);
            
            if (selectedImageFiles.length + newFiles.length > 5) {
                alert("Du kannst maximal 5 Bilder auf einmal senden.");
            } else {
                selectedImageFiles = [...selectedImageFiles, ...newFiles];
            }
            
            otherInputToClear.value = ""; 
            e.target.value = "";
            updatePreviewUI();
            messageInput.focus();
        }
    };

    imageUpload.addEventListener("change", (e) => handleImageSelection(e, cameraUpload));
    cameraUpload.addEventListener("change", (e) => handleImageSelection(e, imageUpload));

    // --- Session Management ---

    const selectSession = async (sessionId) => {
        currentSessionId = sessionId;
        localStorage.setItem("currentSessionId", sessionId);
        contextWarning.style.display = "none";
        renderSessionList(window.lastSessions || []);
        
        // Hide sidebar on mobile after selection
        if (window.innerWidth <= 768) {
            sidebar.classList.remove("open");
        }

        // Enable system prompt button
        systemPromptBtn.disabled = false;

        try {
            // Fetch system prompt
            const promptRes = await fetch(`/api/sessions/${sessionId}/prompt`);
            if (promptRes.ok) {
                const promptData = await promptRes.json();
                systemPromptInput.value = promptData.prompt || "";
            }

            const response = await fetch(`/api/sessions/${sessionId}/history`);
            const history = await response.json();
            
            chatContainer.innerHTML = '';
            if (history && history.length > 0) {
                history.forEach(msg => {
                    appendMessage(msg.text, msg.is_user, msg.image_urls || []);
                });
            } else {
                showInitialGreeting();
            }
        } catch (error) {
            console.error("Failed to load history", error);
        }
    };

    const createNewSession = async () => {
        try {
            const res = await fetch("/api/sessions", { method: "POST" });
            const data = await res.json();
            await loadSessions();
            selectSession(data.id);
        } catch (err) {
            console.error("Error creating session", err);
        }
    };

    newChatBtn.addEventListener("click", createNewSession);

    const renderSessionList = (sessions) => {
        window.lastSessions = sessions;
        sessionList.innerHTML = '';
        sessions.forEach(session => {
            const div = document.createElement("div");
            div.className = `session-item ${session.id === currentSessionId ? "active" : ""}`;
            
            // Format date slightly
            let dateStr = session.created_at;
            if (dateStr) {
                const d = new Date(dateStr);
                dateStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            }

            div.innerHTML = `
                <div class="session-info">
                    <div class="session-date">${dateStr || "Neu"}</div>
                    <div class="session-title">${session.title}</div>
                </div>
                <button class="icon-button danger delete-btn" title="Chat löschen">
                    <i class="ph-bold ph-trash"></i>
                </button>
            `;
            
            // Handle session selection
            div.addEventListener("click", () => selectSession(session.id));
            
            // Handle deletion
            const deleteBtn = div.querySelector('.delete-btn');
            deleteBtn.addEventListener('click', async (e) => {
                e.stopPropagation(); // prevent selecting the session
                if (confirm('Möchtest du diesen Chat wirklich löschen?')) {
                    try {
                        const res = await fetch(`/api/sessions/${session.id}`, { method: 'DELETE' });
                        if (res.ok) {
                            if (currentSessionId === session.id) {
                                currentSessionId = null;
                                localStorage.removeItem("currentSessionId");
                                chatContainer.innerHTML = '';
                            }
                            await loadSessions();
                        } else {
                            alert("Fehler beim Löschen des Chats.");
                        }
                    } catch (err) {
                        console.error("Error deleting session", err);
                    }
                }
            });

            sessionList.appendChild(div);
        });
    };

    const loadSessions = async () => {
        try {
            const res = await fetch("/api/sessions");
            const sessions = await res.json();
            
            if (!sessions || sessions.length === 0) {
                await createNewSession();
                return;
            }

            renderSessionList(sessions);

            // If currentSessionId not in list or not set, select the first one
            if (!currentSessionId || !sessions.find(s => s.id === currentSessionId)) {
                selectSession(sessions[0].id);
            } else {
                selectSession(currentSessionId);
            }
        } catch (err) {
            console.error("Failed to load sessions", err);
        }
    };

    // Handle form submission
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        if (!currentSessionId) {
            alert("Fehler: Keine aktive Sitzung.");
            return;
        }

        const text = messageInput.value.trim();
        if (!text && selectedImageFiles.length === 0) return;

        // Display user message
        let displayMsg = text;
        let localImageUrls = [];
        if (selectedImageFiles.length > 0) {
            displayMsg += displayMsg ? ` [${selectedImageFiles.length} Bild(er) angehängt]` : `[${selectedImageFiles.length} Bild(er) gesendet]`;
            localImageUrls = selectedImageFiles.map(f => URL.createObjectURL(f));
        }
        
        // Remove initial greeting if it's the first message
        if (chatContainer.children.length === 1 && chatContainer.firstElementChild.innerText.includes("Hallo! Was hast du heute gegessen")) {
            chatContainer.innerHTML = '';
        }

        appendMessage(displayMsg, true, localImageUrls);

        // Prepare form data
        const formData = new FormData();
        formData.append("message", text);
        selectedImageFiles.forEach(file => {
            formData.append("images", file);
        });

        // Reset input
        messageInput.value = "";
        selectedImageFiles = [];
        updatePreviewUI();
        
        showTypingIndicator();
        contextWarning.style.display = "none";

        try {
            const response = await fetch(`/api/sessions/${currentSessionId}/chat`, {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            
            removeTypingIndicator();
            appendMessage(data.reply, false);
            
            if (data.context_truncated) {
                contextWarning.style.display = "flex";
            }
            
            // Reload sessions in case the title changed
            const sessionsRes = await fetch("/api/sessions");
            const sessionsData = await sessionsRes.json();
            renderSessionList(sessionsData);
            
        } catch (error) {
            removeTypingIndicator();
            appendMessage("Es gab einen Verbindungsfehler. Bitte versuche es später noch einmal.", false);
            console.error("Error calling chat API", error);
        }
    });

    // --- System Prompt Flow ---
    systemPromptBtn.addEventListener("click", () => {
        if (!currentSessionId) return;
        systemPromptModal.style.display = "flex";
    });

    closePromptBtn.addEventListener("click", () => {
        systemPromptModal.style.display = "none";
    });

    systemPromptForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!currentSessionId) return;

        const promptText = systemPromptInput.value.trim();
        savePromptBtn.disabled = true;
        savePromptBtn.textContent = "Wird gespeichert...";

        try {
            const res = await fetch(`/api/sessions/${currentSessionId}/prompt`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: promptText })
            });

            if (res.ok) {
                systemPromptModal.style.display = "none";
            } else {
                alert("Fehler beim Speichern des Prompts.");
            }
        } catch (err) {
            console.error("Error saving prompt", err);
            alert("Verbindungsfehler beim Speichern.");
        } finally {
            savePromptBtn.disabled = false;
            savePromptBtn.textContent = "Speichern";
        }
    });

    // --- Auth Flow ---
    const checkAuthStatus = async () => {
        try {
            const res = await fetch("/api/auth/status");
            const data = await res.json();
            if (!data.authenticated) {
                startAuthFlow();
            } else {
                loadSessions();
            }
        } catch (err) {
            console.error("Error checking auth status", err);
        }
    };

    const startAuthFlow = async () => {
        authModal.style.display = "flex";
        authUrlLink.textContent = "Lade Login-URL...";
        
        try {
            const res = await fetch("/api/auth/start", { method: "POST" });
            const data = await res.json();
            
            authUrlLink.href = data.url;
            authUrlLink.textContent = data.url;
        } catch (err) {
            authUrlLink.textContent = "Fehler beim Laden der URL.";
            console.error(err);
        }
    };

    authForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const code = authCodeInput.value.trim();
        if (!code) return;

        verifyBtn.disabled = true;
        verifyBtn.textContent = "Wird verifiziert...";

        try {
            const res = await fetch("/api/auth/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code })
            });
            const data = await res.json();
            
            if (data.success) {
                authModal.style.display = "none";
                loadSessions();
            } else {
                alert("Verifizierung fehlgeschlagen. Bitte versuche es erneut.");
                verifyBtn.disabled = false;
                verifyBtn.textContent = "Verifizieren";
            }
        } catch (err) {
            console.error("Error verifying code", err);
            verifyBtn.disabled = false;
            verifyBtn.textContent = "Verifizieren";
        }
    });

    // Init
    checkAuthStatus();
});
