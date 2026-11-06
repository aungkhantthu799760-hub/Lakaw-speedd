# keygen.py (KAVIN ADMIN KEYGEN - Clean English Edition)
import hmac
import hashlib
import random
import string
import os
from datetime import date, timedelta
from rich.console import Console
from rich.text import Text
from rich.prompt import Prompt

SECRET = b"Lakaw_Secret_Key_2024"
console = Console()

def make_key(device_id, days=30):
    # ကျပန်းစာလုံး ၈ လုံး ထုတ်မယ်
    rand_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    # သက်တမ်းကုန်မယ့်ရက်
    expiry = (date.today() + timedelta(days=days)).strftime("%Y%m%d")
    
    # Signature တွက်မယ်
    raw = f"{device_id}|{expiry}|{rand_part}"
    sig = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()[:4].upper()
    
    # Key ပုံစံ - KAVIN-XXXX-XXXX-YYYYMMDD-SIG
    return f"KAVIN-{rand_part[:4]}-{rand_part[4:]}-{expiry}-{sig}"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

if __name__ == "__main__":
    clear_screen()
    console.print(Text("══════════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print(Text("⚡ KAVIN ADMIN PANEL ⚡", style="bold bright_magenta"), justify="center")
    console.print(Text("══════════════════════════════════════════", style="bold bright_cyan"), justify="center")
    console.print()

    console.print(Text("  📌 Enter Customer's Device ID...", style="bold bright_cyan"))
    dev_id = Prompt.ask("  [bold bright_green]➜ 🆔 Device ID[/bold bright_green]").strip().upper()
    
    console.print(Text("  ⏱ Enter Duration in Days (Default: 30) ...", style="bold bright_cyan"))
    days_str = Prompt.ask("  [bold bright_green]➜ 📅 Duration (Days)[/bold bright_green]", default="30").strip()
    
    try:
        days = int(days_str)
    except:
        days = 30

    if not dev_id:
        console.print(Text("  ❌ Error: Device ID is required.", style="bold red"))
        exit()

    key = make_key(dev_id, days)
    expire_date = (date.today() + timedelta(days=days)).isoformat()
    
    console.print("\n")
    console.print(Text("──────────────────────────────────────────", style="dim bright_cyan"))
    console.print(Text("  🎉 KEY GENERATED SUCCESSFULLY 🎉", style="bold bright_green"))
    console.print(Text("──────────────────────────────────────────", style="dim bright_cyan"))
    
    console.print(Text("  👤 🆔 Device ID  : ", style="bold bright_white"), end="")
    console.print(Text(f"{dev_id}", style="bold bright_yellow"))
    
    console.print(Text("  📅 ⏱ Duration   : ", style="bold bright_white"), end="")
    console.print(Text(f"{days} Days", style="bold bright_cyan"))
    
    console.print(Text("  ⏳ 🗓 Expiry Date: ", style="bold bright_white"), end="")
    console.print(Text(f"{expire_date}", style="bold bright_magenta"))
    
    console.print(Text("──────────────────────────────────────────", style="dim bright_cyan"))
    console.print(Text("  🔑 ✨ Generated Key:", style="bold bright_white"))
    console.print(Text(f"  {key}\n", style="bold bright_green"))
    console.print(Text("──────────────────────────────────────────", style="dim bright_cyan"))
