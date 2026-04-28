import os, json, requests, threading, urllib.parse
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# =============================
# APNI KEYS YAHAN DAALO
# =============================
DEEPSEEK_API_KEY = "sk-60389d1e6ba446d7920dd011947db7f5"
BLOGGER_API_KEY = "AIzaSyBFUbx6q98fZhUQZTntDh7YnufDnMa8p18"
BLOGGER_TOKEN = "ya29.a0AQvPyIP74eNJBwazWRCC378sQQghN6o1qWUAdYGcuRpr4f5m7O08JGgshnrxyaGNE3wLW7g1ch7-v9i0YBAp1WayB6TTnCN2gwW7oqJtSQdtQExtgqnim"
BLOG_ID = "21948522432663252"
# =============================

company_state = {"running": False, "logs": [], "results": {}, "status": "standby"}

def log(agent, message, status="working"):
    company_state["logs"].append({"agent": agent, "message": message, "status": status})

def call_deepseek(system_prompt, user_message, max_tokens=2000):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    body = {"model": "deepseek-chat", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}], "max_tokens": max_tokens, "temperature": 0.7}
    resp = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=body, timeout=60)
    return resp.json()["choices"][0]["message"]["content"]

def ceo_agent():
    return call_deepseek("You are Aria, CEO of Neo Vision Hub. Communicate in Roman Urdu. Create daily task plan.", "Aaj ke liye team ko kya plan dena chahiye? 3 points mein Roman Urdu mein batao.", 500)

def trend_hunter_agent():
    return call_deepseek("You are a Trend Hunter for Neo Vision Hub blog. Find trending topics in AI, Technology, Trading, or Gaming. Return ONE trending topic in English.", "Find the most trending topic right now in AI, Tech, Trading or Gaming.", 300)

def content_writer_agent(trend):
    result = call_deepseek("You are a blog Content Writer for Neo Vision Hub. Write SEO-optimized posts in English. Return ONLY valid JSON with keys: title, content (HTML 600-800 words), excerpt.", f"Write a complete blog post about: {trend}\n\nReturn ONLY valid JSON.", 2000)
    try:
        clean = result.strip().replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except:
        return {"title": "Latest Tech Trends 2025", "content": f"<p>{result}</p>", "excerpt": result[:200]}

def seo_expert_agent(title, content):
    result = call_deepseek("You are an SEO Expert. Return ONLY valid JSON with: meta_title, meta_description, keywords (list of 5), tags (list of 5).", f"Optimize SEO for:\nTitle: {title}\nContent: {content[:300]}\n\nReturn ONLY valid JSON.", 500)
    try:
        clean = result.strip().replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except:
        return {"meta_title": title, "meta_description": content[:160], "keywords": ["technology","AI","news","2025","trending"], "tags": ["AI","Tech","News","Trending","2025"]}

def image_agent(title):
    prompt = f"professional blog header image for article about {title}, modern clean digital art"
    encoded = urllib.parse.quote(prompt)
    return f"https://image.pollinations.ai/prompt/{encoded}?width=1200&height=630&nologo=true"

def editor_agent(post, seo, image_url):
    post["image_url"] = image_url
    post["meta_title"] = seo.get("meta_title", post["title"])
    post["meta_description"] = seo.get("meta_description", post.get("excerpt",""))
    post["tags"] = seo.get("tags", [])
    return post

def social_media_agent(title, content):
    result = call_deepseek("You are a Social Media Manager. Return ONLY valid JSON with: instagram, twitter, linkedin captions in English.", f"Create social media captions for: {title}\n\nReturn ONLY valid JSON.", 600)
    try:
        clean = result.strip().replace("```json","").replace("```","").strip()
        return json.loads(clean)
    except:
        return {"instagram": f"New post! {title} - Link in bio! #AI #Tech #NeoVisionHub", "twitter": f"Just published: {title} #AI #Tech", "linkedin": f"New article: {title}"}

