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
# I18N
# ──────────────────────────────────────────────

STRINGS = {
    "en": {
        "step1":          "[*] Step 1 — Getting access code for {}...",
        "rate_limited":   "[!] 429 rate limited — waiting {}s (attempt {}/4)...",
        "rate_give_up":   "[!] Step 1 still failing with 429 after 4 attempts. Wait a few minutes.",
        "step1_failed":   "[!] Step 1 failed — status {}",
        "step1_ok":       "[+] Step 1 OK — country_code={}",
        "step2":          "[*] Step 2 — Exchanging code for app_token...",
        "step2_failed":   "[!] Step 2 failed — status {}",
        "step2_body":     "    Body: {}",
        "step2_unexpected":"[!] Step 2 unexpected response: {}",
        "logged_in":      "[+] Logged in! user_id = {}",
        "token_expired":  "[*] Token expired — renewing automatically...",
        "token_renewed":  "[+] Token renewed and saved to .env",
        "token_error":    "[!] Could not renew token:\n{}",
        "using_token":    "[+] Using direct token, user_id={}",
        "fetching":       "[*] Fetching activity ({}) from {} to {}...",
        "http_error":     "[!] HTTP {}: {}",
        "fetching_weight":"[*] Fetching weight records...",
        "no_weight":      "[!] No weight data found.\n",
        "no_data":        "[!] No data returned for this date range.",
        "api_error":      "[!] API error: {}",
        "saved":          "[+] Raw JSON saved to: {}",
        "email_prompt":   "Zepp email: ",
        "pass_prompt":    "Password:   ",
        "activity_title": " WEEKLY PHYSICAL ACTIVITY TRACKER",
        "weight_title":   " BODY COMPOSITION (Xiaomi scale)",
        "avg_label":      "AVG",
        "col_date":       "Date",
        "col_steps":      "Steps",
        "col_dist":       "Dist",
        "col_cal":        "Cal",
        "col_run":        "Run",
        "col_sleep":      "Sleep",
        "col_score":      "Score",
        "col_rhr":        "RHR",
        "col_wake":       "Wake",
        "col_wmin":       "WMin",
        "col_weight":     "Weight",
        "col_bmi":        "BMI",
        "col_fat":        "Fat%",
        "col_muscle":     "Muscle%",
        "col_water":      "Water%",
        "col_bone":       "Bone",
        "col_visceral":   "Visceral",
        "col_source":     "Source",
        "src_scale":      "scale",
        "src_manual":     "manual",
    },
    "es": {
        "step1":          "[*] Paso 1 — Obteniendo código de acceso para {}...",
        "rate_limited":   "[!] 429 rate limited — esperando {}s (intento {}/4)...",
        "rate_give_up":   "[!] Paso 1 sigue fallando con 429 tras 4 intentos. Espera unos minutos.",
        "step1_failed":   "[!] Paso 1 fallido — estado {}",
        "step1_ok":       "[+] Paso 1 OK — country_code={}",
        "step2":          "[*] Paso 2 — Intercambiando código por app_token...",
        "step2_failed":   "[!] Paso 2 fallido — estado {}",
        "step2_body":     "    Body: {}",
        "step2_unexpected":"[!] Respuesta inesperada en paso 2: {}",
        "logged_in":      "[+] Sesión iniciada. user_id = {}",
        "token_expired":  "[*] Token expirado — renovando automáticamente...",
        "token_renewed":  "[+] Token renovado y guardado en .env",
        "token_error":    "[!] No se pudo renovar el token:\n{}",
        "using_token":    "[+] Usando token directo, user_id={}",
        "fetching":       "[*] Obteniendo actividad ({}) del {} al {}...",
        "http_error":     "[!] HTTP {}: {}",
        "fetching_weight":"[*] Obteniendo registros de peso...",
        "no_weight":      "[!] Sin datos de báscula en este período.\n",
        "no_data":        "[!] Sin datos para este rango de fechas.",
        "api_error":      "[!] Error de API: {}",
        "saved":          "[+] JSON crudo guardado en: {}",
        "email_prompt":   "Email Zepp: ",
        "pass_prompt":    "Contraseña: ",
        "activity_title": " SEGUIMIENTO SEMANAL DE ACTIVIDAD FÍSICA",
        "weight_title":   " COMPOSICIÓN CORPORAL (báscula Xiaomi)",
        "avg_label":      "MEDIA",
        "col_date":       "Fecha",
        "col_steps":      "Pasos",
        "col_dist":       "Dist",
        "col_cal":        "Cal",
        "col_run":        "Corr",
        "col_sleep":      "Sueño",
        "col_score":      "Score",
        "col_rhr":        "FCR",
        "col_wake":       "Desp",
        "col_wmin":       "Min↑",
        "col_weight":     "Peso",
        "col_bmi":        "BMI",
        "col_fat":        "Grasa%",
        "col_muscle":     "Músculo%",
        "col_water":      "Agua%",
        "col_bone":       "Hueso",
        "col_visceral":   "Visceral",
        "col_source":     "Fuente",
        "src_scale":      "báscula",
        "src_manual":     "manual",
    },
}

