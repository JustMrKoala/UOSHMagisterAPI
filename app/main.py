from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from html import escape
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from app import magister_session as ms

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

RESOURCE_DESCRIPTIONS = {
    "overview": "Combined profile, grades, schedule, absences, homework, and messages in one JSON response.",
    "profile": "Account and profile details.",
    "grades": "Recent grades.",
    "schedule": "Schedule for a specific date.",
    "absences": "Recent absences.",
    "homework": "Homework items.",
    "messages": "Recent messages.",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await ms.shutdown()


app = FastAPI(
    title="UOSHMagisterAPI",
    description="""
## UOSHMagisterAPI

UOSHMagisterAPI stands for **Unofficial Selfhosted Magister API**.
UOSHMagisterAPI staat voor **Unofficial Selfhosted Magister API**.

## How to use / Gebruik

1. `POST /login` with Magister credentials to create an API key
2. Use `/ui` for a browser UI with login, API keys, and readable JSON output
3. Use `/raw/overview?api_key=...` for one combined JSON response
4. Use `/llm.txt` as an instruction URL for ChatGPT or other AI tools
5. Closing the linked Chromium session invalidates the API key

1. Gebruik `POST /login` met Magister-inloggegevens om een API-key aan te maken
2. Gebruik `/ui` voor een browserinterface met login, API-keys en leesbare JSON-uitvoer
3. Gebruik `/raw/overview?api_key=...` voor één gecombineerde JSON-response
4. Gebruik `/llm.txt` als instructie-URL voor ChatGPT of andere AI-tools
5. Als de gekoppelde Chromium-sessie sluit, wordt de API-key ongeldig

## Main routes / Belangrijkste routes

- `/ui` → human-friendly dashboard
- `/ui` → gebruiksvriendelijk dashboard
- `/llm.txt` → AI instructions
- `/llm.txt` → AI-instructies
- `/raw/{resource}?api_key=...` → raw JSON for `overview`, `profile`, `grades`, `schedule`, `absences`, `homework`, and `messages`
- `/raw/{resource}?api_key=...` → raw JSON voor `overview`, `profile`, `grades`, `schedule`, `absences`, `homework` en `messages`
- `/profile`, `/grades`, `/schedule`, `/absences`, `/homework`, `/messages` → header-authenticated routes using `X-API-Key`
- `/profile`, `/grades`, `/schedule`, `/absences`, `/homework`, `/messages` → header-geauthenticeerde routes met `X-API-Key`
""",
    version="3.2.0",
    lifespan=lifespan,
)


class LoginRequest(BaseModel):
    username: str
    password: str
    school: str


def require_key(x_api_key: str = Header(..., description="API key from POST /login")) -> str:
    try:
        ms.get_session(x_api_key)
        return x_api_key
    except RuntimeError as error:
        raise HTTPException(status_code=401, detail=str(error))


def require_query_key(api_key: str = Query(..., description="API key from POST /login")) -> str:
    try:
        ms.get_session(api_key)
        return api_key
    except RuntimeError as error:
        raise HTTPException(status_code=401, detail=str(error))


async def get_resource_payload(resource: str, api_key: str, date: Optional[str] = None):
    if resource == "overview":
        return {
            "profile": await ms.get_profile(api_key),
            "grades": await ms.get_grades(api_key),
            "schedule": await ms.get_schedule(api_key, date),
            "absences": await ms.get_absences(api_key),
            "homework": await ms.get_homework(api_key),
            "messages": await ms.get_messages(api_key),
        }
    if resource == "profile":
        return await ms.get_profile(api_key)
    if resource == "grades":
        return await ms.get_grades(api_key)
    if resource == "schedule":
        return await ms.get_schedule(api_key, date)
    if resource == "absences":
        return await ms.get_absences(api_key)
    if resource == "homework":
        return await ms.get_homework(api_key)
    if resource == "messages":
        return await ms.get_messages(api_key)
    raise HTTPException(status_code=404, detail=f"Unknown resource '{resource}'.")


def build_ai_instructions() -> str:
    lines = [
        "# UOSHMagisterAPI - AI Guide",
        "",
        "UOSHMagisterAPI stands for Unofficial Selfhosted Magister API.",
        "This file is served from the same server as the API.",
        "The API base URL is the URL of this file with `/llm.txt` removed.",
        "Example: if this file is at `http://127.0.0.1:8000/llm.txt`, the base URL is `http://127.0.0.1:8000`.",
        "",
        "Use this API when the user gives you:",
        "1. This `llm.txt` URL or the server base URL",
        "2. Their API key",
        "",
        "Authentication:",
        "- Preferred for AI tools: pass the API key as the `api_key` query parameter on `/raw/...` routes.",
        "- The header-based routes also exist, but `/raw/...` is the easiest interface for tools.",
        "",
        "Required AI behavior:",
        "- Always fetch data from the API before answering questions about a user's Magister data.",
        "- Use the fetched JSON to answer the user's actual question.",
        "- Convert raw JSON into concise, human-friendly language.",
        "- Do not paste raw JSON unless the user explicitly asks for raw JSON.",
        "- If the user asks for a specific category, focus only on that category.",
        "- If the answer is not present in the API response, say that clearly.",
        "- If the API returns 401, explain that the API key is invalid or the linked Chromium session was closed.",
        "",
        "Recommended workflow:",
        "1. Derive the base URL by removing `/llm.txt` from this file's URL.",
        "2. Start with `/raw/overview?api_key=API_KEY_HERE` unless the user only wants one category.",
        "3. If needed, call a narrower `/raw/...` route such as `schedule`, `messages`, or `grades`.",
        "4. Parse the JSON response.",
        "5. Answer the user directly in plain language.",
        "",
        "Response style:",
        "- Be direct and useful.",
        "- Prefer summaries, bullet points, short lists, and clear dates/times.",
        "- Mention missing or uncertain data explicitly.",
        "- Keep names, dates, grades, rooms, and message subjects accurate to the fetched JSON.",
        "",
        "Best starting endpoint:",
        "- `/raw/overview?api_key=API_KEY_HERE`",
        "- This returns profile, grades, schedule, absences, homework, and messages in one JSON document.",
        "",
        "Available raw JSON routes:",
    ]
    for resource, description in RESOURCE_DESCRIPTIONS.items():
        suffix = "&date=YYYY-MM-DD" if resource in {"overview", "schedule"} else ""
        lines.append(f"- `/raw/{resource}?api_key=API_KEY_HERE{suffix}` -> {description}")
    lines.extend([
        "",
        "How to answer common questions:",
        "- `What are my latest grades?` -> fetch `overview` or `grades`, then summarize the latest grades and subjects in plain language.",
        "- `Do I have homework?` -> fetch `overview` or `homework`, then list open homework items clearly.",
        "- `What is on my schedule tomorrow?` -> fetch `schedule` for the requested date and summarize lessons, times, rooms, teachers, and cancellations.",
        "- `Any unread messages?` -> fetch `messages` and summarize sender, subject, date, and read state.",
        "- `Give me everything` -> fetch `overview` and organize the response into sections.",
        "",
        "Worked example:",
        "- Input: base URL `http://127.0.0.1:8000`, API key `abc123`, question `What homework do I still have?`",
        "- Fetch: `http://127.0.0.1:8000/raw/homework?api_key=abc123`",
        "- Then answer with a readable summary of the homework items instead of dumping the JSON.",
        "",
        "Notes:",
        "- Use `/raw/schedule?...&date=YYYY-MM-DD` for a specific day.",
        "- The API key is tied to a live Chromium session. Closing that browser invalidates the key.",
        "- `/ui` provides a browser UI to log in, browse active API keys, open the linked Chromium window, and inspect formatted JSON.",
    ])
    return "\n".join(lines)

def build_ui_html() -> str:
    resource_options = "".join(
        f'<option value="{escape(name)}">{escape(name.title())} - {escape(description)}</option>'
        for name, description in RESOURCE_DESCRIPTIONS.items()
    )
    ai_guide = escape(build_ai_instructions())
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>UOSHMagisterAPI Control Panel</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
    h1, h2 {{ margin-bottom: 12px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; }}
    .card {{ background: #111827; border: 1px solid #334155; border-radius: 12px; padding: 18px; }}
    label {{ display: block; margin: 10px 0 6px; font-weight: 600; }}
    input, select, button, textarea {{ width: 100%; box-sizing: border-box; border-radius: 8px; border: 1px solid #475569; padding: 10px 12px; background: #0b1220; color: #e2e8f0; }}
    textarea {{ min-height: 120px; resize: vertical; }}
    button {{ background: #2563eb; cursor: pointer; font-weight: 700; margin-top: 12px; }}
    button.secondary {{ background: #334155; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #020617; border-radius: 8px; padding: 14px; min-height: 240px; overflow: auto; }}
    code {{ color: #93c5fd; }}
    .session {{ border-top: 1px solid #334155; padding-top: 10px; margin-top: 10px; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 12px; }}
    .actions button {{ flex: 1; min-width: 140px; }}
    .muted {{ color: #94a3b8; font-size: 0.95rem; }}
    a {{ color: #93c5fd; }}
  </style>
</head>
<body>
  <main>
    <h1>UOSHMagisterAPI Control Panel</h1>
    <p class="muted">Log in, manage API keys, bring the linked Chromium session to the front, and inspect JSON without curl.</p>
    <div class="grid">
      <section class="card">
        <h2>Login</h2>
        <label>Username</label>
        <input id="username" autocomplete="username">
        <label>Password</label>
        <input id="password" type="password" autocomplete="current-password">
        <label>School subdomain</label>
        <input id="school" placeholder="myschool">
        <button onclick="login()">Create session and API key</button>
        <p id="loginStatus" class="muted"></p>
      </section>
      <section class="card">
        <h2>Use API key</h2>
        <label>API key</label>
        <textarea id="apiKey" placeholder="Paste or generate an API key here"></textarea>
        <label>Resource</label>
        <select id="resource">{resource_options}</select>
        <label>Date for schedule / overview</label>
        <input id="date" placeholder="YYYY-MM-DD">
        <label>Magister path to open in Chromium</label>
        <input id="browserPath" placeholder="/" value="/">
        <div class="actions">
          <button onclick="loadResource()">Load JSON</button>
          <button class="secondary" onclick="openBrowserSession()">Open linked Chromium</button>
          <button class="secondary" onclick="copyRawUrl()">Copy raw URL</button>
        </div>
      </section>
    </div>
    <div class="grid" style="margin-top: 20px;">
      <section class="card">
        <h2>Active sessions</h2>
        <button class="secondary" onclick="refreshSessions()">Refresh sessions</button>
        <div id="sessions" class="muted" style="margin-top: 10px;">No sessions loaded yet.</div>
      </section>
      <section class="card">
        <h2>AI instructions</h2>
        <p class="muted">Give ChatGPT your API key and this guide URL: <code>/llm.txt</code></p>
        <pre>{ai_guide}</pre>
      </section>
    </div>
    <section class="card" style="margin-top: 20px;">
      <h2>JSON output</h2>
      <p id="jsonMeta" class="muted">Pick a resource and load it.</p>
      <pre id="jsonOutput">{json.dumps({}, indent=2)}</pre>
    </section>
  </main>
  <script>
    async function apiFetch(url, options = undefined) {{
      const response = await fetch(url, options);
      const contentType = response.headers.get('content-type') || '';
      const data = contentType.includes('application/json') ? await response.json() : await response.text();
      if (!response.ok) {{
        throw new Error(typeof data === 'string' ? data : JSON.stringify(data, null, 2));
      }}
      return data;
    }}

    function currentRawUrl() {{
      const apiKey = encodeURIComponent(document.getElementById('apiKey').value.trim());
      const resource = encodeURIComponent(document.getElementById('resource').value);
      const date = document.getElementById('date').value.trim();
      let url = `/raw/${{resource}}?api_key=${{apiKey}}`;
      if (date) {{
        url += `&date=${{encodeURIComponent(date)}}`;
      }}
      return url;
    }}

    async function login() {{
      try {{
        const payload = {{
          username: document.getElementById('username').value.trim(),
          password: document.getElementById('password').value,
          school: document.getElementById('school').value.trim(),
        }};
        const result = await apiFetch('/login', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify(payload),
        }});
        document.getElementById('apiKey').value = result.api_key;
        document.getElementById('loginStatus').textContent = result.message;
        await refreshSessions();
      }} catch (error) {{
        document.getElementById('loginStatus').textContent = error.message;
      }}
    }}

    async function loadResource() {{
      try {{
        const url = currentRawUrl();
        const data = await apiFetch(url);
        document.getElementById('jsonMeta').textContent = `Loaded from ${{url}}`;
        document.getElementById('jsonOutput').textContent = JSON.stringify(data, null, 2);
      }} catch (error) {{
        document.getElementById('jsonMeta').textContent = error.message;
      }}
    }}

    async function openBrowserSession() {{
      try {{
        const apiKey = encodeURIComponent(document.getElementById('apiKey').value.trim());
        const browserPath = encodeURIComponent(document.getElementById('browserPath').value.trim() || '/');
        const result = await apiFetch(`/ui/open-browser?api_key=${{apiKey}}&path=${{browserPath}}`, {{ method: 'POST' }});
        document.getElementById('jsonMeta').textContent = `Opened Chromium at ${{result.url}}`;
      }} catch (error) {{
        document.getElementById('jsonMeta').textContent = error.message;
      }}
    }}

    async function refreshSessions() {{
      try {{
        const data = await apiFetch('/ui/api/sessions');
        const container = document.getElementById('sessions');
        if (!data.sessions.length) {{
          container.textContent = 'No active sessions.';
          return;
        }}
        container.innerHTML = data.sessions.map((session) => `
          <div class="session">
            <strong>${{session.username}}</strong> @ ${{session.school}}<br>
            <span class="muted">Key:</span> <code>${{session.api_key}}</code><br>
            <span class="muted">Current URL:</span> <code>${{session.current_url}}</code><br>
            <button class="secondary" onclick="document.getElementById('apiKey').value='${{session.api_key}}'">Use this key</button>
          </div>
        `).join('');
      }} catch (error) {{
        document.getElementById('sessions').textContent = error.message;
      }}
    }}

    async function copyRawUrl() {{
      try {{
        const absoluteUrl = `${{window.location.origin}}${{currentRawUrl()}}`;
        await navigator.clipboard.writeText(absoluteUrl);
        document.getElementById('jsonMeta').textContent = `Copied ${{absoluteUrl}}`;
      }} catch (error) {{
        document.getElementById('jsonMeta').textContent = error.message;
      }}
    }}

    refreshSessions();
  </script>
</body>
</html>
"""


@app.post("/login", tags=["session"], summary="Log in and get your API key")
async def login(body: LoginRequest):
    try:
        api_key = await ms.create_session(body.username, body.password, body.school)
        return {
            "status": "ok",
            "api_key": api_key,
            "message": f"Logged in as {body.username} @ {body.school}.magister.net. Use the api_key in the X-API-Key header for header-authenticated routes.",
        }
    except Exception as error:
        raise HTTPException(status_code=401, detail=str(error))


@app.post("/logout", tags=["session"], summary="Revoke your API key and close the session")
async def logout(api_key: str = Depends(require_key)):
    await ms.revoke_session(api_key)
    return {"status": "ok", "message": "Session closed and API key revoked."}


@app.get("/sessions", tags=["session"], summary="List all active sessions without full API keys")
async def sessions():
    return {"sessions": ms.list_sessions()}


@app.get("/ui/api/sessions", tags=["ui"], summary="List active sessions with full API keys for the local UI")
async def ui_sessions():
    return {"sessions": ms.list_sessions_detailed()}


@app.get("/", tags=["health"], summary="Health check")
async def root():
    return {"status": "ok", "active_sessions": len(ms._sessions)}


@app.get("/ui", response_class=HTMLResponse, tags=["ui"], summary="Human-friendly dashboard for login, API keys, and JSON viewing")
async def ui_dashboard():
    return HTMLResponse(build_ui_html())


@app.post("/ui/open-browser", tags=["ui"], summary="Bring the Chromium session for an API key to the front")
async def open_browser(api_key: str = Depends(require_query_key), path: str = Query(default="/")):
    try:
        return await ms.open_session_view(api_key, path)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


@app.get("/llm.txt", response_class=PlainTextResponse, tags=["ai"], summary="Instructions for AI tools on how to query this API")
async def llm_instructions():
    return PlainTextResponse(build_ai_instructions())


@app.get("/raw/{resource}", tags=["raw"], summary="Raw JSON route that accepts the API key as a query parameter")
async def raw_resource(
    resource: str,
    api_key: str = Depends(require_query_key),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD for schedule or overview"),
):
    return await get_resource_payload(resource, api_key, date)


@app.get("/profile", tags=["account"], summary="Your Magister account info")
async def profile(api_key: str = Depends(require_key)):
    return await ms.get_profile(api_key)


@app.get("/grades", tags=["academics"], summary="Your grades")
async def grades(api_key: str = Depends(require_key)):
    data = await ms.get_grades(api_key)
    return {"count": len(data), "grades": data}


@app.get("/schedule", tags=["academics"], summary="Your schedule")
async def schedule(
    api_key: str = Depends(require_key),
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD, defaults to today", examples=["2024-09-16"]),
):
    data = await ms.get_schedule(api_key, date)
    return {"date": date or "today", "count": len(data), "lessons": data}


@app.get("/absences", tags=["academics"], summary="Your absences")
async def absences(api_key: str = Depends(require_key)):
    data = await ms.get_absences(api_key)
    return {"count": len(data), "absences": data}


@app.get("/homework", tags=["academics"], summary="Your homework")
async def homework(api_key: str = Depends(require_key)):
    data = await ms.get_homework(api_key)
    return {"count": len(data), "homework": data}


@app.get("/messages", tags=["communication"], summary="Your messages")
async def messages(api_key: str = Depends(require_key)):
    data = await ms.get_messages(api_key)
    return {"count": len(data), "messages": data}
