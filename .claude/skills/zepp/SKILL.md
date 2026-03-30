---
name: zepp
description: Guide the user to run the Zepp/Huami activity tracker script from the zepp-steps-sleep repo. Use when the user asks how to get their step/sleep/weight data from their Xiaomi band or Zepp app.
---

Help the user run the Zepp activity tracker from the `zepp-steps-sleep` repo (https://github.com/AlbertoBuenoLamana/zepp-steps-sleep).

First, read the current working directory context to find where the repo is cloned, then guide accordingly.

## Quick start

### 1. Check credentials

Credentials live in `.env` inside the repo. If it doesn't exist yet, copy from `.env.example` and fill in:
- `ZEPP_TOKEN` and `ZEPP_USERID` — get these with `huami-token` (see below)
- `ZEPP_EMAIL` and `ZEPP_PASSWORD` — needed for auto token renewal

### 2. Get a fresh token (if needed)

Tokens expire in minutes. Run this from the repo root:
```bash
venv/bin/huami-token --method amazfit --email YOUR_EMAIL --password YOUR_PASSWORD --no_logout
```
Copy `app_token` → `ZEPP_TOKEN` and `user_id` → `ZEPP_USERID` into `.env`.

The script auto-renews the token if `ZEPP_EMAIL` and `ZEPP_PASSWORD` are set in `.env`.

### 3. Run the script

```bash
# Last 7 days, English (default)
venv/bin/python3 zepp_client.py

# Last 30 days
venv/bin/python3 zepp_client.py --days 30

# Spanish output
venv/bin/python3 zepp_client.py --lang es

# Last 14 days in Spanish
venv/bin/python3 zepp_client.py --days 14 --lang es
```

### 4. What you'll see

- **Weekly activity table**: steps, distance (km), calories, running distance, sleep duration, sleep score (/100), resting heart rate (bpm), wake-ups, minutes awake
- **Body composition table**: weight, BMI, fat%, muscle%, water%, bone mass, visceral fat, score — from the Xiaomi scale or manual entries in the Zepp app

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `401 Unauthorized` | Token expired — auto-renews if email+password are in `.env` |
| `ModuleNotFoundError` | Run `venv/bin/pip install huami-token requests` |
| All zeros in activity | Token likely invalid — get a fresh one with `huami-token` |
| Weight data missing | Requires Xiaomi Mi Body Composition Scale or manual weight entries in Zepp app |
| `venv` not found | Run `python3 -m venv venv && venv/bin/pip install huami-token requests` |

## How it works

1. Reads credentials from `.env`
2. Calls `api-mifit-de2.huami.com` for activity data (steps, sleep, heart rate)
3. Calls `api-mifit.zepp.com` for weight and body composition data
4. Prints formatted tables to terminal
