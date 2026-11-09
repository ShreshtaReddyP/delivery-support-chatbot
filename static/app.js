// Frontend Chat Client for Delivery Support Chatbot

const messagesContainer = document.getElementById("messagesContainer");
const chatForm = document.getElementById("chatForm");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

let conversationHistory = [];

// Initialize Chat
document.addEventListener("DOMContentLoaded", () => {
  renderInitialMessage();
  setupEventListeners();
  checkAgentStatus();
});

async function checkAgentStatus() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.querySelector(".brand .badge");
    if (badge) {
      if (data.is_live) {
        badge.textContent = `🟢 ${data.model} Active`;
        badge.className = "badge online";
        badge.title = "Live Google Gemini AI active with native tool calling";
      } else {
        badge.textContent = "🟡 Offline Preview Mode";
        badge.className = "badge preview";
        badge.title = "Add GEMINI_API_KEY in .env to activate live Gemini AI";
      }
    }
  } catch (e) {
    console.debug("Status check skipped", e);
  }
}

function setupEventListeners() {
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSubmit();
  });

  clearBtn.addEventListener("click", () => {
    conversationHistory = [];
    messagesContainer.innerHTML = "";
    renderInitialMessage();
  });
}

function renderInitialMessage() {
  const welcomeText = 
    `👋 Hello! I am your **SwiftDrop Delivery Assistant**.\n\n` +
    `I can help you track active deliveries, update drop-off instructions, issue instant refunds for missing or damaged food, and answer any delivery policy questions.\n\n` +
    `How can I help you today?`;
  
  appendMessage("assistant", welcomeText);
}

async function handleSubmit() {
  const text = userInput.value.trim();
  if (!text) return;

  // Append user message to UI
  appendMessage("user", text);
  userInput.value = "";
  userInput.disabled = true;
  sendBtn.disabled = true;

  // Render typing indicator
  const typingId = appendTypingIndicator();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: conversationHistory,
        customer_id: "CUST-8801"
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to reach chat assistant.`);
    }

    const data = await response.json();
    removeMessageElement(typingId);

    // Update conversation history
    conversationHistory.push({ role: "user", content: text });
    conversationHistory.push({ role: "model", content: data.response });

    // Append Assistant response + executed tool pills
    appendMessage("assistant", data.response, data.tool_calls);

  } catch (err) {
    removeMessageElement(typingId);
    appendMessage("assistant", `⚠️ **Connection Error:** Could not contact server (${err.message}). Please check that the server is running.`);
  } finally {
    userInput.disabled = false;
    sendBtn.disabled = false;
    userInput.focus();
  }
}

function appendMessage(role, text, toolCalls = []) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.innerHTML = role === "user" ? "👤" : "🛵";

  const bubbleWrap = document.createElement("div");
  bubbleWrap.className = "bubble-wrap";

  // If tools were called, display tool chips
  if (toolCalls && toolCalls.length > 0) {
    toolCalls.forEach((tool, idx) => {
      const toolPill = document.createElement("div");
      toolPill.className = "tool-pill";
      toolPill.innerHTML = `<span>⚙️ Executed: <strong>${escapeHtml(tool.tool_name)}</strong></span>`;
      
      const toolRaw = document.createElement("pre");
      toolRaw.className = "tool-details-raw";
      toolRaw.textContent = JSON.stringify({ arguments: tool.arguments, result: tool.result }, null, 2);
      
      toolPill.onclick = () => {
        toolRaw.style.display = toolRaw.style.display === "block" ? "none" : "block";
      };

      bubbleWrap.appendChild(toolPill);
      bubbleWrap.appendChild(toolRaw);
    });
  }

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = formatMarkdown(text);
  bubbleWrap.appendChild(bubble);

  row.appendChild(avatar);
  row.appendChild(bubbleWrap);

  messagesContainer.appendChild(row);
  scrollToBottom();
}

function appendTypingIndicator() {
  const id = "typing-" + Date.now();
  const row = document.createElement("div");
  row.id = id;
  row.className = "message-row assistant";
  row.innerHTML = `
    <div class="avatar">🛵</div>
    <div class="bubble-wrap">
      <div class="bubble">
        <div class="typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  `;
  messagesContainer.appendChild(row);
  scrollToBottom();
  return id;
}

function removeMessageElement(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollToBottom() {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// Global helpers for user interactions
window.sendQuickPrompt = function(promptText) {
  userInput.value = promptText;
  handleSubmit();
};

window.askAboutOrder = function(orderId) {
  userInput.value = `Where is my order ${orderId}? Can you give me the latest status?`;
  handleSubmit();
};

// Simple Markdown Formatter
function formatMarkdown(text) {
  if (!text) return "";
  
  let formatted = escapeHtml(text);
  
  // Bold: **text**
  formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  
  // Italic: *text*
  formatted = formatted.replace(/\*(.*?)\*/g, "<em>$1</em>");
  
  // Inline code: `code`
  formatted = formatted.replace(/`([^`]+)`/g, "<code>$1</code>");
  
  // Bullet lists (- item)
  const lines = formatted.split("\n");
  let inList = false;
  let result = [];

  for (let line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      if (!inList) {
        result.push("<ul>");
        inList = true;
      }
      result.push(`<li>${trimmed.substring(2)}</li>`);
    } else {
      if (inList) {
        result.push("</ul>");
        inList = false;
      }
      if (trimmed.length > 0) {
        result.push(`<p>${line}</p>`);
      }
    }
  }
  if (inList) result.push("</ul>");

  return result.join("");
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