def marketing_agent(title):
    return call_deepseek("You are a Marketing Agent for Neo Vision Hub. Give practical marketing tips in Roman Urdu.", f"Is blog post ko promote karne ke liye 3 strategies batao (Roman Urdu mein): {title}", 400)

def publish_to_blogger(post, image_url):
    if not BLOGGER_TOKEN or not BLOG_ID or BLOGGER_TOKEN == "apka_access_token":
        return {"status": "skipped", "message": "Blogger credentials nahi hain. Manually copy karo!"}
    content_with_image = f'<img src="{image_url}" alt="{post.get("title","")}" style="width:100%;border-radius:8px;margin-bottom:20px;"/>\n\n{post.get("content","")}'
    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOG_ID}/posts/"
    headers = {"Authorization": f"Bearer {BLOGGER_TOKEN}", "Content-Type": "application/json"}
    body = {"kind": "blogger#post", "title": post.get("title",""), "content": content_with_image, "labels": post.get("tags",[])}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        return {"status": "published", "url": data.get("url",""), "title": data.get("title","")}
    return {"status": "error", "message": resp.text}

def run_company():
    company_state["running"] = True
    company_state["logs"] = []
    company_state["results"] = {}
    company_state["status"] = "running"
    try:
        log("CEO", "Aaj ke tasks assign kar raha hoon...")
        company_state["results"]["ceo"] = ceo_agent()
        log("CEO", "Plan ready!", "done")

        log("Trend Hunter", "Trending topics dhundh raha hoon...")
        trend = trend_hunter_agent()
        company_state["results"]["trend"] = trend
        log("Trend Hunter", "Topic mila!", "done")

        log("Content Writer", "Blog post likh raha hoon...")
        post = content_writer_agent(trend)
        company_state["results"]["post"] = post
        log("Content Writer", "Blog post ready!", "done")

        log("SEO Expert", "SEO optimize kar raha hoon...")
        seo = seo_expert_agent(post["title"], post["content"])
        company_state["results"]["seo"] = seo
        log("SEO Expert", "SEO complete!", "done")

        log("Image Agent", "Image bana raha hoon...")
        image_url = image_agent(post["title"])
        company_state["results"]["image"] = image_url
        log("Image Agent", "Image ready!", "done")

        log("Editor", "Post review kar raha hoon...")
        final_post = editor_agent(post, seo, image_url)
        company_state["results"]["final_post"] = final_post
        log("Editor", "Post approved!", "done")

        log("Social Media", "Captions bana raha hoon...")
        captions = social_media_agent(post["title"], post["content"])
        company_state["results"]["captions"] = captions
        log("Social Media", "Captions ready!", "done")

        log("Marketing", "Strategy bana raha hoon...")
        marketing = marketing_agent(post["title"])
        company_state["results"]["marketing"] = marketing
        log("Marketing", "Strategy ready!", "done")

        log("CEO", "Blogger pr publish kar raha hoon...")
        pub = publish_to_blogger(final_post, image_url)
        company_state["results"]["published"] = pub
        log("CEO", "Kaam mukammal!", "done")

        company_state["status"] = "completed"
    except Exception as e:
        log("System", f"Error: {str(e)}", "error")
        company_state["status"] = "error"
    company_state["running"] = False