_lang = "en"

def t(key: str, *args) -> str:
    s = STRINGS[_lang].get(key, STRINGS["en"][key])
    return s.format(*args) if args else s


# ──────────────────────────────────────────────
# AUTH
# ──────────────────────────────────────────────

# Europe endpoint — change to api-mifit-us.huami.com for US accounts
DATA_URL = "https://api-mifit-de2.huami.com/v1/data/band_data.json"


def login(email: str, password: str) -> dict:
    """Authenticate with Huami/Zepp servers (2-step flow)."""

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

    print(t("step1", email))
    for attempt in range(1, 5):
        r1 = requests.post(step1_url, data=step1_data, headers=step1_headers,
                           allow_redirects=False, timeout=15)
        if r1.status_code != 429:
            break
        wait = attempt * 30
        print(t("rate_limited", wait, attempt))
        time.sleep(wait)
    else:
        print(t("rate_give_up"))
        sys.exit(1)

    location = r1.headers.get("Location", "")
    if not location:
        print(t("step1_failed", r1.status_code))
        print(t("step2_body", r1.text))
        sys.exit(1)

    match = re.search(r"access=([^&]+)", location)
    if not match:
        print(f"[!] Could not parse access code from: {location}")
        sys.exit(1)

    access_code  = match.group(1)
    country_code = re.search(r"country_code=([^&]+)", location)
    country_code = country_code.group(1) if country_code else "ES"
    print(t("step1_ok", country_code))

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

    print(t("step2"))
    r2 = requests.post(step2_url, data=step2_data, headers=step2_headers, timeout=15)

    if r2.status_code != 200:
        print(t("step2_failed", r2.status_code))
        print(t("step2_body", r2.text))
        sys.exit(1)

    data = r2.json()
    if "token_info" not in data:
        print(t("step2_unexpected", json.dumps(data, indent=2)))
        sys.exit(1)

    token_info = data["token_info"]
    print(t("logged_in", token_info["user_id"]))
    return token_info


# ──────────────────────────────────────────────
# TOKEN RENEWAL
# ──────────────────────────────────────────────

