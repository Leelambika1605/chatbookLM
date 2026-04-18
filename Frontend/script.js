// =============================
// 🔥 IMPORTANT: BACKEND URL
// =============================
const API_URL = "https://chatbooklm-r8qd.onrender.com";

// -----------------------------
// Smooth scroll to bottom
// -----------------------------
function scrollToBottom() {
  const chatBox = document.getElementById("chatBox");
  chatBox.scrollTop = chatBox.scrollHeight;
}

// -----------------------------
// Typing effect (AI response)
// -----------------------------
function typeText(element, text, speed = 20) {
  element.innerText = "";
  let i = 0;

  function typing() {
    if (i < text.length) {
      element.innerText += text[i];
      i++;
      scrollToBottom();
      setTimeout(typing, speed);
    }
  }

  typing();
}

// -----------------------------
// Loading animation (...)
// -----------------------------
function animateDots(element) {
  let dots = "";
  return setInterval(() => {
    dots = dots.length < 3 ? dots + "." : "";
    element.innerText = "Thinking" + dots;
  }, 400);
}

// -----------------------------
// File upload handler
// -----------------------------
async function handleFile() {
  const fileInput = document.getElementById("fileInput");
  const fileList = document.getElementById("fileList");

  if (!fileInput.files.length) return;

  const file = fileInput.files[0];

  // Show file in sidebar
  const li = document.createElement("li");
  li.innerText = file.name;
  fileList.appendChild(li);

  // Send to backend
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_URL}/upload`, {
      method: "POST",
      body: formData
    });

    const data = await res.json();

    if (!res.ok) throw new Error(data.error || "Upload failed");

    console.log("Upload success:", data);

  } catch (err) {
    alert("❌ File upload failed");
    console.error(err);
  }
}

// -----------------------------
// Send message to AI
// -----------------------------
async function sendMessage() {
  const input = document.getElementById("question");
  const chatBox = document.getElementById("chatBox");

  const text = input.value.trim();
  if (!text) return;

  // USER MESSAGE
  const userMsg = document.createElement("div");
  userMsg.className = "message user";
  userMsg.innerText = text;
  chatBox.appendChild(userMsg);

  input.value = "";
  scrollToBottom();

  // BOT MESSAGE PLACEHOLDER
  const botMsg = document.createElement("div");
  botMsg.className = "message bot";
  chatBox.appendChild(botMsg);

  const loader = animateDots(botMsg);

  try {
    const res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ question: text })
    });

    const data = await res.json();

    clearInterval(loader);

    if (!res.ok) throw new Error(data.error || "Server error");

    // AI response typing effect
    typeText(botMsg, data.answer || "No response");

  } catch (err) {
    clearInterval(loader);
    botMsg.innerText = "❌ Error: Cannot connect to server";
    console.error(err);
  }

  scrollToBottom();
}

// -----------------------------
// New chat reset
// -----------------------------
function newChat() {
  document.getElementById("chatBox").innerHTML = `
    <div class="message bot">
      👋 New chat started. Upload a document and ask questions.
    </div>
  `;
}

// -----------------------------
// Enter key support
// -----------------------------
document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("question");

  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });
});