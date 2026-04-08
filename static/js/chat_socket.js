document.addEventListener("DOMContentLoaded", function () {
  const threadId     = "{{ thread_id }}";
  const userId       = "{{ user_id }}";
  const partnerId    = "{{ chat_partner_id }}";
  const tenantPrefix = "{{ tenant_prefix|default:'public' }}";
  const wsScheme     = window.location.protocol === "https:" ? "wss" : "ws";

  const sendBtn   = document.getElementById("sendBtn");
  const chatInput = document.getElementById("chatInput");
  const chatMedia = document.getElementById("chatMedia");
  const chatBox   = document.getElementById("chatBox");
  const chatTone  = document.getElementById("chatTone");

  const socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/chat/${tenantPrefix}/${userId}/`);

  socket.onopen = () => console.log("✅ WebSocket connected");

  socket.onclose = (event) => {
    console.log("❌ WebSocket disconnected....");
    console.warn("🔍 Close event:", {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
    });
  };

  socket.onerror = (err) => {
    console.error("🚨 WebSocket error:", err);
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log("📩 WS IN:", data);

      if (!data.type) {
        console.warn("⚠️ Unknown message format:", data);
        return;
      }

      switch (data.type) {
        case "chat_message":
          appendMessageWS(
            data.sender_name,
            data.message,
            data.media_url || null,
            String(data.sender_id) === String(userId),
            data.sent_at || ""
          );
          break;

        case "chat_notify":
          console.log("🔔 Chat notify:", data.preview);
          break;

        case "incoming_chat":
          alert(`${data.from_user_name} wants to start a chat!`);
          break;

        default:
          console.warn("⚠️ Unhandled message type:", data.type);
      }
    } catch (err) {
      console.error("💥 Error handling WS message:", err, event.data);
    }
  };

  sendBtn?.addEventListener("click", sendChatMessage);

  chatInput?.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      e.preventDefault();
      sendChatMessage();
    }
  });

  function sendChatMessage() {
    const text = chatInput.value.trim();
    const file = chatMedia.files[0];
    if (!text && !file) return;

    const formData = new FormData();
    formData.append("text", text);
    if (file) formData.append("media", file);

    sendBtn.disabled = true;

    fetch(`/chat/send/${threadId}/`, {
      method: "POST",
      headers: { "X-CSRFToken": "{{ csrf_token }}" },
      body: formData,
    })
      .then((res) => res.json())
      .then((data) => {
        chatInput.value = "";
        chatMedia.value = "";

        if (chatTone) {
          try {
            chatTone.currentTime = 0;
            chatTone.play().catch((e) => console.log("🔇 Tone blocked:", e));
          } catch (err) {
            console.error("🎵 Tone error:", err);
          }
        }
      })
      .catch((err) => console.error("❌ Send error:", err))
      .finally(() => {
        sendBtn.disabled = false;
      });
  }

  function appendMessageWS(senderName, message, mediaUrl, isOwn, sentAt) {
  try {
    if (!chatBox) {
      console.error("🚫 chatBox not found in DOM.");
      return;
    }

    // Container div with margin-bottom and flex alignment for left/right
    const div = document.createElement("div");
    div.className = `d-flex mb-3 ${isOwn ? "justify-content-start" : "justify-content-end"}`;

    // Inner bubble div with chat-bubble and left/right class for color & shape
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${isOwn ? "left" : "right"}`;
    bubble.style.maxWidth = "70%";
    bubble.style.padding = "12px 16px";
    bubble.style.borderRadius = "16px";
    bubble.style.fontSize = "0.95rem";
    bubble.style.lineHeight = "1.4";
    bubble.style.boxShadow = "0 2px 6px rgba(0, 0, 0, 0.08)";
    bubble.style.position = "relative";

    // Inner HTML for bubble content (sender name bold + message text)
    bubble.innerHTML = `
      <strong style="display:block; margin-bottom: 4px; font-weight: 600;">
        ${isOwn ? "You" : senderName || "Unknown"}
      </strong>
      <div>${message || ""}</div>
    `;

    // Append media if any
    if (mediaUrl) {
      let mediaHTML = "";
      if (/\.(mp4|webm|mov)$/i.test(mediaUrl)) {
        mediaHTML = `<video controls width="100%" style="margin-top:8px; border-radius: 8px;">
                       <source src="${mediaUrl}">
                     </video>`;
      } else if (/\.(jpg|jpeg|png|gif)$/i.test(mediaUrl)) {
        mediaHTML = `<img src="${mediaUrl}" class="img-fluid rounded" style="margin-top:8px; max-height:150px; object-fit:cover;" />`;
      } else {
        mediaHTML = `<a href="${mediaUrl}" target="_blank" class="text-primary" style="font-size: 0.85rem; margin-top:8px; display:block;">
                       Download File
                     </a>`;
      }
      bubble.insertAdjacentHTML('beforeend', mediaHTML);
    }

    // Append sent time with same styling as your CSS for timestamp
    if (sentAt) {
      bubble.insertAdjacentHTML('beforeend', `<div class="text-muted" style="font-size:0.75rem; margin-top:6px; text-align:right;">${sentAt}</div>`);
    }

    div.appendChild(bubble);
    chatBox.appendChild(div);

    // Scroll to bottom
    chatBox.scrollTop = chatBox.scrollHeight;

    // Play chat tone if available
    if (chatTone) {
      try {
        chatTone.currentTime = 0;
        chatTone.play().catch((e) => console.log("🔇 Tone play blocked:", e));
      } catch (err) {
        console.error("🔇 Tone error:", err);
      }
    }
  } catch (err) {
    console.error("💥 Error appending message to chat:", err);
  }
}

});