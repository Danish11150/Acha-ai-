from gevent import monkey
monkey.patch_all()

import os, json, requests, threading, urllib.parse, time
from flask import Flask, render_template_string, jsonify, request
from datetime import datetime

app = Flask(__name__)

# =============================
# ENVIRONMENT VARIABLES
# =============================
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
BLOGGER_REFRESH_TOKEN = os.environ.get("BLOGGER_REFRESH_TOKEN", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
BLOG_ID = os.environ.get("BLOG_ID", "")

# Global state
company_state = {"running": False, "logs": [], "results": {}, "status": "standby"}

def log(agent, message, status="working"):
    company_state["logs"].append({"agent": agent, "message": message, "status": status, "time": datetime.now().strftime("%H:%M:%S")})

def call_deepseek(system_prompt, user_message, max_tokens=2000, retries=2):
    model = "deepseek-v4-flash"
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }
    for attempt in range(retries):
        try:
            resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=body, timeout=60)
            data = resp.json()
            if "error" in data:
                raise Exception(data["error"].get("message", "Unknown API error"))
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == retries - 1:
                return f"Fallback: {str(e)}"
            time.sleep(2)
    return "Fallback: AI unavailable"

def ceo_agent():
    return call_deepseek(
        "You are Aria, CEO of Neo Vision Hub. Communicate in Roman Urdu. Give daily task plan in 3 short points.",
        "Aaj ke liye team ko kya plan dena chahiye? Roman Urdu mein 3 points.",
        max_tokens=500
    )

def trend_hunter_agent():
    return call_deepseek(
        "You are a Trend Hunter. Return ONLY one trending topic in AI, Tech, Trading, or Gaming. No extra words.",
        "Give me the most trending topic right now.",
        max_tokens=50
    )

def content_writer_agent(trend):
    result = call_deepseek(
        "You are a professional blog writer. Write an SEO-optimized article in English (600-800 words). Return ONLY valid JSON with keys: title, content (HTML format with <p> tags), excerpt (short summary).",
        f"Write a detailed, engaging blog post about: {trend}",
        max_tokens=2000
    )
    try:
        clean = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except:
        return {
            "title": f"Latest Trends: {trend}",
            "content": f"<p>{result[:600]}...</p>",
            "excerpt": result[:150]
        }

def seo_expert_agent(title, content):
    result = call_deepseek(
        "You are an SEO Expert. Return ONLY valid JSON with: meta_title (max 60 chars), meta_description (max 160 chars), keywords (list of 5), tags (list of 5).",
        f"Optimize SEO for:\nTitle: {title}\nContent preview: {content[:300]}",
        max_tokens=500
    )
    try:
        clean = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except:
        return {
            "meta_title": title[:60],
            "meta_description": content[:160],
            "keywords": ["technology", "AI", "trends", "2025", "innovation"],
            "tags": ["AI", "Tech", "Trends", "Blog", "News"]
        }

def image_agent(title):
    prompt = f"professional blog header image for article about {title}, modern digital art, high quality"
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true"

def editor_agent(post, seo, image_url):
    post["image_url"] = image_url
    post["meta_title"] = seo.get("meta_title", post["title"])
    post["meta_description"] = seo.get("meta_description", post.get("excerpt", ""))
    post["tags"] = seo.get("tags", [])
    post["keywords"] = seo.get("keywords", [])
    return post

def social_media_agent(title):
    result = call_deepseek(
        "You are a Social Media Manager. Return ONLY valid JSON with: instagram, twitter, linkedin captions (English, under 200 chars each).",
        f"Create engaging captions for: {title}",
        max_tokens=400
    )
    try:
        clean = result.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except:
        return {
            "instagram": f"🚀 New post: {title}\nLink in bio! #AI #Tech",
            "twitter": f"Just published: {title} #AI #Tech",
            "linkedin": f"Check out our latest article: {title}"
        }

def marketing_agent(title):
    return call_deepseek(
        "You are a Marketing Agent. Give 3 practical promotional tips in Roman Urdu.",
        f"Is blog post ko promote karne ke liye 3 strategies batayein: {title}",
        max_tokens=400
    )

