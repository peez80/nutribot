document.addEventListener("DOMContentLoaded", () => {
    const chatContainer = document.getElementById("chat-container");
    const chatForm = document.getElementById("chat-form");
    const messageInput = document.getElementById("message-input");
    const imageUpload = document.getElementById("image-upload");
    const cameraUpload = document.getElementById("camera-upload");
    const imagePreviewContainer = document.getElementById("image-preview-container");
    const imagePreview = document.getElementById("image-preview");
    const removeImageBtn = document.getElementById("remove-image-btn");

    // Auth Modal elements
    const authModal = document.getElementById("auth-modal");
    const authUrlLink = document.getElementById("auth-url-link");
    const authForm = document.getElementById("auth-form");
    const authCodeInput = document.getElementById("auth-code-input");
    const verifyBtn = document.getElementById("verify-btn");

    let selectedImageFiles = [];

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

    // Load History
    const loadHistory = async () => {
        try {
            const response = await fetch("/api/history");
            const history = await response.json();
            if (history && history.length > 0) {
                chatContainer.innerHTML = ''; // clear initial greeting if there's history
                history.forEach(msg => {
                    appendMessage(msg.text, msg.is_user, msg.image_urls || []);
                });
            }
        } catch (error) {
            console.error("Failed to load history", error);
        }
    };

    // Handle form submission
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const text = messageInput.value.trim();
        if (!text && selectedImageFiles.length === 0) return;

        // Display user message
        let displayMsg = text;
        let localImageUrls = [];
        if (selectedImageFiles.length > 0) {
            displayMsg += displayMsg ? ` [${selectedImageFiles.length} Bild(er) angehängt]` : `[${selectedImageFiles.length} Bild(er) gesendet]`;
            localImageUrls = selectedImageFiles.map(f => URL.createObjectURL(f));
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

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                body: formData
            });
            const data = await response.json();
            
            removeTypingIndicator();
            appendMessage(data.reply, false);
            
        } catch (error) {
            removeTypingIndicator();
            appendMessage("Es gab einen Verbindungsfehler. Bitte versuche es später noch einmal.", false);
            console.error("Error calling chat API", error);
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
                loadHistory();
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
                loadHistory();
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
