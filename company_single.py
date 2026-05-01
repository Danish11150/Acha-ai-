import os, json, requests, threading, urllib.parse
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# =============================
# APNI KEYS YAHAN DAALO
# =============================
DEEPSEEK_API_KEY = "sk-60389d1e6ba446d7920dd011947db7f5"
CLIENT_ID        = "aapka_google_client_id"
CLIENT_SECRET    = "aapka_google_client_secret"
REFRESH_TOKEN    = "aapka_refresh_token"
BLOG_ID          = "21948522432663252"
# =============================

company_state = {"running": False, "logs": [], "results": {}, "status": "standby"}

def log(agent, message, status="working"):
    company_state["logs"].append({"agent": agent, "message": message, "status": status})

def get_fresh_blogger_token():
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": REFRESH_TOKEN,
        "grant_type":    "refresh_token"
    }, timeout=15)
    result = resp.json()
    if "access_token" in result:
        return result["access_token"]
    raise Exception(f"Token refresh failed: {result}")

def call_deepseek(system_prompt, user_message, max_tokens=2000):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    body = {"model": "deepseek-chat", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}], "max_tokens": max_tokens, "temperature": 0.7}
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=body, timeout=60)
    return resp.json()["choices"][0]["message"]["content"]

def ceo_agent():
    return call_deepseek("You are Aria, CEO of Neo Vision Hub. Communicate in Roman Urdu. Create daily task plan.", "Aaj ke liye team ko kya plan dena chahiye? 3 points mein Roman Urdu mein batao.", 500)

def trend_hunter_agent():
    return call_deepseek("You are a Trend Hunter. Find ONE trending topic in AI or Tech.", "Find the most trending topic right now in AI or Tech.", 300)

def content_writer_agent(trend):
    result = call_deepseek("You are a blog Content Writer. Write SEO posts in English. Return ONLY valid JSON with keys: title, content (HTML), excerpt.", f"Write a blog post about: {trend}\n\nReturn ONLY valid JSON.", 2000)
    try:
        clean = result.strip().replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except:
        return {"title": "Latest Trends 2025", "content": f"<p>{result}</p>", "excerpt": result[:200]}

def seo_expert_agent(title, content):
    result = call_deepseek("You are an SEO Expert. Return ONLY valid JSON with: meta_title, meta_description, keywords, tags.", f"Optimize SEO for: {title}\n\nReturn ONLY valid JSON.", 500)
    try:
        clean = result.strip().replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except:
        return {"meta_title": title, "meta_description": content[:160], "keywords": ["AI","Tech"], "tags": ["AI","Tech"]}

def image_agent(title):
    prompt = f"professional blog header image for {title}"
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true"

def editor_agent(post, seo, image_url):
    post["image_url"] = image_url
    post["meta_title"] = seo.get("meta_title", post["title"])
    post["tags"] = seo.get("tags", [])
    return post

def social_media_agent(title, content):
    result = call_deepseek("You are a Social Media Manager. Return ONLY valid JSON with: instagram, twitter, linkedin captions.", f"Create captions for: {title}\n\nReturn ONLY valid JSON.", 600)
    try:
        clean = result.strip().replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except:
        return {"instagram": "New post!", "twitter": "Check this out!", "linkedin": "New article."}

def marketing_agent(title):
    return call_deepseek("You are a Marketing Agent. Give 3 tips in Roman Urdu.", f"Marketing tips for: {title}", 400)

def publish_to_blogger(post, image_url):
    try:
        fresh_token = get_fresh_blogger_token()
        content_with_image = f'<img src="{image_url}" style="width:100%;border-radius:8px;"/>\n\n{post.get("content","")}'
        url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
        headers = {"Authorization": f"Bearer {fresh_token}", "Content-Type": "application/json"}
        body = {"kind": "blogger#post", "title": post.get("title",""), "content": content_with_image, "labels": post.get("tags",[])}
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        if resp.status_code == 200:
            return {"status": "published", "url": resp.json().get("url","")}
        return {"status": "error", "message": resp.text}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def run_company():
    company_state["running"] = True
    company_state["logs"] = []
    company_state["status"] = "running"
    try:
        log("CEO", "Planning...")
        company_state["results"]["ceo"] = ceo_agent()
        
        log("Trend Hunter", "Finding trends...")
        trend = trend_hunter_agent()
        
        log("Content Writer", "Writing...")
        post = content_writer_agent(trend)
        
        log("SEO Expert", "Optimizing...")
        seo = seo_expert_agent(post["title"], post["content"])
        
        log("Image Agent", "Generating image...")
        img = image_agent(post["title"])
        
        log("Editor", "Reviewing...")
        final = editor_agent(post, seo, img)
        
        log("Social Media", "Creating captions...")
        company_state["results"]["captions"] = social_media_agent(post["title"], post["content"])
        
        log("Marketing", "Strategy...")
        company_state["results"]["marketing"] = marketing_agent(post["title"])
        
        log("CEO", "Publishing...")
        pub = publish_to_blogger(final, img)
        company_state["results"]["published"] = pub
        
        company_state["status"] = "completed"
        log("CEO", "Kaam ho gaya!", "done")
    except Exception as e:
        log("System", f"Error: {str(e)}", "error")
        company_state["status"] = "error"
    company_state["running"] = False

DASHBOARD = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Company — Neo Vision Hub</title>
<style>
body{font-family:sans-serif;background:#0a0a0a;color:#fff;padding:20px}
.card{background:#111;border:1px solid #222;padding:15px;margin-bottom:10px;border-radius:8px}
.btn{background:#6366f1;color:#fff;border:none;padding:10px 20px;border-radius:5px;cursor:pointer}
.working{color:#6366f1} .done{color:#22c55e} .error{color:#ef4444}
</style></head><body>
<h2>Neo Vision Hub — AI Agents</h2>
<button class="btn" onclick="fetch('/run',{method:'POST'});location.reload()">Run Company</button>
<div id="status"></div>
<script>
setInterval(async ()=>{
  const d = await(await fetch('/status')).json();
  let h = `<h3>Status: ${d.status}</h3>`;
  d.logs.forEach(l => h += `<div class="card ${l.status}">${l.agent}: ${l.message}</div>`);
  document.getElementById('status').innerHTML = h;
}, 2000);
</script></body></html>'''

@app.route("/")
def index(): return render_template_string(DASHBOARD)

@app.route("/status")
def status(): return jsonify(company_state)

@app.route("/run", methods=["POST"])
def run():
    if not company_state["running"]:
        threading.Thread(target=run_company).start()
    return jsonify({"status": "started"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
