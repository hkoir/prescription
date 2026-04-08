const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
const currentUserId = window.currentUserId;
const userRole = window.currentUserRole;
const tenantPrefix = window.tenantPrefix;

let audioUnlocked = false;
let callSocket = null;
let reconnectTimeout = null;

const notifyAudio = new Audio("/static/sounds/notify.mp3");
notifyAudio.loop = false;
notifyAudio.volume = 1.0;

const silenceAudio = new Audio("/static/sounds/silence.mp3");
silenceAudio.volume = 0.0;
let callAudio = null;



// Unlock autoplay
function unlockAudio() {
  if (!audioUnlocked) {
    silenceAudio
      .play()
      .then(() => {
        audioUnlocked = true;
        console.log("✅ Audio unlocked via silence.mp3");
      })
      .catch(err => console.warn("🔒 Unlock failed:", err));
  }
}
document.addEventListener("click", unlockAudio, { once: true });
document.addEventListener("keydown", unlockAudio, { once: true });

function playNotifySound() {
  if (audioUnlocked) {
    notifyAudio.pause();
    notifyAudio.currentTime = 0;
    notifyAudio.play().catch(e => console.warn("🔇 Audio play error:", e));
  } else {
    console.warn("🔇 Audio not unlocked yet");
  }
}


function ringCallAlert(retries = 5) {
  if (audioUnlocked) {
    const ringAudio = new Audio("/static/sounds/ring.mp3");
    ringAudio.loop = true;
    ringAudio.volume = 0.9;

    ringAudio.play().catch(err => {
      console.warn("🔇 Ringtone play failed:", err);
    });

    setTimeout(() => {
      ringAudio.pause();
      ringAudio.currentTime = 0;
    }, 20000);

    return ringAudio;
  } else {
    console.warn("🔇 Audio not unlocked, retrying...");   
    return null;
  }
}




function connectCallSocket() {
  if (!(currentUserId && tenantPrefix)) {
    console.warn("❌ currentUserId or tenantPrefix missing");
    console.log("✅ Latest version of doctor_ws.js loaded");

    return;
  }

  const socketUrl = `${wsScheme}://${window.location.host}/ws/call/${tenantPrefix}/${currentUserId}/`;
  callSocket = new WebSocket(socketUrl);

  if (Notification.permission !== "granted") {
    Notification.requestPermission();
  }

  callSocket.onopen = () => {
    console.log("✅ Call socket connected.");
    clearTimeout(reconnectTimeout);
  };

  callSocket.onmessage = (e) => {
    const data = JSON.parse(e.data);
    console.log("📨 Call socket IN:", data);

    if (data.type === "chat_notify") {
        if (data.sender_id === currentUserId) {          
            return;
        }
      if (typeof window.activeThreadId !== "undefined" &&
        parseInt(window.activeThreadId) === parseInt(data.thread_id)) {
      console.log(`🔕 Suppressing popup: already in thread ${data.thread_id}`);
      return;
        }
      playNotifySound();      
      showChatNotification(data);
      showNotificationPopup(`New message from ${data.sender_name}`, data.thread_id);
    }

if (data.type === "play_ringtone") {
    callAudio = ringCallAlert();
    console.log(`Incoming call from ${data.caller_name}`);

    const popup = document.createElement("div");
    popup.style.cssText = `
        position: fixed;
        bottom: 80px;
        right: 20px;
        background-color: #2c3e50;
        color: white;
        padding: 16px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        font-family: sans-serif;
        width: 300px;
        pointer-events: auto;
    `;
    popup.innerHTML = `
        <div><strong>Incoming Call from ${data.caller_name}</strong></div>
        <div style="margin-top: 10px; display: flex; justify-content: space-between;">
            <button id="joinCallBtn">Open</button>
            <button id="dismissCallBtn">Dismiss</button>
        </div>
    `;
    document.body.appendChild(popup);

    const joinBtn = popup.querySelector("#joinCallBtn");
    const dismissBtn = popup.querySelector("#dismissCallBtn");

    const roomId = data.webrtc_room;

    joinBtn.addEventListener("click", e => {
        try {
            e.preventDefault();
            console.log("✅ Join button clicked");
            
            if (callAudio) { 
                callAudio.pause(); 
                callAudio.currentTime = 0; 
            }

            if (!roomId) {
                console.error("❌ No WebRTC room ID — cannot redirect.");
                alert("No WebRTC room found for this call.");
                return;
            }

            callSocket.send(JSON.stringify({
                type: "join_room",
                room_id: roomId,
                user_role: "doctor",
            }));

            console.log(`➡️ Redirecting to /group_conference/${roomId}/`);
            window.location.href = `/chat/group_conference/${roomId}/`;          
            popup.remove();

        } catch (err) {
            console.error("❌ Error in joinBtn click:", err);
        }
    });

    dismissBtn.addEventListener("click", e => {
        e.preventDefault();
        console.log("ℹ️ Call dismissed");
        if (callAudio) { 
            callAudio.pause(); 
            callAudio.currentTime = 0; 
        }
        popup.remove();
    });
}



    if (data.type === "incoming_call") {     
      try {
        callAudio = ringCallAlert();
      } catch (e) {
        console.warn("🔇 Could not start ringtone:", e);
      }

      const popup = document.createElement("div");
      popup.style.cssText = `
        position: fixed;
        bottom: 80px;
        right: 20px;
        background-color: #2c3e50;
        color: white;
        padding: 16px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        z-index: 10000;
        font-family: sans-serif;
        width: 300px;
        pointer-events: auto;
      `;

  popup.innerHTML = `
        <div><strong>Incoming Call from  ${data.caller_name}</strong></div>
        <div style="margin-top: 10px; display: flex; justify-content: space-between;">
          <button id="joinCallBtn">Open</button>
          <button id="dismissCallBtn">Dismiss</button>
        </div>
      `;

      document.body.appendChild(popup);

      const joinBtn = popup.querySelector("#joinCallBtn");
      const dismissBtn = popup.querySelector("#dismissCallBtn");

      ["click", "touchstart"].forEach(event => {
        document.addEventListener(event, unlockAudio, { once: true });
        joinBtn.addEventListener(event, e => {
          e.preventDefault();
          console.log("Join clicked or tapped");
          if (callAudio) {
            callAudio.pause();
            callAudio.currentTime = 0;
          }
          callSocket.send(JSON.stringify({
            type: "doctor.joined",
             thread_id:data.thread_id,
            patient_id: currentUserId // must be available in JS
          }));
           setTimeout(() => {
            window.location.href = data.zoom_join_url;
          }, 300); // 300ms delay is usually enough
          
        });

        dismissBtn.addEventListener(event, e => {
          e.preventDefault();
          console.log("Dismiss clicked or tapped");
          if (callAudio) {
            callAudio.pause();
            callAudio.currentTime = 0;
          }
          popup.remove();
        });
      });

     

      document.body.appendChild(popup);
    }
  };

  callSocket.onclose = (e) => {
    console.warn("❌ Call socket closed. Reconnecting in 3s...", e.reason);
    reconnectTimeout = setTimeout(connectCallSocket, 3000);
  };

  callSocket.onerror = (err) => {
    console.error("❌ Call socket error:", err);
    callSocket.close();
  };
}

