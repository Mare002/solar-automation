# Solar Sales Automation — setup on a new machine

Status: **Fully rebuilt on new machine** (2026-09-17). Python API, Docker stack,
n8n workflows, and Odoo database have been recreated and tested end-to-end.
Complete workflow verified: form submission → Odoo opportunity creation →
solar system calculation → PDF proposal generation with customer data.

---

## 1. Install

| Tool | Why | Link |
|---|---|---|
| Docker Desktop | runs all four containers | https://www.docker.com/products/docker-desktop/ |
| Python 3.12+ | only if you want to run the API outside Docker | https://www.python.org/downloads/ |
| Git | version control | https://git-scm.com/downloads |
| PyCharm Community | editing the Python modules | https://www.jetbrains.com/pycharm/ |

On Windows, Docker Desktop needs WSL2 enabled. Reboot after install and
confirm `docker version` responds before continuing.

Free account needed: **Groq** — https://console.groq.com — the old API key is
gone with the old machine, generate a new one.

## 2. Configure

```powershell
cd "<...>\Sales Automation Kit for Solar Installers, project 1\PyCharmMiscProject\solar-automation"
copy .env.example .env
```

Open `.env` and:

1. Set a real `POSTGRES_PASSWORD`.
2. Generate `N8N_ENCRYPTION_KEY`:
   ```powershell
   [Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
   ```
   **Save this key in a password manager.** It is what makes every future
   credential backup restorable. Losing it is how the old setup became
   unrecoverable.

## 3. Start the stack

```powershell
docker compose up -d --build
```

First boot pulls ~1.5 GB and takes 2–4 minutes. Then check:

| Service | URL | First-run action |
|---|---|---|
| Odoo | http://localhost:8069 | create database — name it `solar`, note the master password |
| n8n | http://localhost:5678 | create the owner account (email + password) |
| Solar API | http://localhost:8000/health | should return `{"status":"ok",...}` |
| API docs | http://localhost:8000/docs | interactive test of `/calculate` |

If you have a `.\backup\` folder from a previous machine, run
`.\restore.ps1` instead of rebuilding section 4 by hand.

## 4. Rebuild the parts that were lost

### 4.1 Odoo

- Install the **CRM** app.
- Set pipeline stages: `Nový lead → Kvalifikácia → Ponuka odoslaná → Zmluva → Realizácia`.
- Settings → General Settings → Developer Tools → activate developer mode.
- Create an API user for n8n and generate an API key
  (Settings → Users → *user* → Account Security → New API Key).

### 4.2 n8n credentials

- **Groq** — paste the new API key.
- **Odoo** — URL `http://odoo:8069`, database `solar`, the API user + key above.

### 4.3 n8n workflows

Two workflows to rebuild — full node-by-node spec in the Obsidian note.
The one thing that trips people up:

> Inside the Docker network, containers reach each other by **service name**,
> not `localhost`. From an n8n HTTP Request node the API is
> `http://solar_api:8000/generate-proposal` and Odoo is `http://odoo:8069`.
> `http://localhost:8000` only works from your browser.

## 5. Back up — every session

```powershell
.\backup.ps1
git add backup/workflows.json && git commit -m "backup: n8n workflows"
```

`backup/workflows.json` is safe to commit. `backup/credentials.json` is
encrypted but still don't commit it — it's in `.gitignore`.

## 6. Push to GitHub

```powershell
git add .
git commit -m "Update API field names and add orientation support; verify end-to-end workflow"
git push origin main
```

## Files

```
docker-compose.yml     four services: postgres, odoo, n8n, solar_api
Dockerfile             builds the Python API image
requirements.txt       fastapi, uvicorn, reportlab, pydantic
.env.example           template - copy to .env
solar_calculator.py    sizing, pricing, ROI, confidence score
proposal_generator.py  ReportLab PDF proposal
api_server.py          FastAPI: /calculate, /generate-proposal, /health, /download
backup.ps1             export n8n workflows + credentials + Odoo dump
restore.ps1            import them back on a new machine
backup/                the exports themselves
```

## Verified

**2026-09-17** — End-to-end workflow tested successfully:
- Form submission accepted and parsed correctly
- Odoo opportunity created with customer and system data
- `/calculate` endpoint returned solar system specs for south-facing sloped-roof case
- `/generate-proposal` generated PDF with actual customer name and email embedded
- Orientation coefficients expanded: now supports south, southwest, southeast, west, east, north, northeast, northwest
- All customer data (name, email, phone) flows correctly from form → n8n → API → PDF

Recent fixes:
- Fixed `api_server.py` ProposalRequest field names to match n8n output (customer_name, customer_email, customer_phone)
- Added northeast (0.80) and northwest (0.80) to orientation_coefficient dict in `solar_calculator.py`
- Both changes deployed and verified with Docker rebuild
