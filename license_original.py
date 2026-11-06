# license.py (Fixed Device ID Edition)
import os
import json
import hmac
import hashlib
import uuid
from datetime import date, datetime

SECRET = b"Lakaw_Secret_Key_2024"
KEY_FILE = "license_key.txt"
ID_FILE = "device_id.txt" 

def get_device_id():
    if os.path.exists(ID_FILE):
        try:
            with open(ID_FILE, "r") as f:
                saved_id = f.read().strip()
                if saved_id:
                    return saved_id
        except:
            pass

    try:
        new_id = str(uuid.uuid4()).replace("-", "").upper()[:16]
    except:
        new_id = "KAVIN_DEVICE_01"
        
    try:
        with open(ID_FILE, "w") as f:
            f.write(new_id)
    except:
        pass
        
    return new_id

def verify_key(user_key, device_id):
    try:
        parts = user_key.split("-")
        if len(parts) != 5 or parts[0] != "KAVIN":
            return False, "Invalid key format", 0
        
        rand1, rand2, expiry_str, sig = parts[1], parts[2], parts[3], parts[4]
        
        raw = f"{device_id}|{expiry_str}|{rand1}{rand2}"
        expected_sig = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()[:4].upper()
        
        if expected_sig != sig:
            return False, "Invalid signature (Wrong Device or Key)", 0
        
        try:
            expiry = datetime.strptime(expiry_str, "%Y%m%d").date()
        except:
            return False, "Invalid expiry date", 0
        
        if date.today() > expiry:
            return False, f"Key expired on {expiry.strftime('%Y-%m-%d')}", 0
        
        left = (expiry - date.today()).days
        return True, f"{left} Days Left (Exp: {expiry.strftime('%Y-%m-%d')})", left
        
    except Exception as e:
        return False, f"Error: {str(e)}", 0

def check_approval():
    print("\n" + "=" * 50)
    print("⚡ KAVIN FAST SPEED ⚡")
    print("License Check")
    print("=" * 50 + "\n")

    dev = get_device_id()

    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE) as f:
                data = json.load(f)
            key = data.get("key", "")
            ok, msg, days = verify_key(key, dev)
            if ok:
                print(f"✅ License Valid: {msg}")
                print("-" * 50)
                return True, msg
            else:
                print(f"❌ {msg}")
                print("🗑️ Invalid key found. Please re-enter.")
        except Exception:
            pass

    print(f"📱 Your Device ID:\n\n    {dev}\n")
    print("─" * 50)
    print("🗣️ Send this ID to Admin.")
    print("🗣️ Paste the Key here when you get it.")
    print("─" * 50 + "\n")

    key = input("➜ Enter Key: ").strip()
    ok, msg, days = verify_key(key, dev)
    if ok:
        print(f"\n✅ License Valid: {msg}")
        try:
            with open(KEY_FILE, "w") as f:
                json.dump({"key": key, "device": dev}, f)
        except Exception:
            pass
        return True, msg
    else:
        print(f"\n❌ {msg}")
        input("Press Enter to exit...")
        return False, ""

if __name__ == "__main__":
    check_approval()
