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
# WEIGHT DATA
# ──────────────────────────────────────────────

def get_weight(app_token: str, user_id: str, from_date: str, to_date: str) -> list:
    """Fetch body composition records from the Xiaomi smart scale."""
    from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").timestamp())
    to_ts   = int(datetime.strptime(to_date,   "%Y-%m-%d").timestamp()) + 86400

    url = f"https://api-mifit.zepp.com/users/{user_id}/members/-1/weightRecords"
    headers = {"apptoken": app_token}
    params  = {"limit": 200, "toTime": to_ts}

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    if not resp.ok:
        print(f"[!] Weight HTTP {resp.status_code}: {resp.text}")
        return []

    items = resp.json().get("items", [])
    results = []
    for item in items:
        wt = item.get("weightType", -1)
        # 0 = báscula Xiaomi, 7 = entrada manual / Apple Health
        if wt not in (0, 7):
            continue
        if not (from_ts <= item["generatedTime"] <= to_ts):
            continue
        s = item["summary"]
        results.append({
            "date":     datetime.fromtimestamp(item["generatedTime"]).strftime("%Y-%m-%d"),
            "source":   "báscula" if wt == 0 else "manual",
            "weight":   s.get("weight", 0),
            "bmi":      s.get("bmi", 0),
            "fat":      s.get("fatRate", 0),
            "muscle":   s.get("muscleRate", 0),
            "water":    s.get("bodyWaterRate", 0),
            "bone":     s.get("boneMass", 0),
            "visceral": s.get("visceralFat", 0),
            "score":    s.get("bodyScore", 0),
        })
    return sorted(results, key=lambda x: x["date"])


def print_weight(records: list):
    if not records:
        print("[!] Sin datos de báscula en este período.\n")
        return

    W = 72
    print("\n" + "═" * W)
    print(" COMPOSICIÓN CORPORAL (báscula Xiaomi)")
    print("═" * W)
    print(f"{'Fecha':<12} {'Fuente':<8} {'Peso':>5} {'BMI':>5} {'Grasa%':>7} {'Músculo%':>9} {'Agua%':>6} {'Hueso':>6} {'Visceral':>9} {'Score':>6}")
    print("─" * W)
    for r in records:
        fat_s  = f"{r['fat']:.1f}"     if r['fat']     else "—"
        musc_s = f"{r['muscle']:.1f}"  if r['muscle']  else "—"
        water_s= f"{r['water']:.1f}"   if r['water']   else "—"
        bone_s = f"{r['bone']:.2f}"    if r['bone']    else "—"
        visc_s = f"{r['visceral']:.0f}"if r['visceral']else "—"
        score_s= f"{r['score']}"       if r['score']   else "—"
        print(f"{r['date']:<12} {r['source']:<8} {r['weight']:>5.1f} {r['bmi']:>5.1f} {fat_s:>7} {musc_s:>9} {water_s:>6} {bone_s:>6} {visc_s:>9} {score_s:>6}")
    print("═" * W + "\n")


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

def fmt_dur(minutes: int) -> str:
    return f"{minutes // 60}h {minutes % 60}m" if minutes else "—"

def fmt_km(meters: int) -> str:
    return f"{meters / 1000:.2f}" if meters else "—"

def fmt_val(v, suffix="") -> str:
    return f"{v:,}{suffix}" if v else "—"


def parse_and_print(data: dict):
    """Pretty-print the activity summary."""

    if data.get("code") != 1:
        print(f"[!] API error: {data}")
        return

    records = data.get("data", [])
    if not records:
        print("[!] No data returned for this date range.")
        return

    rows = []
    for rec in records:
        date_val = rec.get("date_time", "N/A")
        raw = rec.get("summary", "")
        try:
            summary = json.loads(base64.b64decode(raw + "=="))
        except Exception:
            summary = {}

        stp = summary.get("stp", {})
        slp = summary.get("slp", {})

        # Actividad
        steps    = stp.get("ttl", 0)
        dist_m   = stp.get("dis", 0)
        cal      = stp.get("cal", 0)
        run_m    = stp.get("runDist", 0)
        run_cal  = stp.get("runCal", 0)

        # Sueño
        st, ed   = slp.get("st", 0), slp.get("ed", 0)
        sleep    = (ed - st) // 60 if st and ed else 0
        score    = slp.get("ss", 0)
        rhr      = slp.get("rhr", 0)
        wakeups  = slp.get("wc", 0)
        wake_min = slp.get("wk", 0)

        rows.append({
            "date": date_val,
            "steps": steps, "dist_m": dist_m, "cal": cal,
            "run_m": run_m, "run_cal": run_cal,
            "sleep": sleep, "score": score, "rhr": rhr,
            "wakeups": wakeups, "wake_min": wake_min,
        })

    W = 72
    print("\n" + "═" * W)
    print(" SEGUIMIENTO SEMANAL DE ACTIVIDAD FÍSICA")
    print("═" * W)

    # Cabecera
    print(f"{'Fecha':<12} {'Pasos':>7} {'Dist':>6} {'Cal':>5} {'Corr':>6} {'Sueño':>7} {'Score':>6} {'FCR':>5} {'Desp':>5} {'Min↑':>5}")
    print(f"{'':12} {'':>7} {'km':>6} {'':>5} {'km':>6} {'':>7} {'/100':>6} {'bpm':>5} {'':>5} {'':>5}")
    print("─" * W)

    for r in rows:
        print(
            f"{r['date']:<12}"
            f" {fmt_val(r['steps']):>7}"
            f" {fmt_km(r['dist_m']):>6}"
            f" {fmt_val(r['cal']):>5}"
            f" {fmt_km(r['run_m']):>6}"
            f" {fmt_dur(r['sleep']):>7}"
            f" {fmt_val(r['score']):>6}"
            f" {fmt_val(r['rhr']):>5}"
            f" {fmt_val(r['wakeups']):>5}"
            f" {fmt_val(r['wake_min']):>5}"
        )

    # Promedios
    def avg(key):
        vals = [r[key] for r in rows if r[key]]
        return sum(vals) / len(vals) if vals else 0

    print("─" * W)
    print(
        f"{'MEDIA':<12}"
        f" {avg('steps'):>7,.0f}"
        f" {avg('dist_m')/1000:>6.2f}"
        f" {avg('cal'):>5.0f}"
        f" {avg('run_m')/1000:>6.2f}"
        f" {fmt_dur(int(avg('sleep'))):>7}"
        f" {avg('score'):>6.1f}"
        f" {avg('rhr'):>5.1f}"
        f" {avg('wakeups'):>5.1f}"
        f" {avg('wake_min'):>5.1f}"
    )
    print("═" * W + "\n")


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

    # 3. Mostrar actividad
    parse_and_print(raw)

    # 4. Peso / composición corporal (últimos 10 registros de báscula)
    print("[*] Fetching weight records...")
    weight_records = get_weight(app_token, user_id, "2000-01-01", to_date)
    print_weight(weight_records[-10:] if weight_records else [])

    # 5. Guardar JSON crudo por si quieres procesarlo después
    out_file = f"zepp_activity_{from_date}_{to_date}.json"
    with open(out_file, "w") as f:
        json.dump(raw, f, indent=2)
    print(f"[+] Raw JSON guardado en: {out_file}")