def renew_token(email: str, password: str, env_file: str) -> str:
    huami_bin = os.path.join(os.path.dirname(__file__), "venv", "bin", "huami-token")
    print(t("token_expired"))
    result = subprocess.run(
        [huami_bin, "--method", "amazfit", "--email", email, "--password", password, "--no_logout"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    match = re.search(r"^app_token=(.+)$", output, re.MULTILINE)
    if not match:
        print(t("token_error", output))
        sys.exit(1)
    new_token = match.group(1).strip()
    with open(env_file) as f:
        content = f.read()
    content = re.sub(r"^ZEPP_TOKEN=.*$", f"ZEPP_TOKEN={new_token}", content, flags=re.MULTILINE)
    with open(env_file, "w") as f:
        f.write(content)
    print(t("token_renewed"))
    return new_token


# ──────────────────────────────────────────────
# WEIGHT DATA
# ──────────────────────────────────────────────

def get_weight(app_token: str, user_id: str, from_date: str, to_date: str) -> list:
    """Fetch body composition records from the Xiaomi smart scale."""
    from_ts = int(datetime.strptime(from_date, "%Y-%m-%d").timestamp())
    to_ts   = int(datetime.strptime(to_date,   "%Y-%m-%d").timestamp()) + 86400

    url     = f"https://api-mifit.zepp.com/users/{user_id}/members/-1/weightRecords"
    headers = {"apptoken": app_token}
    params  = {"limit": 200, "toTime": to_ts}

    resp = requests.get(url, headers=headers, params=params, timeout=15)
    if not resp.ok:
        print(t("http_error", resp.status_code, resp.text))
        return []

    results = []
    for item in resp.json().get("items", []):
        wt = item.get("weightType", -1)
        if wt not in (0, 7):
            continue
        if not (from_ts <= item["generatedTime"] <= to_ts):
            continue
        s = item["summary"]
        results.append({
            "date":     datetime.fromtimestamp(item["generatedTime"]).strftime("%Y-%m-%d"),
            "source":   t("src_scale") if wt == 0 else t("src_manual"),
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
        print(t("no_weight"))
        return

    W = 80
    print("\n" + "═" * W)
    print(t("weight_title"))
    print("═" * W)
    print(f"{t('col_date'):<12} {t('col_source'):<8} {t('col_weight'):>6} {t('col_bmi'):>5} {t('col_fat'):>7} {t('col_muscle'):>9} {t('col_water'):>7} {t('col_bone'):>6} {t('col_visceral'):>9} {t('col_score'):>6}")
    print("─" * W)
    for r in records:
        fat_s  = f"{r['fat']:.1f}"      if r['fat']      else "—"
        musc_s = f"{r['muscle']:.1f}"   if r['muscle']   else "—"
        water_s= f"{r['water']:.1f}"    if r['water']    else "—"
        bone_s = f"{r['bone']:.2f}"     if r['bone']     else "—"
        visc_s = f"{r['visceral']:.0f}" if r['visceral'] else "—"
        score_s= f"{r['score']}"        if r['score']    else "—"
        print(f"{r['date']:<12} {r['source']:<8} {r['weight']:>6.1f} {r['bmi']:>5.1f} {fat_s:>7} {musc_s:>9} {water_s:>7} {bone_s:>6} {visc_s:>9} {score_s:>6}")
    print("═" * W + "\n")


# ──────────────────────────────────────────────
# ACTIVITY DATA
# ──────────────────────────────────────────────

def get_activity(app_token: str, user_id: str,
                 from_date: str, to_date: str,
                 query_type: str = "summary") -> dict:
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

    print(t("fetching", query_type, from_date, to_date))
    resp = requests.get(DATA_URL, headers=headers, params=params, timeout=15)
    if not resp.ok:
        print(t("http_error", resp.status_code, resp.text))
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
    if data.get("code") != 1:
        print(t("api_error", data))
        return

    records = data.get("data", [])
    if not records:
        print(t("no_data"))
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

        st, ed   = slp.get("st", 0), slp.get("ed", 0)
        rows.append({
            "date":     date_val,
            "steps":    stp.get("ttl", 0),
            "dist_m":   stp.get("dis", 0),
            "cal":      stp.get("cal", 0),
            "run_m":    stp.get("runDist", 0),
            "sleep":    (ed - st) // 60 if st and ed else 0,
            "score":    slp.get("ss", 0),
            "rhr":      slp.get("rhr", 0),
            "wakeups":  slp.get("wc", 0),
            "wake_min": slp.get("wk", 0),
        })

    W = 72
    print("\n" + "═" * W)
    print(t("activity_title"))
    print("═" * W)
    print(f"{t('col_date'):<12} {t('col_steps'):>7} {t('col_dist'):>6} {t('col_cal'):>5} {t('col_run'):>6} {t('col_sleep'):>7} {t('col_score'):>6} {t('col_rhr'):>5} {t('col_wake'):>5} {t('col_wmin'):>5}")
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

    def avg(key):
        vals = [r[key] for r in rows if r[key]]
        return sum(vals) / len(vals) if vals else 0

    print("─" * W)
    print(
        f"{t('avg_label'):<12}"
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

    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    parser = argparse.ArgumentParser(description="Zepp / Huami activity & body composition fetcher")
    parser.add_argument("--token",    default=os.environ.get("ZEPP_TOKEN"),    help="app_token (skips login)")
    parser.add_argument("--userid",   default=os.environ.get("ZEPP_USERID"),   help="user_id (skips login)")
    parser.add_argument("--email",    default=os.environ.get("ZEPP_EMAIL"),    help="Zepp account email")
    parser.add_argument("--password", default=os.environ.get("ZEPP_PASSWORD"), help="Zepp account password")
    parser.add_argument("--days",     type=int, default=7,                     help="Days back to fetch (default: 7)")
    parser.add_argument("--lang",     default=os.environ.get("ZEPP_LANG", "en"), choices=["en", "es"], help="Output language (default: en)")
    args = parser.parse_args()

    _lang = args.lang

    to_date   = datetime.today().strftime("%Y-%m-%d")
    from_date = (datetime.today() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    email    = args.email    or input(t("email_prompt"))
    password = args.password or input(t("pass_prompt"))

    if args.token and args.userid:
        print(t("using_token", args.userid))
        app_token = args.token
        user_id   = args.userid
    else:
        token_info = login(email, password)
        app_token  = token_info["app_token"]
        user_id    = str(token_info["user_id"])

    try:
        raw = get_activity(app_token, user_id, from_date, to_date)
    except Exception:
        app_token = renew_token(email, password, env_file)
        raw = get_activity(app_token, user_id, from_date, to_date)

    parse_and_print(raw)

    print(t("fetching_weight"))
    weight_records = get_weight(app_token, user_id, "2000-01-01", to_date)
    print_weight(weight_records[-10:] if weight_records else [])

    out_file = f"zepp_activity_{from_date}_{to_date}.json"
    with open(out_file, "w") as f:
        json.dump(raw, f, indent=2)
    print(t("saved", out_file))
