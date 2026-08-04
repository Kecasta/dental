// Widget Interactivo de Chat para Smile Aesthetic & Dental Clinic

const API_CHAT_ENDPOINT = "/api/chat";
const USER_PHONE = "+57300" + Math.floor(1000000 + Math.random() * 9000000); // Generar id de sesión para la demo

function toggleChatWindow() {
    const chatWindow = document.getElementById("chat-window");
    const container = document.getElementById("chat-widget");
    chatWindow.classList.toggle("hidden");
    if (container) {
        container.classList.toggle("active-chat", !chatWindow.classList.contains("hidden"));
    }
}

function openChat(initialText = "") {
    const chatWindow = document.getElementById("chat-window");
    const container = document.getElementById("chat-widget");
    chatWindow.classList.remove("hidden");
    if (container) {
        container.classList.add("active-chat");
    }
    if (initialText) {
        const input = document.getElementById("chat-input");
        input.value = initialText;
        sendMessage();
    }
}


function handleKeyPress(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById("chat-input");
    const text = input.value.trim();
    if (!text) return;

    // Agregar mensaje del usuario en la pantalla
    appendMessage(text, "user");
    input.value = "";

    // Mostrar indicador de escribiendo
    showTypingIndicator();

    try {
        const response = await fetch(API_CHAT_ENDPOINT, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                phone_number: USER_PHONE,
                message: text,
                channel: "web_chat"
            })
        });

        removeTypingIndicator();

        if (response.ok) {
            const data = await response.json();
            appendMessage(data.response_text, "agent");
        } else {
            appendMessage("¡Hola! Tu mensaje ha sido recibido. Sofía te atenderá en un instante. 😊", "agent");
        }
    } catch (error) {
        removeTypingIndicator();
        // Simulación local si el servidor aún no está respondiendo
        setTimeout(() => {
            appendMessage("✨ Sofía (Smile Clinic): Gracias por escribirnos. He recibido tu solicitud y he verificado disponibilidad para tu valoración.", "agent");
        }, 800);
    }
}

function appendMessage(text, sender) {
    const container = document.getElementById("chat-messages");
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${sender}`;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    bubble.innerText = text;

    const time = document.createElement("span");
    time.className = "msg-time";
    time.innerText = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    msgDiv.appendChild(bubble);
    msgDiv.appendChild(time);
    container.appendChild(msgDiv);

    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById("chat-messages");
    const typingDiv = document.createElement("div");
    typingDiv.id = "typing-indicator";
    typingDiv.className = "message agent";
    typingDiv.innerHTML = `<div class="msg-bubble" style="opacity:0.7;">✨ Sofía está escribiendo...</div>`;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById("typing-indicator");
    if (indicator) indicator.remove();
}
