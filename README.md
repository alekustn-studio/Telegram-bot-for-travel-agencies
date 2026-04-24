# France visa — Telegram assistant

A **Telegram** assistant built for a visa workflow: it introduces **France visa** basics, delivers a **PDF guide** on request, and collects **structured contact requests** (phone or username, name, short context) so an agent can reply. New requests trigger **notifications** in a dedicated Telegram chat, and submissions are stored in a local **SQLite** database.

**Stack:** Python, Telegram Bot API, SQLite.

## What the bot does

- **Welcome** on `/start` with a short explanation of the flow  
- **Menu** with two paths:
  - **France visa info** — sends the PDF guide, then a follow-up message with next steps  
  - **Contact the agent** — step-by-step collection of contact details and a short free-text note  
- **Validation** of phone numbers and Telegram usernames where applicable  
- **Persistence** of each submission for the team  
- **Private chat alerts** when someone completes a contact request  

Copy and operational setup (tokens, hosting, PDF placement, launch agents) are handled outside this readme — the repo is mainly a **reference for stakeholders** on what was delivered and how the product behaves, not a public runbook for cloning the whole stack.
