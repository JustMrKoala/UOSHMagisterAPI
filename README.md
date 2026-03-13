# UOSHMagisterAPI

UOSHMagisterAPI stands for **Unofficial Selfhosted Magister API**.
UOSHMagisterAPI staat voor **Unofficial Selfhosted Magister API**.

## English

UOSHMagisterAPI is a self-hosted FastAPI + Playwright service that logs into Magister in Chromium, keeps that browser session alive behind an API key, and exposes:

- a browser dashboard for humans
- raw JSON routes for scripts and AI tools
- header-authenticated API routes for direct integrations

### Features

- Chromium-backed Magister login flow
- API keys tied to live browser sessions
- browser dashboard at `/ui`
- raw JSON endpoints at `/raw/*`
- AI instruction file at `/llm.txt`
- routes for profile, grades, schedule, absences, homework, and messages

### Requirements

- Windows
- Python 3.13 or another version that matches your local `.venv`
- Playwright Chromium

### Installation

1. Create or activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### Running Locally

Start the server with:

```bash
python run.py
```

`run.py` tries to use the local `.venv` automatically. If startup fails, it keeps the console open so the error stays visible.

### Main URLs

#### Browser dashboard

```text
http://127.0.0.1:8000/ui
```

Use it to:

- log in with Magister credentials
- create and reuse API keys
- open the linked Chromium session for a key
- inspect JSON output without curl

#### Swagger docs

```text
http://127.0.0.1:8000/docs
```

#### AI instructions

```text
http://127.0.0.1:8000/llm.txt
```

Give an AI tool this URL together with the user's API key.

#### Combined raw JSON

```text
http://127.0.0.1:8000/raw/overview?api_key=YOUR_API_KEY
```

#### Individual raw JSON routes

```text
http://127.0.0.1:8000/raw/profile?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/grades?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/schedule?api_key=YOUR_API_KEY&date=YYYY-MM-DD
http://127.0.0.1:8000/raw/absences?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/homework?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/messages?api_key=YOUR_API_KEY
```

### Session Model

- `POST /login` creates a live Chromium-backed Magister session
- the returned API key is tied to that browser session
- closing the Chromium page or context invalidates that key
- `POST /ui/open-browser` can reopen or focus the linked browser view for a key

### Authentication

Two authentication styles are supported:

- header-based routes use `X-API-Key`
- raw JSON routes use the `api_key` query parameter

Example:

```text
http://127.0.0.1:8000/raw/overview?api_key=YOUR_API_KEY
```

### API Overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/login` | Log in and create an API key |
| POST | `/logout` | Revoke the current API key |
| GET | `/sessions` | List active sessions without full API keys |
| GET | `/ui` | Browser dashboard |
| GET | `/ui/api/sessions` | Dashboard session list with full API keys |
| POST | `/ui/open-browser?api_key=...&path=/...` | Open or focus the linked Chromium page |
| GET | `/llm.txt` | AI instructions for querying the API |
| GET | `/raw/overview?api_key=...` | Combined raw JSON snapshot |
| GET | `/raw/profile?api_key=...` | Raw profile JSON |
| GET | `/raw/grades?api_key=...` | Raw grades JSON |
| GET | `/raw/schedule?api_key=...&date=YYYY-MM-DD` | Raw schedule JSON |
| GET | `/raw/absences?api_key=...` | Raw absences JSON |
| GET | `/raw/homework?api_key=...` | Raw homework JSON |
| GET | `/raw/messages?api_key=...` | Raw messages JSON |
| GET | `/profile` | Header-authenticated profile endpoint |
| GET | `/grades` | Header-authenticated grades endpoint |
| GET | `/schedule?date=YYYY-MM-DD` | Header-authenticated schedule endpoint |
| GET | `/absences` | Header-authenticated absences endpoint |
| GET | `/homework` | Header-authenticated homework endpoint |
| GET | `/messages` | Header-authenticated messages endpoint |

### AI Tooling

`/llm.txt` is designed for tools like ChatGPT. It explains:

- how to derive the base URL
- how to authenticate
- which raw routes to call
- how the tool should convert raw JSON into human-friendly answers

Recommended starting route for AI tools:

```text
/raw/overview?api_key=YOUR_API_KEY
```

### Headless Mode

If you want the browser to run without a visible window, change this in `app/magister_session.py`:

```python
_browser = await _playwright.chromium.launch(headless=False, args=["--start-maximized"])
```

to:

```python
_browser = await _playwright.chromium.launch(headless=True, args=["--start-maximized"])
```

### Security Notes

- Do not commit real Magister credentials
- Do not commit real API keys
- API keys only remain valid while their linked Chromium session is alive
- Treat the dashboard and raw routes as sensitive local access points

### Repository Hygiene

Before publishing this repository, make sure you do not include:

- `.env`
- cached credentials
- browser profile data
- unnecessary local folders such as `.venv`, `.venv_old`, `.tmp`, and `.idea`

### License

Add a license before publishing if you plan to release the project publicly.

## Nederlands

UOSHMagisterAPI is een self-hosted FastAPI + Playwright-service die inlogt op Magister via Chromium, die browsersessie actief houdt achter een API-key, en het volgende aanbiedt:

- een browserdashboard voor mensen
- raw JSON-routes voor scripts en AI-tools
- header-geauthenticeerde API-routes voor directe integraties

### Functies