connectCallSocket();

function showNotificationPopup(message, threadId = null) {
  const popup = document.createElement("div");

  Object.assign(popup.style, {
    position: "fixed",
    bottom: "20px",
    right: "20px",
    backgroundColor: "rgba(30, 136, 229, 0.95)",
    color: "white",
    padding: "16px 24px",
    borderRadius: "12px",
    boxShadow: "0 8px 20px rgba(0, 0, 0, 0.15)",
    backdropFilter: "blur(8px)",
    WebkitBackdropFilter: "blur(8px)",
    zIndex: 10000,
    display: "flex",
    alignItems: "center",
    minWidth: "280px",
    maxWidth: "320px",
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    fontSize: "16px",
    fontWeight: "500",
    userSelect: "none",
    cursor: threadId ? "pointer" : "default",
    animation: "slideInUp 0.4s ease forwards",
  });

  if (threadId) {
    popup.onclick = () => {
      const chatUrl =
        userRole === "doctor"
          ? `/chat/doctor/thread/${threadId}/`
          : `/chat/patient/thread/${threadId}/`;
      window.location.href = chatUrl;
    };
  }

  if (!document.getElementById("popup-slide-in-style")) {
    const style = document.createElement("style");
    style.id = "popup-slide-in-style";
    style.textContent = `
      @keyframes slideInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
      }
      .popup-close-button:hover {
        color: #f44336;
      }
    `;
    document.head.appendChild(style);
  }

  const msgSpan = document.createElement("span");
  msgSpan.textContent = message;
  msgSpan.style.flex = "1";

  const closeBtn = document.createElement("button");
  closeBtn.innerHTML = "&times;";
  closeBtn.className = "popup-close-button";

  Object.assign(closeBtn.style, {
    background: "transparent",
    border: "none",
    color: "white",
    fontSize: "22px",
    cursor: "pointer",
    padding: "0 0 2px 16px",
    fontWeight: "700",
    lineHeight: "1",
    transition: "color 0.3s ease",
  });

  closeBtn.onclick = (event) => {
    event.stopPropagation();
    popup.remove();
  };

  popup.appendChild(msgSpan);
  popup.appendChild(closeBtn);
  document.body.appendChild(popup);

  if (!threadId) {
    setTimeout(() => {
      popup.remove();
    }, 20000);
  }
}

// === Browser Notification ===
function showChatNotification(data) {
  if (Notification.permission === "granted") {
    const notification = new Notification(`New message from ${data.sender_name}`, {
      body: data.preview || "New message...",
      icon: data.sender_avatar || "/static/images/icons/patient.png",
    });

    notification.onclick = () => {
      window.focus();
      const chatUrl =
        userRole === "doctor"
          ? `/chat/doctor/thread/${data.thread_id}/`
          : `/chat/patient/thread/${data.thread_id}/`;
      window.location.href = chatUrl;
    };
  }
}
