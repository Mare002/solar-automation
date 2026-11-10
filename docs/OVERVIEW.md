# Solar Sales Automation: project overview

**From a website visit to a PDF quote in the customer's inbox in about a minute, with the lead already in the CRM.**

## The problem

A small solar installer gets requests through a website form, phone or email. For each one, a salesperson asks the
same questions, works out the system size and price in a spreadsheet, writes a quote, emails it and copies everything
into the CRM. That is typically one to three hours per lead (estimate), and the customer often waits days. Many
requests never become customers, so most of that time is spent on people who were only curious.

## What this project does

- **Two ways in:** a web form, or an AI chat assistant that asks the same eight questions in Slovak or English, one
  at a time, and shows a summary to confirm.
- **Instant calculation:** system size, number of panels, yearly production, price (with or without a battery),
  yearly savings and payback, based on consumption, the region's solar yield and the roof orientation.
- **PDF quote by email** to the customer, in Slovak, usually within a minute.
- **CRM updated automatically:** a new opportunity in Odoo with all numbers, the PDF attached and the stage set to
  *Proposition*, so the salesperson starts from a complete card.
- **Unusual requests go to a person:** low-confidence results (for example a north roof, very high consumption, an
  unknown region) or calculator errors get a *Manual review* tag and an email to sales instead of an automatic offer.
- **Nothing fails silently:** if any step breaks (CRM, PDF, email), an alert email names the step, the error and links
  to the failed run.

## How it is built

| Layer | Tool | Role |
|---|---|---|
| Website | HTML/CSS | Fictional installer site with quote and chat buttons |
| Workflows | n8n, self-hosted | Form, chatbot, the shared Quote Pipeline, error alerts |
| AI | n8n AI Agent + Groq (Qwen 3.8 27B) | Conversation only; never trusted with the final values |
| Business logic | Python, FastAPI | Sizing, pricing, ROI, confidence score, PDF (ReportLab) |
| CRM | Odoo 19 Community, PostgreSQL | Opportunities, stages, attachments, tags |
| Infrastructure | Docker Compose | Four containers, runs on a laptop or a small server |

Design decisions worth noting:

- **One pipeline for every channel.** The form and the chatbot call the same sub-workflow, so a fix or a new rule
  applies to both.
- **The AI collects, rules decide.** A language model can invent answers. Every value passes a deterministic check
  (allowed options, real email, kWh range, name and surname, the customer's own "yes") before anything is created.
  In testing, an early version without this check created a quote from made-up data; with it, such calls are
  rejected and nothing is created.
- **Calculation in Python, not in the workflow tool.** The numbers live in one tested module (14 automated tests)
  instead of being spread over workflow expressions.
- **No silent defaults.** Missing or misnamed fields return an error instead of a believable but wrong quote, after
  exactly that bug was found and fixed during the build.

## What it would save an installer

| | Manual process (estimate) | With the pipeline |
|---|---|---|
| Time to the customer's first quote | hours to days | about 1 minute |
| Salesperson time per lead before the first call | 1–3 hours | none; review only unusual leads |
| Data typed into the CRM | by hand | automatic, with the PDF attached |
| Availability | office hours | 24/7 |

The salesperson's time goes to site visits and to customers who already have a price and still want to talk.

## Status and limits

Working prototype, tested end to end on 9–10 November 2026 (form, chat, manual review, error alert). Limits:
prices and yields are placeholder values, the AI runs on Groq's free tier (a token-per-minute limit that a paid tier
removes), and the form and PDF are in English while the emails and chat are Slovak.

Possible next steps: Slovak form and PDF, installer branding from configuration, live solar data (PVGIS),
e-signature, hosting on a small VPS.
