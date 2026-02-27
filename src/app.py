import time
import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from src.agents import ToolEnabledAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("multi-agent-pcaplog.app")

app = FastAPI(title="Collaborative Multi-Agent Framework — Security Analysis Chat")

agent = ToolEnabledAgent()

class Query(BaseModel):
    text: str

CHAT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Analysis Chat</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f1419;
            --bg-card: #1a2332;
            --bg-input: #252d3a;
            --accent: #3b82f6;
            --accent-hover: #2563eb;
            --text-primary: #e7edf3;
            --text-muted: #8b9aaa;
            --user-msg: #1e3a5f;
            --agent-msg: #1e293b;
            --border: #2d3748;
        }
        * { box-sizing: border-box; }
        body {
            font-family: 'Outfit', -apple-system, sans-serif;
            background: var(--bg-dark);
            color: var(--text-primary);
            min-height: 100vh;
        }
        .chat-container {
            max-width: 760px;
            margin: 0 auto;
            padding: 1.5rem;
            height: calc(100vh - 120px);
            display: flex;
            flex-direction: column;
        }
        .chat-header {
            text-align: center;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        .chat-header h1 {
            font-size: 1.35rem;
            font-weight: 600;
            color: var(--text-primary);
        }
        .chat-header p {
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        #chat-box {
            flex: 1;
            overflow-y: auto;
            padding: 1rem 0;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }
        .msg {
            max-width: 88%;
            padding: 0.9rem 1.1rem;
            border-radius: 14px;
            line-height: 1.5;
            animation: fadeIn 0.25s ease;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        .msg-user {
            align-self: flex-end;
            background: var(--accent);
            color: white;
        }
        .msg-agent {
            align-self: flex-start;
            background: var(--bg-card);
            border: 1px solid var(--border);
        }
        .msg-agent .log-section {
            margin-top: 0.75rem;
            padding-top: 0.75rem;
            border-top: 1px solid var(--border);
        }
        .log-entry {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.75rem;
            color: var(--text-muted);
            padding: 0.25rem 0;
        }
        .msg-agent .answer-content {
            font-size: 0.95rem;
        }
        .msg-agent .answer-content p { margin: 0.5em 0; }
        .msg-agent .answer-content strong { color: var(--accent); }
        .input-row {
            display: flex;
            gap: 0.5rem;
            margin-top: auto;
            padding-top: 1rem;
        }
        #user-input {
            flex: 1;
            background: var(--bg-input);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.75rem 1rem;
            border-radius: 10px;
            font-size: 0.95rem;
        }
        #user-input::placeholder { color: var(--text-muted); }
        #user-input:focus {
            outline: none;
            border-color: var(--accent);
        }
        .btn-send {
            background: var(--accent);
            color: white;
            border: none;
            padding: 0.75rem 1.25rem;
            border-radius: 10px;
            font-weight: 500;
            cursor: pointer;
        }
        .btn-send:hover { background: var(--accent-hover); }
        .btn-send:disabled { opacity: 0.6; cursor: not-allowed; }
        .loading-dots {
            display: inline-flex;
            gap: 4px;
            padding: 0.5rem 0;
        }
        .loading-dots span {
            width: 6px;
            height: 6px;
            background: var(--text-muted);
            border-radius: 50%;
            animation: bounce 1.2s infinite ease-in-out;
        }
        .loading-dots span:nth-child(2) { animation-delay: 0.15s; }
        .loading-dots span:nth-child(3) { animation-delay: 0.3s; }
        @keyframes bounce { 0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>Security Analysis Chat</h1>
            <p>Request traffic analysis by IP address. Multi-agents analyze packets and logs, and an LLM generates answers.</p>
        </div>
        <div id="chat-box"></div>
        <div class="input-row">
            <input type="text" id="user-input" placeholder="e.g., Analyze traffic for 192.168.10.50" autocomplete="off">
            <button class="btn-send" id="btn-send">Send</button>
        </div>
    </div>
    <script>
        const box = document.getElementById('chat-box');
        const input = document.getElementById('user-input');
        const btn = document.getElementById('btn-send');

        function escapeHtml(s) {
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }

        function renderMarkdown(text) {
            const raw = text || '';
            if (typeof marked !== 'undefined') {
                try {
                    marked.setOptions({ breaks: true });
                    return (marked.parse || marked)(raw);
                } catch (_) {}
            }
            return escapeHtml(raw).replace(/\\n/g, '<br>');
        }

        function addPlaceholder() {
            const el = document.createElement('div');
            el.className = 'msg msg-agent';
            el.innerHTML = '<div class="loading-dots"><span></span><span></span><span></span></div>';
            el.dataset.placeholder = '1';
            box.appendChild(el);
            box.scrollTop = box.scrollHeight;
            return el;
        }

        async function sendQuery() {
            const text = input.value.trim();
            if (!text) return;

            box.querySelectorAll('[data-placeholder]').forEach(e => e.remove());
            box.innerHTML += `<div class="msg msg-user">${escapeHtml(text)}</div>`;
            input.value = '';
            btn.disabled = true;

            const placeholder = addPlaceholder();

            try {
                const res = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: text })
                });
                const data = await res.json();

                let logHtml = '';
                if (data.execution_log && data.execution_log.length) {
                    logHtml = '<div class="log-section"><div class="log-entry">' + 
                        data.execution_log.map(l => escapeHtml(l)).join('</div><div class="log-entry">') + '</div></div>';
                }
                const answerHtml = '<div class="answer-content">' + renderMarkdown(data.answer || 'Failed to generate a response.') + '</div>';

                placeholder.removeAttribute('data-placeholder');
                placeholder.innerHTML = logHtml + answerHtml;
            } catch (err) {
                placeholder.removeAttribute('data-placeholder');
                placeholder.innerHTML = '<div class="answer-content" style="color:#ef4444;">Error: ' + escapeHtml(err.message) + '</div>';
            }
            btn.disabled = false;
            box.scrollTop = box.scrollHeight;
        }

        btn.addEventListener('click', sendQuery);
        input.addEventListener('keypress', e => { if (e.key === 'Enter') sendQuery(); });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    logger.info("GET / - Index page requested")
    return CHAT_HTML

@app.post("/ask")
async def ask_agent(query: Query):
    logger.info("POST /ask - Query: %r", query.text[:100] + ("..." if len(query.text) > 100 else ""))
    t0 = time.perf_counter()
    try:
        result = await agent.ask(query.text)
        elapsed = time.perf_counter() - t0
        logger.info("POST /ask - Completed in %.2fs", elapsed)
        return result
        
    except Exception as e:
        logger.exception("POST /ask - Error: %s", e)
        raise

if __name__ == "__main__":
    logger.info("Starting web server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
