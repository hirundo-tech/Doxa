from flask import Flask, render_template_string, request, jsonify, Response, send_from_directory
from crawler import doxa_crawler
from ingest import run_ingest, DATA_DIR
from agent import make_chain
from langchain_core.messages import HumanMessage, AIMessage
import os, json, time
from pathlib import Path

app = Flask(__name__)

# Percorso per servire il logo dalla cartella principale
BASE_PATH = os.getcwd()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Doxa Elite</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root { --primary: #299AEA; --bg: #FFFFFF; --text: #1A1A1A; --gray: #F5F5F7; }
        
        body { font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); margin: 0; display: flex; flex-direction: column; align-items: center; overflow-x: hidden; }
        
        /* HEADER PERSISTENTE CON LOGO */
        .main-header { width: 100%; padding: 40px 0 20px 0; display: flex; justify-content: center; align-items: center; background: var(--bg); position: sticky; top: 0; z-index: 100; }
        .logo-container { width: 80px; height: 80px; display: flex; justify-content: center; align-items: center; }
        .logo-container img { width: 100%; height: 100%; object-fit: contain; transition: transform 0.3s ease; }
        .logo-container img:hover { transform: scale(1.05); }

        .container { width: 100%; max-width: 800px; padding: 0 20px 60px 20px; box-sizing: border-box; display: flex; flex-direction: column; }

        .fade { transition: opacity 0.5s ease, transform 0.5s ease; }
        .hidden { opacity: 0; transform: translateY(10px); pointer-events: none; }
        
        h1 { font-weight: 800; font-size: 3.2rem; letter-spacing: -2px; margin-bottom: 10px; text-align: center; }
        h2 { font-weight: 600; font-size: 1.5rem; line-height: 1.4; margin-bottom: 20px; text-align: center; }
        p.desc { color: #636366; font-size: 1.1rem; margin-bottom: 40px; text-align: center; }

        .input-group { display: flex; gap: 12px; width: 100%; align-items: flex-end; }
        
        input[type="text"], textarea { 
            flex: 1; padding: 18px; border: 1px solid #E5E5E7; border-radius: 14px; 
            font-size: 1rem; outline: none; background: var(--gray); font-family: inherit;
            resize: none; transition: background 0.2s;
        }
        textarea { min-height: 58px; max-height: 200px; overflow-y: auto; }

        .btn { background: var(--primary); color: white; border: none; padding: 18px 30px; border-radius: 14px; cursor: pointer; font-weight: 600; transition: 0.2s; height: 58px; }
        .btn:hover { background: #1E7BCA; transform: translateY(-2px); }

        #progress-area { display: none; margin-top: 40px; width: 100%; }
        .progress-container { background: var(--gray); height: 12px; border-radius: 20px; overflow: hidden; }
        .progress-fill { background: var(--primary); width: 0%; height: 100%; transition: width 0.8s cubic-bezier(0.34, 1.56, 0.64, 1); }

        #chat-section { display: none; flex-direction: column; height: 85vh; margin-top: -30px; width: 100%; }
        #chat-window { flex: 1; overflow-y: auto; padding: 20px 0; display: flex; flex-direction: column; gap: 20px; scroll-behavior: smooth; }
        .msg { padding: 16px 22px; border-radius: 18px; max-width: 85%; line-height: 1.6; font-size: 1rem; }
        .user { background: var(--primary); color: white; align-self: flex-end; border-bottom-right-radius: 4px; }
        .ai { background: var(--gray); color: var(--text); align-self: flex-start; border-bottom-left-radius: 4px; }

        .typing { display: none; align-self: flex-start; background: var(--gray); padding: 12px 20px; border-radius: 18px; gap: 5px; align-items: center; }
        .dot { width: 6px; height: 6px; background: #8E8E93; border-radius: 50%; animation: pulse 1.4s infinite; }
        .dot:nth-child(2) { animation-delay: 0.2s; }
        .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes pulse { 0%, 100% { opacity: 0.3; transform: scale(1); } 50% { opacity: 1; transform: scale(1.1); } }
    </style>
</head>
<body>
    <header class="main-header fade">
        <div class="logo-container">
            <img src="/logo.png" alt="Doxa Logo">
        </div>
    </header>

    <div class="container">
        <div id="intro" class="fade">
            <h1>Benvenuto su Doxa.</h1>
            <h2>Ciao, sono Doxa e sono il tuo Agente AI che semplifica la tua vita con documenti pubblici di ogni tipo.</h2>
            <p class="desc">Inserisci l'URL dei documenti da analizzare e farò il resto.</p>
            <div class="input-group">
                <input type="text" id="url-input" placeholder="Incolla l'URL da analizzare...">
                <button class="btn" onclick="startAnalysis()">ANALIZZA</button>
            </div>
        </div>

        <div id="progress-area" class="fade">
            <span id="status-label" style="font-weight:600; color:var(--primary); display:block; text-align:center; margin-bottom:15px;">Ricerca iniziata...</span>
            <div class="progress-container"><div id="fill" class="progress-fill"></div></div>
        </div>

        <div id="chat-section" class="fade">
            <div id="chat-window"></div>
            <div id="typing-indicator" class="typing">
                <div class="dot"></div><div class="dot"></div><div class="dot"></div>
            </div>
            <div class="input-group" style="padding-top:20px; border-top:1px solid #EEE;">
                <textarea id="user-msg" placeholder="Chiedi a Doxa..." rows="1" oninput="autoResize(this)"></textarea>
                <button class="btn" onclick="send()">INVIA</button>
            </div>
        </div>
    </div>

    <script>
    let chatHistory = [];

    async function startAnalysis() {
        const url = document.getElementById('url-input').value;
        if(!url) return;

        const intro = document.getElementById('intro');
        intro.style.maxWidth = intro.offsetWidth + 'px'; 
        intro.classList.add('hidden');
        
        setTimeout(() => {
            intro.style.display = 'none';
            document.getElementById('progress-area').style.display = 'block';
        }, 500);

        const eventSource = new EventSource(`/stream?url=${encodeURIComponent(url)}`);
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            document.getElementById('fill').style.width = data.progress + "%";
            document.getElementById('status-label').innerText = data.status;
            if(data.progress === 100) {
                eventSource.close();
                setTimeout(() => {
                    document.getElementById('progress-area').style.display = 'none';
                    initChat(data.title);
                }, 800);
            }
        };
    }

    function autoResize(el) {
        el.style.height = 'auto';
        el.style.height = (el.scrollHeight) + 'px';
    }

    document.getElementById('user-msg')?.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    });

    function initChat(title) {
        document.getElementById('chat-section').style.display = 'flex';
        const welcome = `Ciao, eccomi qui. Ho analizzato i documenti di: **${title}**.`;
        addMessage(welcome, 'ai');
        chatHistory.push({role: "ai", content: welcome});
    }

    async function send() {
        const input = document.getElementById('user-msg');
        const text = input.value.trim();
        if(!text) return;

        input.value = "";
        input.style.height = 'auto'; 
        addMessage(text, 'user');
        
        document.getElementById('typing-indicator').style.display = 'flex';
        const win = document.getElementById('chat-window');
        win.scrollTop = win.scrollHeight;

        const res = await fetch('/chat', {
            method:'POST', 
            headers:{'Content-Type':'application/json'}, 
            body:JSON.stringify({message: text, history: chatHistory})
        });
        
        chatHistory.push({role: "human", content: text});
        const data = await res.json();
        
        document.getElementById('typing-indicator').style.display = 'none';
        addMessage(data.response, 'ai');
        chatHistory.push({role: "ai", content: data.response});
    }

    function addMessage(content, type) {
        const win = document.getElementById('chat-window');
        const div = document.createElement('div');
        div.className = `msg ${type} fade`;
        div.innerHTML = type === 'ai' ? marked.parse(content) : content;
        win.appendChild(div);
        win.scrollTop = win.scrollHeight;
    }
    </script>
