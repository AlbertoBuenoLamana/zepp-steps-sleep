#!/usr/bin/env python3
"""
Zepp / Huami Unofficial API Client
Fetches activity data (steps, calories, distance, sleep) from Huami servers.
"""

import requests
import json
import sys
import time
import re
import os
import subprocess
import base64
from datetime import datetime, timedelta
from typing import Optional

# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

# Europe endpoint — change to api-mifit-us.huami.com for US accounts
DATA_URL = "https://api-mifit-de2.huami.com/v1/data/band_data.json"


def login(email: str, password: str) -> dict:
    """
    Authenticate with Huami/Zepp servers using the 2-step flow (2024/2025).
    Step 1: POST to api-user.huami.com/registrations/{email}/tokens → access code
    Step 2: POST to account.huami.com/v2/client/login → app_token + user_id
    """

    # ── Step 1: get access code ───────────────────────────────────────────────
    step1_url = f"https://api-user.huami.com/registrations/{requests.utils.quote(email)}/tokens"
    step1_headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "User-Agent":   "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15",
    }
    step1_data = {
        "client_id":    "HuaMi",
        "password":     password,
        "redirect_uri": "https://s3-us-west-2.amazonaws.com/hm-registration/successsignin.html",
        "token":        "access",
    }

    print(f"[*] Step 1 — Getting access code for {email}...")
    for attempt in range(1, 5):
        r1 = requests.post(step1_url, data=step1_data, headers=step1_headers,
                           allow_redirects=False, timeout=15)
        if r1.status_code != 429:
            break
        wait = attempt * 30
        print(f"[!] 429 rate limited — esperando {wait}s (intento {attempt}/4)...")
        time.sleep(wait)
    else:
        print("[!] Step 1 sigue fallando con 429 tras 4 intentos. Espera unos minutos.")
        sys.exit(1)

    # The response is a 303 redirect; access token is in the Location header
    location = r1.headers.get("Location", "")
    if not location:
        print(f"[!] Step 1 failed — status {r1.status_code}")
        print(f"    Body: {r1.text}")
        sys.exit(1)

    match = re.search(r"access=([^&]+)", location)
    if not match:
        print(f"[!] Could not parse access code from: {location}")
        sys.exit(1)

    access_code = match.group(1)
    country_code = re.search(r"country_code=([^&]+)", location)
    country_code = country_code.group(1) if country_code else "ES"
    print(f"[+] Step 1 OK — country_code={country_code}")

    # ── Step 2: exchange access code for app_token ────────────────────────────
    step2_url = "https://account.huami.com/v2/client/login"
    step2_headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Origin":     "https://user.zepp.com",
        "Referer":    "https://user.zepp.com/",
        "app_name":   "com.huami.webapp",
    }
    step2_data = {
        "app_name":           "com.xiaomi.hm.health",
        "dn":                 "account.huami.com,api-user.huami.com,api-watch.huami.com,"
                              "api-analytics.huami.com,app-analytics.huami.com,api-mifit.huami.com",
        "device_id":          "02:00:00:00:00:00",
        "device_model":       "android_phone",
        "app_version":        "6.3.0",
        "allow_registration": "false",
        "third_name":         "huami",
        "grant_type":         "access_token",
        "country_code":       country_code,
        "code":               access_code,
    }

    print(f"[*] Step 2 — Exchanging code for app_token...")
    r2 = requests.post(step2_url, data=step2_data, headers=step2_headers, timeout=15)

    if r2.status_code != 200:
        print(f"[!] Step 2 failed — status {r2.status_code}")
        print(f"    Body: {r2.text}")
        sys.exit(1)

    data = r2.json()
    if "token_info" not in data:
        print(f"[!] Step 2 unexpected response: {json.dumps(data, indent=2)}")
        sys.exit(1)

    token_info = data["token_info"]
    print(f"[+] Logged in! user_id = {token_info['user_id']}")
    return token_info


# ──────────────────────────────────────────────
# TOKEN RENEWAL
# ──────────────────────────────────────────────

