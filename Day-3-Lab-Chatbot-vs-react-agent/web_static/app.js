let sessionId = localStorage.getItem("session_id") || "";

const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("composer");
const inputEl = document.getElementById("input");
const sendEl = document.getElementById("send");
const restartEl = document.getElementById("restart");

function addMessage(text, who) {
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  div.textContent = text;
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

addMessage("Gợi ý: bạn có thể nói “Tôi muốn đặt bàn cho 4 người tối nay ở Riverside lúc 19:00”.", "meta");

async function sendMessage(message) {
  const payload = { message, session_id: sessionId || null };

  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `HTTP ${res.status}`);
  }

  const data = await res.json();
  sessionId = data.session_id;
  localStorage.setItem("session_id", sessionId);
  return data.reply;
}

async function resetSessionOnServer() {
  const sid = sessionId || localStorage.getItem("session_id") || "";
  if (!sid) return;
  try {
    await fetch("/api/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sid }),
    });
  } catch {
    // ignore reset errors
  }
}

restartEl?.addEventListener("click", async () => {
  await resetSessionOnServer();
  sessionId = "";
  localStorage.removeItem("session_id");
  window.location.reload();
});

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;

  inputEl.value = "";
  addMessage(message, "user");

  sendEl.disabled = true;
  inputEl.disabled = true;
  const thinkingId = crypto.randomUUID();
  addMessage("Đang xử lý...", "meta");

  try {
    const reply = await sendMessage(message);
    addMessage(reply, "bot");
  } catch (err) {
    addMessage(`Lỗi: ${err?.message || String(err)}`, "meta");
  } finally {
    sendEl.disabled = false;
    inputEl.disabled = false;
    inputEl.focus();
  }
});