</body>
</html>
"""

# Rotta per servire il logo dalla root
@app.route('/logo.png')
def serve_logo():
    return send_from_directory(BASE_PATH, 'logo.png')

@app.route('/stream')
def stream():
    url = request.args.get('url')
    def generate():
        yield f"data: {json.dumps({'progress': 5, 'status': '🌐 Avvio ricerca...'})}\n\n"
        data = doxa_crawler(url)
        files = [f for f in os.listdir("DATA") if f.endswith(".pdf")]
        for i, f in enumerate(files):
            prog = 10 + int((i + 1) / len(files) * 40)
            yield f"data: {json.dumps({'progress': prog, 'status': f'📥 Scaricato: {f}'})}\n\n"
            time.sleep(0.1)
        
        status_msg = "🧠 Addestrando l'AI..."
        yield f"data: {json.dumps({'progress': 75, 'status': status_msg})}\n\n"
        run_ingest()
        yield f"data: {json.dumps({'progress': 100, 'status': '✅ Completato!', 'title': data.get('titolo', 'Bene Analizzato')})}\n\n"
    return Response(generate(), mimetype='text/event-stream')

@app.route('/chat', methods=['POST'])
def chat():
    msg = request.json.get('message')
    history_raw = request.json.get('history', [])
    formatted_history = [HumanMessage(content=m['content']) if m['role'] == "human" else AIMessage(content=m['content']) for m in history_raw]
    chain = make_chain()
    response = chain.invoke({"question": msg, "chat_history": formatted_history})
    return jsonify({"response": response})

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
