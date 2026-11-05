# license.py
import os
import json
import base64
import hmac
import hashlib
import uuid
from datetime import date

SECRET = b"Lakaw_Secret_Key_2024"
KEY_FILE = "license_key.txt"

def get_device_id():
    try:
        return str(uuid.getnode()).upper()
    except:
        return "UNKNOWN_DEVICE"

def verify_key(user_key, device_id):
    try:
        parts = user_key.split("-")
        if len(parts) < 3:
            return False, "Invalid key format"
        
        if parts[0] != "KAVIN":
            return False, "Invalid key prefix"
        
        sig = parts[-1]
        token = "".join(parts[1:-1]) 
        
        pad = "=" * (-len(token) % 4)
        try:
            raw = base64.urlsafe_b64decode(token + pad)
        except:
            return False, "Invalid token format"
        
        expected_sig = hmac.new(SECRET, raw, hashlib.sha256).hexdigest()[:16].upper()
        if not hmac.compare_digest(expected_sig, sig):
            return False, "Invalid signature"
        
        try:
            payload = json.loads(raw.decode())
        except:
            return False, "Invalid payload data"
            
        key_device = payload.get("d", "").upper()
        expiry_str = payload.get("e", "")
        
        if key_device != device_id.upper():
            return False, f"Key is for another device (Expected: {key_device})"
        
        try:
            expiry = date.fromisoformat(expiry_str)
        except:
            return False, "Invalid expiry date"
        
        if date.today() > expiry:
            return False, f"Key expired on {expiry_str}"
        
        left = (expiry - date.today()).days
        return True, f"Valid — {left} days left (Expires: {expiry_str})"
        
    except Exception as e:
        return False, f"Error: {str(e)}"

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
            ok, msg = verify_key(key, dev)
            if ok:
                print(f"✅ {msg}")
                return True
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
    ok, msg = verify_key(key, dev)
    if ok:
        print(f"\n✅ {msg}")
        try:
            with open(KEY_FILE, "w") as f:
                json.dump({"key": key, "device": dev}, f)
        except Exception:
            pass
        return True
    else:
        print(f"\n❌ {msg}")
        input("Press Enter to exit...")
        return False

if __name__ == "__main__":
    if check_approval():
        print("✅ License check passed.")
    else:
        print("❌ License check failed.")