from __future__ import annotations

import asyncio
import logging
import secrets
from dataclasses import dataclass
from datetime import date
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

logger = logging.getLogger(__name__)

_playwright: Optional[Playwright] = None
_browser: Optional[Browser] = None
_sessions: dict[str, "Session"] = {}
_lock = asyncio.Lock()


@dataclass
class Session:
    api_key: str
    username: str
    school: str
    person_id: int
    context: BrowserContext
    page: Page
    logged_in: bool = False


def _invalidate_session(api_key: str) -> None:
    session = _sessions.pop(api_key, None)
    if session:
        session.logged_in = False


def _base(school: str) -> str:
    return f"https://{school}.magister.net"


async def _ensure_browser() -> Browser:
    global _playwright, _browser
    if _browser is None:
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=False, args=["--start-maximized"])
        logger.info("Browser started.")
    return _browser


async def shutdown() -> None:
    global _playwright, _browser, _sessions
    for session in list(_sessions.values()):
        await session.context.close()
    _sessions.clear()
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()
    _browser = None
    _playwright = None


async def _fetch(page: Page, url: str) -> dict | list:
    return await page.evaluate(
        f"""
        async () => {{
            const response = await fetch('{url}', {{credentials: 'include'}});
            if (!response.ok) return {{error: response.status + ' ' + response.statusText}};
            return response.json();
        }}
    """
    )


