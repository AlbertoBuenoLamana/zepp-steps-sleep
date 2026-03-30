# zepp-steps-sleep

> 🇪🇸 [Versión en español](README_ES.md)

Unofficial Python client to extract **activity, sleep and body composition data** from Huami/Zepp servers (Xiaomi, Amazfit) without using the official app.

## What it does

- Authenticates with Huami servers using your Zepp/Amazfit account
- Downloads daily activity summaries for the last N days
- Displays a **weekly physical tracker** table: steps, distance, calories, running distance, sleep duration, sleep score, resting heart rate and wake-up quality
- Fetches **weight and body composition history** from the Xiaomi Mi Body Composition Scale (body fat, muscle mass, water, bone mass, visceral fat, body score)
- Also shows **manually entered weight** from the app
- Automatically renews the session token when it expires
- Saves raw data to a local JSON file

## Requirements

- Python 3.12+
- Zepp/Amazfit account with email and password (Google/Apple login not supported)
- Xiaomi Mi Body Composition Scale (optional, for full body composition data)

## Installation

```bash
git clone https://github.com/AlbertoBuenoLamana/zepp-steps-sleep.git
cd zepp-steps-sleep
python3 -m venv venv
venv/bin/pip install huami-token requests
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Get your `app_token` and `user_id` with:

```bash
venv/bin/huami-token --method amazfit --email you@email.com --password yourpassword --no_logout
```

Copy the `app_token` and `user_id` values into `.env`.

> The token expires in minutes, but the script renews it automatically if `ZEPP_EMAIL` and `ZEPP_PASSWORD` are set in `.env`.

## Usage

```bash
# Last 7 days (default), English output
venv/bin/python3 zepp_client.py

# Last 30 days
venv/bin/python3 zepp_client.py --days 30

# Spanish output
venv/bin/python3 zepp_client.py --lang es
```

### Sample output

```
════════════════════════════════════════════════════════════════════════
 WEEKLY PHYSICAL ACTIVITY TRACKER
════════════════════════════════════════════════════════════════════════
Date           Steps   Dist   Cal    Run   Sleep  Score   RHR  Wake  WMin
                         km           km           /100   bpm
────────────────────────────────────────────────────────────────────────
2026-03-23     8,091   6.39   292   4.85  7h 48m     94    56     —     —
2026-03-24     8,765   6.97   304   5.27   6h 6m     73    56     —     —
2026-03-25    10,513   8.40   360   6.38  6h 55m     79    54     —     —
2026-03-27    12,347   9.17   360   7.05  6h 28m     87    57     1     3
2026-03-28    18,460  13.42   515  10.20       —      —     —     —     —
2026-03-29     6,936   5.15   220   3.93  8h 58m     73    57     3    62
────────────────────────────────────────────────────────────────────────
AVG            9,807   7.48   313   5.68   7h 6m   83.3  56.1   2.0  32.5
════════════════════════════════════════════════════════════════════════

════════════════════════════════════════════════════════════════════════════════
 BODY COMPOSITION (Xiaomi scale)
════════════════════════════════════════════════════════════════════════════════
Date         Source    Weight   BMI    Fat%  Muscle%   Water%   Bone  Visceral  Score
────────────────────────────────────────────────────────────────────────────────
2026-03-01   manual      89.9  28.7       —        —        —      —         —      —
2023-11-21   scale       73.0  23.3    20.5     55.0     54.5   2.95         9     88
════════════════════════════════════════════════════════════════════════════════
```

### Activity columns

| Column | Description |
|--------|-------------|
| Steps | Total daily steps |
| Dist km | Total distance walked/run |
| Cal | Calories burned |
| Run km | Running distance only |
| Sleep | Sleep duration (start → end) |
| Score /100 | Sleep score from the device |
| RHR bpm | Resting heart rate (lower = better fitness) |
| Wake | Number of times you woke up |
| WMin | Minutes awake during the night |

### Body composition columns

| Column | Description |
|--------|-------------|
| Source | `scale` (Xiaomi) or `manual` (entered in app) |
| Weight | Weight in kg |
| BMI | Body mass index |
| Fat% | Body fat percentage |
| Muscle% | Muscle mass percentage |
| Water% | Body water percentage |
| Bone | Bone mass in kg |
| Visceral | Visceral fat level |
| Score | Overall body score |

## Notes

- Default endpoint is European (`api-mifit-de2.huami.com`). For US accounts, change `DATA_URL` to `api-mifit-us.huami.com`.
- Sleep duration is calculated from the band's start/end timestamps.
- Full body composition data (fat, muscle, etc.) requires the Xiaomi Mi Body Composition Scale; manual entries only record weight and BMI.
- Always shows the last 10 weight records regardless of the activity date range.