- Inlogflow voor Magister via Chromium
- API-keys die gekoppeld zijn aan live browsersessies
- browserdashboard op `/ui`
- raw JSON-endpoints op `/raw/*`
- AI-instructiebestand op `/llm.txt`
- routes voor profiel, cijfers, rooster, afwezigheden, huiswerk en berichten

### Vereisten

- Windows
- Python 3.13 of een andere versie die overeenkomt met je lokale `.venv`
- Playwright Chromium

### Installatie

1. Maak of activeer een virtual environment.
2. Installeer de dependencies:

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### Lokaal starten

Start de server met:

```bash
python run.py
```

`run.py` probeert automatisch de lokale `.venv` te gebruiken. Als opstarten mislukt, blijft de console open zodat je de foutmelding kunt lezen.

### Belangrijkste URL's

#### Browserdashboard

```text
http://127.0.0.1:8000/ui
```

Gebruik dit om:

- in te loggen met Magister-gegevens
- API-keys aan te maken en opnieuw te gebruiken
- de gekoppelde Chromium-sessie voor een key te openen
- JSON-uitvoer te bekijken zonder curl

#### Swagger-documentatie

```text
http://127.0.0.1:8000/docs
```

#### AI-instructies

```text
http://127.0.0.1:8000/llm.txt
```

Geef een AI-tool deze URL samen met de API-key van de gebruiker.

#### Gecombineerde raw JSON

```text
http://127.0.0.1:8000/raw/overview?api_key=YOUR_API_KEY
```

#### Losse raw JSON-routes

```text
http://127.0.0.1:8000/raw/profile?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/grades?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/schedule?api_key=YOUR_API_KEY&date=YYYY-MM-DD
http://127.0.0.1:8000/raw/absences?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/homework?api_key=YOUR_API_KEY
http://127.0.0.1:8000/raw/messages?api_key=YOUR_API_KEY
```

### Sessiemodel

- `POST /login` maakt een live Chromium-gebaseerde Magister-sessie aan
- de teruggegeven API-key is gekoppeld aan die browsersessie
- als de Chromium-pagina of context sluit, wordt die key ongeldig
- `POST /ui/open-browser` kan de gekoppelde browserweergave opnieuw openen of naar voren halen

### Authenticatie

Er zijn twee authenticatiestijlen:

- header-routes gebruiken `X-API-Key`
- raw JSON-routes gebruiken de queryparameter `api_key`

Voorbeeld:

```text
http://127.0.0.1:8000/raw/overview?api_key=YOUR_API_KEY
```

### API-overzicht

| Methode | Pad | Beschrijving |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/login` | Inloggen en een API-key aanmaken |
| POST | `/logout` | De huidige API-key intrekken |
| GET | `/sessions` | Actieve sessies zonder volledige API-keys |
| GET | `/ui` | Browserdashboard |
| GET | `/ui/api/sessions` | Dashboard-overzicht met volledige API-keys |
| POST | `/ui/open-browser?api_key=...&path=/...` | De gekoppelde Chromium-pagina openen of focussen |
| GET | `/llm.txt` | AI-instructies voor deze API |
| GET | `/raw/overview?api_key=...` | Gecombineerde raw JSON-snapshot |
| GET | `/raw/profile?api_key=...` | Raw profiel-JSON |
| GET | `/raw/grades?api_key=...` | Raw cijfers-JSON |
| GET | `/raw/schedule?api_key=...&date=YYYY-MM-DD` | Raw rooster-JSON |
| GET | `/raw/absences?api_key=...` | Raw afwezigheden-JSON |
| GET | `/raw/homework?api_key=...` | Raw huiswerk-JSON |
| GET | `/raw/messages?api_key=...` | Raw berichten-JSON |
| GET | `/profile` | Profiel-endpoint met header-authenticatie |
| GET | `/grades` | Cijfers-endpoint met header-authenticatie |
| GET | `/schedule?date=YYYY-MM-DD` | Rooster-endpoint met header-authenticatie |
| GET | `/absences` | Afwezigheden-endpoint met header-authenticatie |
| GET | `/homework` | Huiswerk-endpoint met header-authenticatie |
| GET | `/messages` | Berichten-endpoint met header-authenticatie |

### AI-gebruik

`/llm.txt` is bedoeld voor tools zoals ChatGPT. Het legt uit:

- hoe de basis-URL bepaald wordt
- hoe authenticatie werkt
- welke raw routes aangeroepen moeten worden
- hoe ruwe JSON omgezet moet worden naar mensvriendelijke antwoorden

Aanbevolen startroute voor AI-tools:

```text
/raw/overview?api_key=YOUR_API_KEY
```

### Headless-modus

Als je wilt dat de browser zonder zichtbaar venster draait, verander dit in `app/magister_session.py`:

```python
_browser = await _playwright.chromium.launch(headless=False, args=["--start-maximized"])
```

naar:

```python
_browser = await _playwright.chromium.launch(headless=True, args=["--start-maximized"])
```

### Beveiligingsnotities

- Commit geen echte Magister-inloggegevens
- Commit geen echte API-keys
- API-keys blijven alleen geldig zolang hun gekoppelde Chromium-sessie actief is
- Behandel het dashboard en de raw routes als gevoelige lokale toegangspunten

### Repository-hygiëne

Controleer vóór publicatie dat je dit niet meeneemt:

- `.env`
- gecachte credentials
- browserprofieldata
- onnodige lokale mappen zoals `.venv`, `.venv_old`, `.tmp` en `.idea`

### Licentie

Voeg een licentie toe voordat je het project publiek op GitHub publiceert.