async def create_session(username: str, password: str, school: str) -> str:
    async with _lock:
        browser = await _ensure_browser()
        context = await browser.new_context(no_viewport=True)
        page = await context.new_page()

        try:
            logger.info("Going to %s", _base(school))
            await page.goto(_base(school), wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            username_input = await page.wait_for_selector('input[type="text"], input[type="email"]', timeout=10_000)
            await username_input.click()
            await username_input.fill(username)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")
            logger.info("Filled username, pressed Enter")

            password_input = await page.wait_for_selector('input[type="password"]', state="visible", timeout=15_000)
            await password_input.click()
            await password_input.fill(password)
            await page.wait_for_timeout(500)
            await page.keyboard.press("Enter")
            logger.info("Filled password, pressed Enter")

            await page.wait_for_timeout(3000)
            await page.wait_for_load_state("networkidle", timeout=20_000)
            logger.info("Landed on: %s", page.url)

            account = await _fetch(page, "/api/account")
            person_id = account.get("Persoon", {}).get("Id") if isinstance(account, dict) else None
            if not person_id:
                raise RuntimeError(f"Could not get person ID. Account response: {account}")
            logger.info("Person ID: %s", person_id)

            api_key = secrets.token_urlsafe(32)
            _sessions[api_key] = Session(
                api_key=api_key,
                username=username,
                school=school,
                person_id=person_id,
                context=context,
                page=page,
                logged_in=True,
            )
            page.on("close", lambda: _invalidate_session(api_key))
            context.on("close", lambda: _invalidate_session(api_key))
            logger.info("Session ready. Key: ...%s", api_key[-8:])
            return api_key
        except Exception as error:
            logger.error("Login failed: %s", error, exc_info=True)
            await context.close()
            raise


async def revoke_session(api_key: str) -> None:
    session = _sessions.pop(api_key, None)
    if session:
        await session.context.close()


def get_session(api_key: str) -> Session:
    session = _sessions.get(api_key)
    if not session or not session.logged_in:
        raise RuntimeError("Invalid or expired API key. Call POST /login first.")
    return session


def list_sessions() -> list[dict]:
    return [
        {
            "username": session.username,
            "school": session.school,
            "person_id": session.person_id,
            "key_suffix": session.api_key[-6:],
        }
        for session in _sessions.values()
    ]


def list_sessions_detailed() -> list[dict]:
    return [
        {
            "api_key": session.api_key,
            "key_suffix": session.api_key[-6:],
            "username": session.username,
            "school": session.school,
            "person_id": session.person_id,
            "logged_in": session.logged_in,
            "current_url": session.page.url,
        }
        for session in _sessions.values()
    ]


async def open_session_view(api_key: str, path: str | None = None) -> dict:
    session = get_session(api_key)
    base_url = _base(session.school)
    target_url = session.page.url or base_url

    if path:
        if path.startswith("http://") or path.startswith("https://"):
            if not path.startswith(base_url):
                raise RuntimeError("Requested URL must stay inside the logged-in Magister domain.")
            target_url = path
        else:
            normalized_path = path if path.startswith("/") else f"/{path}"
            target_url = f"{base_url}{normalized_path}"
        await session.page.goto(target_url, wait_until="domcontentloaded")

    await session.page.bring_to_front()
    return {"status": "ok", "url": target_url, "school": session.school, "username": session.username}


async def get_grades(api_key: str) -> list[dict]:
    session = get_session(api_key)
    response = await _fetch(session.page, f"/api/personen/{session.person_id}/cijfers/laatste?top=50")
    logger.info("Grades raw keys: %s", list(response.keys()) if isinstance(response, dict) else type(response))
    items = response.get("items") or response.get("Items") if isinstance(response, dict) else None
    if not items:
        return [{"error": response}]
    return [
        {
            "vak": item.get("vak", {}).get("omschrijving") or item.get("Vak", {}).get("Omschrijving", ""),
            "code": item.get("vak", {}).get("code") or item.get("Vak", {}).get("Code", ""),
            "cijfer": item.get("waarde") or item.get("CijferStr", ""),
            "omschrijving": item.get("omschrijving") or item.get("Omschrijving", ""),
            "weging": item.get("weegfactor") or item.get("Weging", ""),
            "datum": (item.get("ingevoerdOp") or item.get("DatumIngevoerd", ""))[:10],
            "voldoende": item.get("isVoldoende") if item.get("isVoldoende") is not None else None,
            "telt_mee": item.get("teltMee", True),
        }
        for item in items
    ]


async def get_schedule(api_key: str, date_str: str | None = None) -> list[dict]:
    target = date_str or date.today().isoformat()
    session = get_session(api_key)
    response = await _fetch(session.page, f"/api/personen/{session.person_id}/afspraken?status=1&tot={target}&van={target}")
    logger.info("Schedule raw keys: %s", list(response.keys()) if isinstance(response, dict) else type(response))
    items = response.get("items") or response.get("Items") if isinstance(response, dict) else None
    if not items:
        return [{"error": response}]
    return [
        {
            "vak": item.get("omschrijving") or item.get("Omschrijving", ""),
            "docent": (item.get("docenten") or item.get("Docenten") or [{}])[0].get("naam")
            or (item.get("docenten") or item.get("Docenten") or [{}])[0].get("Naam", ""),
            "lokaal": (item.get("lokalen") or item.get("Lokalen") or [{}])[0].get("naam")
            or (item.get("lokalen") or item.get("Lokalen") or [{}])[0].get("Naam", ""),
            "start": item.get("start") or item.get("Start", ""),
            "einde": item.get("einde") or item.get("Einde", ""),
            "uitgevallen": (item.get("status") or item.get("Status", 1)) == 5,
        }
        for item in items
    ]


async def get_absences(api_key: str) -> list[dict]:
    session = get_session(api_key)
    response = await _fetch(session.page, f"/api/personen/{session.person_id}/absenties?top=50")
    logger.info("Absences raw keys: %s", list(response.keys()) if isinstance(response, dict) else type(response))
    items = response.get("items") or response.get("Items") if isinstance(response, dict) else None
    if not items:
        return [{"error": response}]
    return [
        {
            "datum": (item.get("begin") or item.get("Begin", ""))[:10],
            "vak": item.get("omschrijving") or item.get("Omschrijving", ""),
            "reden": item.get("redenOmschrijving") or item.get("RedenOmschrijving", ""),
            "geoorloofd": item.get("geoorloofd") or item.get("Geoorloofd", False),
            "duur": item.get("duur") or item.get("Duur", ""),
        }
        for item in items
    ]


async def get_homework(api_key: str) -> list[dict]:
    session = get_session(api_key)
    response = await _fetch(session.page, f"/api/personen/{session.person_id}/huiswerk?top=50")
    logger.info("Homework raw keys: %s", list(response.keys()) if isinstance(response, dict) else type(response))
    items = response.get("items") or response.get("Items") if isinstance(response, dict) else None
    if not items:
        return [{"error": response}]
    return [
        {
            "vak": (item.get("vak") or item.get("Vak") or {}).get("omschrijving")
            or (item.get("vak") or item.get("Vak") or {}).get("Omschrijving", ""),
            "omschrijving": item.get("omschrijving") or item.get("Omschrijving", ""),
            "datum": (item.get("datumTijd") or item.get("DatumIngevoerd", ""))[:10],
            "klaar": item.get("afgerond") or item.get("Afgerond", False),
        }
        for item in items
    ]


async def get_messages(api_key: str) -> list[dict]:
    session = get_session(api_key)
    response = await _fetch(session.page, "/api/berichten/berichten?top=25")
    logger.info("Messages raw keys: %s", list(response.keys()) if isinstance(response, dict) else type(response))
    items = response.get("items") or response.get("Items") if isinstance(response, dict) else None
    if not items:
        return [{"error": response}]
    return [
        {
            "onderwerp": item.get("onderwerp") or item.get("Onderwerp", ""),
            "afzender": (item.get("afzender") or item.get("Afzender") or {}).get("naam")
            or (item.get("afzender") or item.get("Afzender") or {}).get("Naam", ""),
            "datum": (item.get("verzendDatum") or item.get("VerzendDatum", ""))[:10],
            "gelezen": item.get("isGelezen") or item.get("IsGelezen", False),
        }
        for item in items
    ]


async def get_profile(api_key: str) -> dict:
    session = get_session(api_key)
    response = await _fetch(session.page, "/api/account")
    logger.info("Profile: %s", str(response)[:200])
    if isinstance(response, dict) and "Persoon" in response:
        person = response["Persoon"]
        return {
            "naam": f"{person.get('Roepnaam', '')} {person.get('Tussenvoegsel', '')} {person.get('Achternaam', '')}".strip(),
            "geboortedatum": person.get("Geboortedatum", ""),
            "person_id": person.get("Id", ""),
        }
    return response if isinstance(response, dict) else {}
