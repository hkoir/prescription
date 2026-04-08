const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
const doctorUserId = window.doctorUserId;
const tenantPrefix = window.tenantPrefix;

let callRingAudio = null;
let audioUnlocked = false;
let callSocket = null;
let reconnectTimeout = null;

// Unlock audio with silent fallback
(function unlockAudio() {
  const silentAudio = new Audio("/static/sounds/silence.mp3");
  silentAudio.play().then(() => {
    console.log("Audio unlocked via silent.mp3");
    audioUnlocked = true;
  }).catch(() => {
    console.log("Silent autoplay blocked. Waiting for interaction...");
    const unlock = () => {
      const temp = new Audio("/static/sounds/ring.mp3");
      temp.play().then(() => {
        temp.pause();
        temp.currentTime = 0;
        audioUnlocked = true;
        console.log("Audio unlocked by user gesture.");
      }).catch(err => console.warn("Unlock failed:", err));
      document.body.removeEventListener("click", unlock);
      document.body.removeEventListener("mousemove", unlock);
    };
    document.body.addEventListener("click", unlock);
    document.body.addEventListener("mousemove", unlock);
  });
})();

function ringCallAlert() {
  if (callRingAudio) {
    callRingAudio.pause();
    callRingAudio.currentTime = 0;
  }

  callRingAudio = new Audio("/static/sounds/ring.mp3");
  callRingAudio.loop = true;
  callRingAudio.volume = 0.9;

  callRingAudio.play().catch(err => {
    console.warn("Ringtone autoplay failed:", err);
  });

  setTimeout(() => {
    if (callRingAudio) {
      callRingAudio.pause();
      callRingAudio.currentTime = 0;
    }
  }, 20000);
}

function connectCallSocket() {
  if (!(doctorUserId && tenantPrefix)) {
    console.warn("doctorUserId or tenantPrefix missing; websocket not opened.");
    return;
  }

  const socketUrl = `${wsScheme}://${window.location.host}/ws/call/${tenantPrefix}/${doctorUserId}/`;
  callSocket = new WebSocket(socketUrl);

  if (Notification.permission !== "granted") {
    Notification.requestPermission();
  }

  callSocket.onopen = function () {
    console.log("Call socket connected.");
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout);
      reconnectTimeout = null;
    }
  };

  callSocket.onmessage = function (e) {
    const data = JSON.parse(e.data);
    console.log("Call socket IN: ", data);

    if (data.type === "chat_notify") {
      showChatNotification(data);
      showNotificationPopup(`New message from ${data.sender_name}`, data.thread_id);
    }

    if (data.type === "incoming_call") {
      if (audioUnlocked) ringCallAlert();

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
      `;

      popup.innerHTML = `
        <div><strong>Incoming Call from ${data.patient_name}</strong></div>
        <div style="margin-top: 10px; display: flex; justify-content: space-between;">
          <button id="joinCallBtn">Join</button>
          <button id="dismissCallBtn">Dismiss</button>
        </div>
      `;

      popup.querySelector("#joinCallBtn").onclick = () => {
        if (callRingAudio) {
          callRingAudio.pause();
          callRingAudio.currentTime = 0;
        }
        window.location.href = data.zoom_start_url;
      };

      popup.querySelector("#dismissCallBtn").onclick = () => {
        if (callRingAudio) {
          callRingAudio.pause();
          callRingAudio.currentTime = 0;
        }
        popup.remove();
      };

      document.body.appendChild(popup);
    }
  };

  callSocket.onclose = function (e) {
    console.warn("Call socket closed unexpectedly. Reconnecting in 3s...", e.reason);
    reconnectTimeout = setTimeout(connectCallSocket, 3000);
  };

  callSocket.onerror = function (err) {
    console.error("Call socket error:", err);
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
      window.location.href = `/chat/doctor/thread/${threadId}/`;
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

function showChatNotification(data) {
  if (Notification.permission === "granted") {
    const notification = new Notification(`New message from ${data.sender_name}`, {
      body: data.preview || "New message...",
      icon: data.sender_avatar || "/static/images/icons/patient.png",
    });

    notification.onclick = function () {
      window.focus();
      window.location.href = `/chat/doctor/thread/${data.thread_id}/`;
    };
  }
}