DASHBOARD = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Company — Neo Vision Hub</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh}
.header{padding:16px 20px;border-bottom:1px solid #1e1e1e;display:flex;align-items:center;justify-content:space-between}
.logo{font-size:16px;font-weight:600;color:#fff}.logo span{color:#6366f1}
.badge{font-size:11px;color:#888;background:#1a1a1a;border:1px solid #2a2a2a;padding:3px 10px;border-radius:20px}
.main{max-width:860px;margin:0 auto;padding:20px 14px}
.run-section{text-align:center;padding:24px 0 20px}
.run-btn{background:#6366f1;color:#fff;border:none;padding:13px 36px;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;transition:all 0.2s}
.run-btn:hover:not(:disabled){background:#4f46e5;transform:translateY(-1px)}
.run-btn:disabled{background:#333;cursor:not-allowed;transform:none}
.status-bar{background:#111;border:1px solid #1e1e1e;border-radius:10px;padding:11px 15px;margin-bottom:18px;display:flex;align-items:center;gap:10px;font-size:13px;color:#888}
.pulse{width:8px;height:8px;border-radius:50%;background:#333;flex-shrink:0}
.pulse.active{background:#22c55e;animation:pulse 1s infinite}
.pulse.done{background:#22c55e}.pulse.error{background:#ef4444}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}
.team-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.ceo-card{grid-column:1/-1}
.agent-card{background:#111;border:1px solid #1e1e1e;border-radius:12px;padding:14px;transition:border-color 0.3s}
.agent-card.active{border-color:#6366f1}.agent-card.done{border-color:#22c55e33}.agent-card.error{border-color:#ef444433}
.agent-head{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.avatar{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.agent-name{font-size:13px;font-weight:600;color:#fff}.agent-role{font-size:11px;color:#666}
.chip{font-size:10px;padding:3px 8px;border-radius:20px;background:#1a1a1a;border:1px solid #2a2a2a;color:#666;margin-left:auto}
.chip.working{background:#1e1b4b;border-color:#6366f133;color:#a5b4fc}
.chip.done{background:#052e16;border-color:#22c55e33;color:#86efac}
.chip.error{background:#2d0000;border-color:#ef444433;color:#fca5a5}
.agent-log{font-size:12px;color:#555;border-top:1px solid #1a1a1a;padding-top:9px;min-height:28px;line-height:1.6}
.agent-log.msg{color:#999}
.dots span{animation:blink 1.2s infinite;display:inline-block}
.dots span:nth-child(2){animation-delay:0.2s}.dots span:nth-child(3){animation-delay:0.4s}
@keyframes blink{0%,100%{opacity:0.2}50%{opacity:1}}
.result-card{background:#111;border:1px solid #1e1e1e;border-radius:12px;margin-top:10px;overflow:hidden}
.result-header{padding:11px 15px;background:#161616;border-bottom:1px solid #1e1e1e;font-size:13px;font-weight:600;color:#ccc;display:flex;align-items:center;cursor:pointer}
.result-header .arr{margin-left:auto;color:#555}
.result-body{padding:14px;font-size:12px;color:#aaa;line-height:1.7}
.caption-box{background:#0f172a;border:1px solid #1e293b;border-radius:8px;padding:11px;margin-bottom:8px}
.clabel{font-size:10px;color:#475569;margin-bottom:5px;text-transform:uppercase;letter-spacing:0.5px}
.pub{padding:11px;border-radius:8px;font-size:13px}
.pub.published{background:#052e16;color:#86efac;border:1px solid #22c55e33}
.pub.skipped{background:#1c1900;color:#fde68a;border:1px solid #f59e0b33}
.pub.error{background:#2d0000;color:#fca5a5;border:1px solid #ef444433}
@media(max-width:560px){.team-grid{grid-template-columns:1fr}.ceo-card{grid-column:1}}
</style></head><body>
<div class="header"><div class="logo">Company <span>•</span> Neo Vision Hub</div><div class="badge">8 AI Agents</div></div>
<div class="main">
<div class="run-section">
  <button class="run-btn" id="runBtn" onclick="startRun()">▶ Run Karo</button>
  <div style="font-size:12px;color:#555;margin-top:8px">Sab agents tayar hain</div>
</div>
<div class="status-bar"><div class="pulse" id="mainPulse"></div><span id="mainStatus">Standby — Run Karo dabao</span></div>
<div class="team-grid">
  <div class="agent-card ceo-card" id="card-ceo"><div class="agent-head"><div class="avatar" style="background:#1e1b4b">👔</div><div><div class="agent-name">Aria</div><div class="agent-role">CEO</div></div><div class="chip" id="chip-ceo">Standby</div></div><div class="agent-log" id="log-ceo">Intezaar mein...</div></div>
  <div class="agent-card" id="card-trend"><div class="agent-head"><div class="avatar" style="background:#064e3b">🔍</div><div><div class="agent-name">Zain</div><div class="agent-role">Trend Hunter</div></div><div class="chip" id="chip-trend">Standby</div></div><div class="agent-log" id="log-trend">Intezaar mein...</div></div>
  <div class="agent-card" id="card-writer"><div class="agent-head"><div class="avatar" style="background:#1e3a5f">✍️</div><div><div class="agent-name">Sara</div><div class="agent-role">Content Writer</div></div><div class="chip" id="chip-writer">Standby</div></div><div class="agent-log" id="log-writer">Intezaar mein...</div></div>
  <div class="agent-card" id="card-seo"><div class="agent-head"><div class="avatar" style="background:#1a2e05">🎯</div><div><div class="agent-name">Rayan</div><div class="agent-role">SEO Expert</div></div><div class="chip" id="chip-seo">Standby</div></div><div class="agent-log" id="log-seo">Intezaar mein...</div></div>
  <div class="agent-card" id="card-image"><div class="agent-head"><div class="avatar" style="background:#3b1f00">🎨</div><div><div class="agent-name">Pixel</div><div class="agent-role">Image Agent</div></div><div class="chip" id="chip-image">Standby</div></div><div class="agent-log" id="log-image">Intezaar mein...</div></div>
  <div class="agent-card" id="card-editor"><div class="agent-head"><div class="avatar" style="background:#2d0047">✅</div><div><div class="agent-name">Alex</div><div class="agent-role">Editor</div></div><div class="chip" id="chip-editor">Standby</div></div><div class="agent-log" id="log-editor">Intezaar mein...</div></div>
  <div class="agent-card" id="card-social"><div class="agent-head"><div class="avatar" style="background:#3b0a1e">📱</div><div><div class="agent-name">Mia</div><div class="agent-role">Social Media</div></div><div class="chip" id="chip-social">Standby</div></div><div class="agent-log" id="log-social">Intezaar mein...</div></div>
  <div class="agent-card" id="card-marketing"><div class="agent-head"><div class="avatar" style="background:#1a0030">📢</div><div><div class="agent-name">Omar</div><div class="agent-role">Marketing</div></div><div class="chip" id="chip-marketing">Standby</div></div><div class="agent-log" id="log-marketing">Intezaar mein...</div></div>
</div>
<div id="results"></div>
</div>
<script>
let polling=null,lastLog=0;
const amap={"CEO":"ceo","Trend Hunter":"trend","Content Writer":"writer","SEO Expert":"seo","Image Agent":"image","Editor":"editor","Social Media":"social","Marketing":"marketing","System":"ceo"};
function setChip(id,st,txt){const c=document.getElementById(`chip-${id}`),card=document.getElementById(`card-${id}`);if(!c)return;c.textContent=txt;c.className=`chip ${st}`;card.className=`agent-card ${id==="ceo"?"ceo-card ":""}${st}`;}
function setLog(id,msg){const el=document.getElementById(`log-${id}`);if(!el)return;el.className="agent-log msg";el.textContent=msg;}
function setWorking(id){const el=document.getElementById(`log-${id}`);if(!el)return;el.className="agent-log msg";el.innerHTML='Kaam kar raha hai <span class="dots"><span>.</span><span>.</span><span>.</span></span>';setChip(id,"working","Working...");}
async function startRun(){
  const btn=document.getElementById("runBtn");
  btn.disabled=true;btn.textContent="⏳ Chal raha hai...";
  document.getElementById("mainPulse").className="pulse active";
  document.getElementById("mainStatus").textContent="Team kaam kar rahi hai...";
  document.getElementById("results").innerHTML="";
  lastLog=0;
  ["ceo","trend","writer","seo","image","editor","social","marketing"].forEach(id=>{setChip(id,"","Standby");const el=document.getElementById(`log-${id}`);if(el){el.className="agent-log";el.textContent="Queue mein...";} });
  await fetch("/run",{method:"POST"});
  polling=setInterval(poll,1500);
}
async function poll(){
  try{
    const d=await(await fetch("/status")).json();
    const logs=d.logs||[];
    for(let i=lastLog;i<logs.length;i++){const l=logs[i],id=amap[l.agent]||"ceo";if(l.status==="working")setWorking(id);else if(l.status==="done"){setChip(id,"done","Done ✓");setLog(id,l.message);}else if(l.status==="error"){setChip(id,"error","Error");setLog(id,l.message);}}
    lastLog=logs.length;
    if(d.status==="completed"){clearInterval(polling);document.getElementById("runBtn").disabled=false;document.getElementById("runBtn").textContent="▶ Dobara Chalao";document.getElementById("mainPulse").className="pulse done";document.getElementById("mainStatus").textContent="Sab kaam mukammal! 🎉";showResults(d.results);}
    else if(d.status==="error"){clearInterval(polling);document.getElementById("runBtn").disabled=false;document.getElementById("runBtn").textContent="▶ Dobara Try Karo";document.getElementById("mainPulse").className="pulse error";document.getElementById("mainStatus").textContent="Error aaya — dobara chalao";}
  }catch(e){}
}
function rc(title,body){return`<div class="result-card"><div class="result-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'block':'none'">${title}<span class="arr">▲</span></div><div class="result-body">${body}</div></div>`;}
function showResults(r){
  let html="";
  if(r.post)html+=rc("📝 Blog Post",`${r.image?`<img src="${r.image}" style="width:100%;border-radius:8px;margin-bottom:12px" onerror="this.style.display='none'"/>`:""}
    <strong style="font-size:15px;color:#fff;display:block;margin-bottom:8px">${r.post.title||""}</strong>
    <p style="color:#666;font-size:12px;margin-bottom:10px">${r.post.excerpt||""}</p>
    <div style="color:#888;font-size:12px">${(r.post.content||"").substring(0,400)}...</div>`);
  if(r.seo)html+=rc("🎯 SEO",`<div style="display:grid;gap:8px">
    <div><span style="color:#555;font-size:11px">META TITLE</span><div style="color:#ccc">${r.seo.meta_title||""}</div></div>
    <div><span style="color:#555;font-size:11px">KEYWORDS</span><div style="color:#6366f1">${(r.seo.keywords||[]).join(" • ")}</div></div>
    <div><span style="color:#555;font-size:11px">TAGS</span><div>${(r.seo.tags||[]).map(t=>`<span style="background:#1e1b4b;color:#a5b4fc;padding:2px 8px;border-radius:20px;font-size:11px;margin-right:4px">${t}</span>`).join("")}</div></div></div>`);
  if(r.captions)html+=rc("📱 Social Media",`
    <div class="caption-box"><div class="clabel">Instagram</div>${r.captions.instagram||""}</div>
    <div class="caption-box"><div class="clabel">Twitter</div>${r.captions.twitter||""}</div>
    <div class="caption-box"><div class="clabel">LinkedIn</div>${r.captions.linkedin||""}</div>`);
  if(r.marketing)html+=rc("📢 Marketing",`<div style="white-space:pre-wrap">${r.marketing}</div>`);
  if(r.published){const p=r.published,cls=p.status==="published"?"published":p.status==="error"?"error":"skipped",msg=p.status==="published"?`✅ Published! <a href="${p.url}" target="_blank" style="color:#86efac">${p.url}</a>`:`⚠️ ${p.message}`;html+=rc("🚀 Publish",`<div class="pub ${cls}">${msg}</div>`);}
  document.getElementById("results").innerHTML=html;
}
</script></body></html>'''

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD)

@app.route("/run", methods=["POST"])
def run():
    if company_state["running"]:
        return jsonify({"error": "Team pehle se kaam kar rahi hai!"}), 400
    t = threading.Thread(target=run_company)
    t.daemon = True
    t.start()
    return jsonify({"message": "Chalu ho gaya!"})

@app.route("/status")
def get_status():
    return jsonify(company_state)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