def get_fresh_token():
    if not all([BLOGGER_REFRESH_TOKEN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET]):
        return None
    try:
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "refresh_token": BLOGGER_REFRESH_TOKEN,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "grant_type": "refresh_token"
        }, timeout=30)
        return resp.json().get("access_token")
    except:
        return None

def publish_to_blogger(post, image_url):
    if not BLOG_ID or not BLOGGER_REFRESH_TOKEN:
        return {"status": "skipped", "message": "Blogger credentials not set. Publish skipped."}
    token = get_fresh_token()
    if not token:
        return {"status": "error", "message": "Failed to authenticate with Google."}
    try:
        content_with_image = f'<img src="{image_url}" alt="{post["title"]}" style="width:100%; margin-bottom:20px; border-radius:12px;"/><br/>{post["content"]}'
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {
            "kind": "blogger#post",
            "title": post["title"],
            "content": content_with_image,
            "labels": post.get("tags", [])
        }
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return {"status": "published", "url": data.get("url"), "title": data.get("title")}
        return {"status": "error", "message": resp.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_company():
    company_state["running"] = True
    company_state["logs"] = []
    company_state["results"] = {}
    company_state["status"] = "running"
    try:
        log("CEO", "Planning day tasks...")
        ceo_plan = ceo_agent()
        company_state["results"]["ceo"] = ceo_plan
        log("CEO", "Plan ready", "done")

        log("Trend Hunter", "Searching trending topics...")
        trend = trend_hunter_agent()
        company_state["results"]["trend"] = trend
        log("Trend Hunter", f"Topic: {trend}", "done")

        log("Content Writer", "Writing blog post...")
        post = content_writer_agent(trend)
        company_state["results"]["post"] = post
        log("Content Writer", "Post written", "done")

        log("SEO Expert", "Optimizing SEO...")
        seo = seo_expert_agent(post["title"], post["content"])
        company_state["results"]["seo"] = seo
        log("SEO Expert", "SEO optimized", "done")

        log("Image Agent", "Generating image...")
        image_url = image_agent(post["title"])
        company_state["results"]["image"] = image_url
        log("Image Agent", "Image ready", "done")

        log("Editor", "Reviewing and finalizing...")
        final_post = editor_agent(post, seo, image_url)
        company_state["results"]["final_post"] = final_post
        log("Editor", "Post approved", "done")

        log("Social Media", "Creating captions...")
        captions = social_media_agent(post["title"])
        company_state["results"]["captions"] = captions
        log("Social Media", "Captions ready", "done")

        log("Marketing", "Planning promotion...")
        marketing = marketing_agent(post["title"])
        company_state["results"]["marketing"] = marketing
        log("Marketing", "Strategy ready", "done")

        log("CEO", "Publishing to Blogger...")
        pub = publish_to_blogger(final_post, image_url)
        company_state["results"]["published"] = pub
        log("CEO", f"Publish status: {pub['status']}", "done")

        company_state["status"] = "completed"
        log("System", "All tasks completed successfully!", "done")
    except Exception as e:
        log("System", f"Error: {str(e)}", "error")
        company_state["status"] = "error"
    finally:
        company_state["running"] = False

# =============================
# PROFESSIONAL DASHBOARD (Modern UI)
# =============================
DASHBOARD = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neo Vision Hub | AI Agent Company</title>
    <meta name="description" content="AI-powered blog content generation for Neo Vision Hub">
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0B0F1E 0%, #0A0F1A 100%);
            color: #E8EDFF;
            min-height: 100vh;
        }
        .glass-card {
            background: rgba(18, 24, 38, 0.7);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(99, 102, 241, 0.2);
            border-radius: 24px;
        }
        .gradient-text {
            background: linear-gradient(135deg, #818CF8, #C084FC);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
        }
        .btn-primary {
            background: linear-gradient(135deg, #6366F1, #8B5CF6);
            border: none;
            padding: 12px 32px;
            border-radius: 40px;
            font-weight: 600;
            color: white;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(99,102,241,0.4);
        }
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .agent-card {
            background: rgba(15, 20, 30, 0.6);
            border: 1px solid rgba(99, 102, 241, 0.15);
            border-radius: 20px;
            transition: all 0.3s;
        }
        .agent-card:hover {
            border-color: rgba(99, 102, 241, 0.4);
            transform: translateY(-2px);
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
        }
        .status-working { background: #F59E0B; box-shadow: 0 0 8px #F59E0B; }
        .status-done { background: #10B981; box-shadow: 0 0 8px #10B981; }
        .status-error { background: #EF4444; box-shadow: 0 0 8px #EF4444; }
        .status-standby { background: #6B7280; }
        .pulse {
            animation: pulse 1.5s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        .log-line {
            font-size: 12px;
            color: #9CA3AF;
            border-left: 2px solid #6366F1;
            padding-left: 12px;
            margin-bottom: 8px;
        }
        .result-section {
            background: #0F1420;
            border-radius: 20px;
            padding: 20px;
            margin-top: 24px;
        }
        .tag {
            background: rgba(99, 102, 241, 0.2);
            padding: 4px 12px;
            border-radius: 30px;
            font-size: 12px;
            display: inline-block;
            margin: 4px;
        }
        @media (max-width: 768px) {
            .grid-cols-2 { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="max-w-6xl mx-auto px-4 py-8">
        <!-- Header -->
        <div class="flex justify-between items-center mb-8">
            <div>
                <h1 class="text-3xl font-bold"><span class="gradient-text">Neo Vision Hub</span> 🤖</h1>
                <p class="text-gray-400 mt-1">AI Agent Company — 8 Expert Agents</p>
            </div>
            <div class="glass-card px-6 py-3 rounded-full text-sm">
                <span id="mainStatusText">Standby</span>
                <span class="status-dot ml-2" id="mainStatusDot"></span>
            </div>
        </div>

        <!-- Run Button -->
        <div class="text-center my-8">
            <button id="runBtn" class="btn-primary text-lg px-10 py-3" onclick="startRun()">▶ Run AI Agents</button>
            <p class="text-gray-500 text-sm mt-3">Generates blog post, SEO, social media, and publishes to Blogger</p>
        </div>

        <!-- Agents Grid -->
        <div class="grid md:grid-cols-2 gap-5 mb-10">
            <!-- CEO -->
            <div class="agent-card p-5 col-span-full md:col-span-2" id="card-ceo">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-12 h-12 rounded-full bg-indigo-500/20 flex items-center justify-center text-2xl">👔</div>
                        <div><h3 class="font-semibold">Aria</h3><p class="text-xs text-gray-400">CEO</p></div>
                    </div>
                    <div><span class="text-xs px-3 py-1 rounded-full bg-gray-800" id="chip-ceo">Standby</span></div>
                </div>
                <div class="mt-3 text-sm text-gray-400" id="log-ceo">Waiting...</div>
            </div>
            <!-- Other agents -->
            <div class="agent-card p-4" id="card-trend"><div class="flex justify-between"><div><span class="text-xl">🔍</span> <span class="font-medium ml-2">Zain</span><div class="text-xs text-gray-400">Trend Hunter</div></div><span class="text-xs px-2 py-1 rounded-full bg-gray-800" id="chip-trend">Standby</span></div><div class="mt-2 text-sm text-gray-400" id="log-trend">-</div></div>
            <div class="agent-card p-4" id="card-writer"><div class="flex justify-between"><div><span class="text-xl">✍️</span> <span class="font-medium ml-2">Sara</span><div class="text-xs text-gray-400">Content Writer</div></div><span class="text-xs px-2 py-1 rounded-full bg-gray-800" id="chip-writer">Standby</span></div><div class="mt-2 text-sm text-gray-400" id="log-writer">-</div></div>
            <div class="agent-card p-4" id="card-seo"><div class="flex justify-between"><div><span class="text-xl">🎯</span> <span class="font-medium ml-2">Rayan</span><div class="text-xs text-gray-400">SEO Expert</div></div><span class="text-xs px-2 py-1 rounded-full bg-gray-800" id="chip-seo">Standby</span></div><div class="mt-2 text-sm text-gray-400" id="log-seo">-</div></div>
            <div class="agent-card p-4" id="card-image"><div class="flex justify-between"><div><span class="text-xl">🎨</span> <span class="font-medium ml-2">Pixel</span><div class="text-xs text-gray-400">Image Agent</div></div><span class="text-xs px-2 py-1 rounded-full bg-gray-800" id="chip-image">Standby</span></div><div class="mt-2 text-sm text-gray-400" id="log-image">-</div></div>
            <div class="agent-card p-4" id="card-editor"><div class="flex justify-between"><div><span class="text-xl">✅</span> <span class="font-medium ml-2">Alex</span><div class="text-xs text-gray-400">Editor</div></div><span class="text-xs px-2 py-1 rounded-full bg-gray-800" id="chip-editor">Standby</span></div><div class="mt-2 text-sm text-gray-400" id="log-editor">-</div></div>
            <div class="agent-card p-4" id="card-social"><div class="flex justify-between"><div><span class="text-xl">📱</span> <span class="font-medium ml-2">Mia</span><div class="text-xs text-gray-400">Social Media</div></div><span class="text-xs px-2 py-1 rounded-full bg-gray-800" id="chip-social">Standby</span></div><div class="mt-2 text-sm text-gray-400" id="log-social">-</div></div>
            <div class="agent-card p-4" id="card-marketing"><div class="flex justify-between"><div><span class="text-xl">📢</span> <span class="font-medium ml-2">Omar</span><div class="text-xs text-gray-400">Marketing</div></div><span class="text-xs px-2 py-1 rounded-full bg-gray-800" id="chip-marketing">Standby</span></div><div class="mt-2 text-sm text-gray-400" id="log-marketing">-</div></div>
        </div>

        <!-- Results Area -->
        <div id="results" class="result-section hidden"></div>
    </div>

    <script>
        let pollInterval = null;
        let lastLogCount = 0;
        const agentMap = {"CEO":"ceo","Trend Hunter":"trend","Content Writer":"writer","SEO Expert":"seo","Image Agent":"image","Editor":"editor","Social Media":"social","Marketing":"marketing","System":"ceo"};

        function setStatus(agentId, status, text, logMsg) {
            const chip = document.getElementById(`chip-${agentId}`);
            const logEl = document.getElementById(`log-${agentId}`);
            if (chip) {
                chip.innerText = text;
                chip.className = `text-xs px-2 py-1 rounded-full ${status === 'working' ? 'bg-yellow-500/20 text-yellow-300' : status === 'done' ? 'bg-green-500/20 text-green-300' : status === 'error' ? 'bg-red-500/20 text-red-300' : 'bg-gray-800 text-gray-400'}`;
            }
            if (logEl && logMsg) logEl.innerText = logMsg;
        }

        function setWorking(agentId) {
            setStatus(agentId, 'working', 'Working...', 'Processing...');
        }

        async function startRun() {
            const btn = document.getElementById('runBtn');
            btn.disabled = true;
            btn.innerText = '⏳ Running Agents...';
            document.getElementById('mainStatusText').innerText = 'Running';
            document.getElementById('mainStatusDot').className = 'status-dot status-working pulse';
            document.getElementById('results').innerHTML = '';
            lastLogCount = 0;
            // Reset all agents
            ['ceo','trend','writer','seo','image','editor','social','marketing'].forEach(id => {
                setStatus(id, 'standby', 'Standby', 'Waiting...');
            });
            const response = await fetch('/run', {method: 'POST'});
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(pollStatus, 1500);
        }

        async function pollStatus() {
            try {
                const res = await fetch('/status');
                const data = await res.json();
                const logs = data.logs || [];
                for (let i = lastLogCount; i < logs.length; i++) {
                    const log = logs[i];
                    const agentId = agentMap[log.agent] || 'ceo';
                    if (log.status === 'working') setWorking(agentId);
                    else if (log.status === 'done') setStatus(agentId, 'done', 'Done ✓', log.message);
                    else if (log.status === 'error') setStatus(agentId, 'error', 'Error', log.message);
                }
                lastLogCount = logs.length;
         