def renew_token(email: str, password: str, env_file: str) -> str:
    """Renueva el app_token usando huami-token y actualiza el .env."""
    huami_bin = os.path.join(os.path.dirname(__file__), "venv", "bin", "huami-token")
    print("[*] Token expirado — renovando automáticamente...")
    result = subprocess.run(
        [huami_bin, "--method", "amazfit", "--email", email, "--password", password, "--no_logout"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    match = re.search(r"^app_token=(.+)$", output, re.MULTILINE)
    if not match:
        print("[!] No se pudo renovar el token:\n" + output)
        sys.exit(1)
    new_token = match.group(1).strip()
    # Actualizar .env
    with open(env_file) as f:
        content = f.read()
    content = re.sub(r"^ZEPP_TOKEN=.*$", f"ZEPP_TOKEN={new_token}", content, flags=re.MULTILINE)
    with open(env_file, "w") as f:
        f.write(content)
    print(f"[+] Token renovado y guardado en .env")
    return new_token


# ──────────────────────────────────────────────
# ACTIVITY DATA
# ──────────────────────────────────────────────

def get_activity(app_token: str, user_id: str,
                 from_date: str, to_date: str,
                 query_type: str = "summary") -> dict:
    """
    Fetch band activity data.
    query_type: 'summary' | 'detail'
    dates: 'YYYY-MM-DD'
    """
    headers = {
        "AppPlatform": "web",
        "appname":     "com.xiaomi.hm.health",
        "apptoken":    app_token,
    }
    params = {
        "query_type":  query_type,
        "device_type": "android_phone",
        "userid":      user_id,
        "from_date":   from_date,
        "to_date":     to_date,
    }

    print(f"[*] Fetching activity ({query_type}) from {from_date} to {to_date}...")
    resp = requests.get(DATA_URL, headers=headers, params=params, timeout=15)
    if not resp.ok:
        print(f"[!] HTTP {resp.status_code}: {resp.text}")
        resp.raise_for_status()
    return resp.json()


# ──────────────────────────────────────────────
# DISPLAY
# ──────────────────────────────────────────────

def parse_and_print(data: dict):
    """Pretty-print the activity summary."""
    import base64

    if data.get("code") != 1:
        print(f"[!] API error: {data}")
        return

    records = data.get("data", [])
    if not records:
        print("[!] No data returned for this date range.")
        return

    print("\n" + "═" * 38)
    print(f"{'Fecha':<12} {'Pasos':>10} {'Sueño':>10}")
    print("─" * 38)

    for rec in records:
        date_val = rec.get("date_time", "N/A")
        raw = rec.get("summary", "")
        try:
            summary = json.loads(base64.b64decode(raw + "=="))
        except Exception:
            summary = {}

        stp = summary.get("stp", {})
        slp = summary.get("slp", {})

        steps = stp.get("ttl", 0)
        st, ed = slp.get("st", 0), slp.get("ed", 0)
        sleep = (ed - st) // 60 if st and ed else 0
        sleep_s = f"{sleep // 60}h {sleep % 60}m" if sleep else "—"

        print(f"{date_val:<12} {steps:>10,} {sleep_s:>10}")

    print("═" * 38)
    print(f"Total records: {len(records)}\n")


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import os

    # Cargar .env si existe
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    parser = argparse.ArgumentParser(description="Zepp activity fetcher")
    parser.add_argument("--token",    default=os.environ.get("ZEPP_TOKEN"),    help="app_token directo (salta login)")
    parser.add_argument("--userid",   default=os.environ.get("ZEPP_USERID"),   help="user_id directo (salta login)")
    parser.add_argument("--email",    default=os.environ.get("ZEPP_EMAIL"),    help="Email Zepp")
    parser.add_argument("--password", default=os.environ.get("ZEPP_PASSWORD"), help="Password Zepp")
    parser.add_argument("--days",     type=int, default=7, help="Días hacia atrás (default: 7)")
    args = parser.parse_args()

    to_date   = datetime.today().strftime("%Y-%m-%d")
    from_date = (datetime.today() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    email    = args.email    or input("Email Zepp: ")
    password = args.password or input("Password:   ")

    if args.token and args.userid:
        print(f"[+] Usando token directo, user_id={args.userid}")
        app_token = args.token
        user_id   = args.userid
    else:
        token_info = login(email, password)
        app_token  = token_info["app_token"]
        user_id    = str(token_info["user_id"])

    # 2. Obtener actividad (con auto-renovación de token si expira)
    try:
        raw = get_activity(app_token, user_id, from_date, to_date)
    except Exception:
        app_token = renew_token(email, password, env_file)
        raw = get_activity(app_token, user_id, from_date, to_date)

    # Debug: ver estructura completa si falla
    # print(json.dumps(raw, indent=2))

    # 3. Mostrar
    parse_and_print(raw)

    # 4. Guardar JSON crudo por si quieres procesarlo después
    out_file = f"zepp_activity_{from_date}_{to_date}.json"
    with open(out_file, "w") as f:
        json.dump(raw, f, indent=2)
    print(f"[+] Raw JSON guardado en: {out_file}")
