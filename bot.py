import telebot
import hmac
import hashlib
import random
import string
from datetime import date, timedelta
from telebot import types

# ================= CONFIGURATION =================
BOT_TOKEN = "9171784150:AAGW7bpVK3S211jhLfGpb2XG5y-u_qiNQZg"
ADMIN_ID = 123456789  # ★ သင့် Telegram ID ကို ဒီမှာ ထည့်ပါ
KPAY_NO = "09266976019 (Mu Yan)" 

# ★★★ ဈေးနှုန်းများ ★★★
PRICES = {
    1: 1000,      
    3: 3000,      
    7: 5000,      
    15: 10000,    
    30: 15000,    
    36500: 30000  # Ultimate (ရာသက်ပန်)
}

PACKAGE_NAMES = {
    1: "1 Day",
    3: "3 Days",
    7: "7 Days",
    15: "15 Days",
    30: "1 Month",
    36500: "Ultimate (Lifetime)"
}
# =================================================

SECRET = b"Lakaw_Secret_Key_2024"
bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

# Device ID ပါဝင်တဲ့ Key ထုတ်တဲ့ Function
def make_key(device_id, days):
    rand_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    expiry = (date.today() + timedelta(days=days)).strftime("%Y%m%d")
    raw = f"{device_id}|{expiry}|{rand_part}"
    sig = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()[:4].upper()
    return f"KAVIN-{rand_part[:4]}-{rand_part[4:]}-{expiry}-{sig}"

def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_key = types.InlineKeyboardButton("🔑 Buy Key", callback_data="get_key")
    btn_prices = types.InlineKeyboardButton("💰 Price List", callback_data="view_prices")
    btn_help = types.InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin")
    markup.add(btn_key, btn_prices, btn_help)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data[user_id] = {"step": "main_menu"}
    
    text = (
        f"👋 မင်္ဂလာပါ {message.from_user.first_name}!\n\n"
        "🤖 **KAVIN FAST SPEED - Key Bot** မှ ကြိုဆိုပါတယ်။\n\n"
        "အောက်ပါ Menu ကနေ ရွေးချယ်နိုင်ပါတယ်။"
    )
    bot.send_message(message.chat.id, text, reply_markup=get_main_menu(), parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    user_id = call.from_user.id
    
    if call.data == "get_key":
        user_data[user_id] = {"step": "ask_device_id"}
        bot.edit_message_text(
            "🆔 **သင့်ရဲ့ Device ID ကို ပို့ပေးပါ။**\n\n"
            "(Program ကို Run လိုက်ရင် Device ID ပေါ်လာပါလိမ့်မယ်။)",
            call.message.chat.id, call.message.message_id, parse_mode='Markdown'
        )
        
    elif call.data == "view_prices":
        price_text = "💰 **ဈေးနှုန်းစာရင်း**\n\n"
        for days, price in PRICES.items():
            price_text += f"⏳ {PACKAGE_NAMES[days]} - {price:,} ကျပ်\n"
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, price_text, parse_mode='Markdown')
        
    elif call.data == "contact_admin":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, f"📞 Admin ကို ဆက်သွယ်ရန်: @YourTelegramUsername")

    elif call.data.startswith("days_"):
        days = int(call.data.split("_")[1])
        dev_id = user_data[user_id].get("dev_id", "")
        
        if not dev_id:
            bot.send_message(call.message.chat.id, "Error: Device ID မရှိပါ။ /start ကနေ ပြန်စပါ။")
            return
            
        user_data[user_id]["days"] = days
        price = PRICES.get(days, 0)
        pkg_name = PACKAGE_NAMES.get(days, f"{days} Days")
        
        text = (
            f"🛒 **အော်ဒါ အချက်အလက်**\n\n"
            f"🆔 Device ID: `{dev_id}`\n"
            f"📦 Package: {pkg_name}\n"
            f"💰 ကျသင့်ငွေ: {price:,} ကျပ်\n\n"
            f"💸 ငွေလွှဲရန် - KPay: `{KPAY_NO}`\n\n"
            f"ငွေလွှဲပြီးရင် **ပြေစာပုံ (Screenshot)** ကို ဒီ Chat မှာ ပို့ပေးပါ။"
        )
        user_data[user_id]["step"] = "wait_receipt"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='Markdown')

@bot.message_handler(func=lambda message: user_data.get(message.from_user.id, {}).get("step") == "ask_device_id")
def get_device_id(message):
    user_id = message.from_user.id
    dev_id = message.text.strip().upper()
    
    if len(dev_id) < 10:
        bot.reply_to(message, "❌ Device ID ပုံစံ မမှန်ပါ။ ပြန်ပို့ပါ။")
        return
        
    user_data[user_id]["dev_id"] = dev_id
    user_data[user_id]["step"] = "choose_days"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    for days, price in PRICES.items():
        markup.add(types.InlineKeyboardButton(f"{PACKAGE_NAMES[days]} - {price:,} Ks", callback_data=f"days_{days}"))
    
    bot.reply_to(message, f"✅ Device ID သိမ်းပြီးပါပြီ: `{dev_id}`\n\n⏳ သက်တမ်းကို ရွေးချယ်ပါ-", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    user_id = message.from_user.id
    if user_data.get(user_id, {}).get("step") != "wait_receipt":
        bot.reply_to(message, "ကျေးဇူးပြုပြီး /start ကနေ ပြန်စပါ။")
        return
    
    bot.reply_to(message, "⏳ ပြေစာ စစ်ဆေးနေပါသည်။ ခဏစောင့်ပါ။")
    
    dev_id = user_data[user_id].get("dev_id", "Unknown")
    days = user_data[user_id].get("days", 30)
    price = PRICES.get(days, 0)
    pkg_name = PACKAGE_NAMES.get(days, f"{days} Days")
    
    markup = types.InlineKeyboardMarkup()
    approve_btn = types.InlineKeyboardButton("✅ Approve", callback_data=f"appr_{user_id}")
    reject_btn = types.InlineKeyboardButton("❌ Reject", callback_data=f"rej_{user_id}")
    markup.add(approve_btn, reject_btn)
    
    caption = f"🧾 ပြေစာအသစ်\nUser: {message.from_user.first_name}\nID: `{user_id}`\nDevice: `{dev_id}`\nPackage: {pkg_name}\nPrice: {price} Ks"
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith(('appr_', 'rej_')))
def handle_admin_action(call):
    action, user_id_str = call.data.split("_")
    user_id = int(user_id_str)
    
    if action == "appr":
        dev_id = user_data[user_id]["dev_id"]
        days = user_data[user_id]["days"]
        key = make_key(dev_id, days)
        expire_date = (date.today() + timedelta(days=days)).isoformat()
        pkg_name = PACKAGE_NAMES.get(days, f"{days} Days")
        
        msg = (
            f"🎉 **ငွေလွှဲမှု အတည်ပြုပြီးပါပြီ!**\n\n"
            f"🆔 Device ID: `{dev_id}`\n"
            f"📦 Package: {pkg_name}\n"
            f"📅 Expiry: {expire_date}\n\n"
            f"🔑 **Generated Key:**\n`{key}`\n\n"
            f"ဒီ Key ကို Copy ကူးပြီး Program မှာ ထည့်ပါ။"
        )
        bot.send_message(user_id, msg, parse_mode='Markdown')
        
        guide_text = (
            "📖 **Termux မှာ သုံးနည်း (အဆင့် ၄ ဆင့်)**\n"
            "───────────────────────\n"
            "**အဆင့် (၁) - Termux ဖွင့်ပြီး လိုအပ်တာသွင်းပါ**\n"
            "`pkg update -y && pkg install python git -y && pip install requests rich`\n\n"
            "**အဆင့် (၂) - Program ကို ဒေါင်းလုဒ်ဆွဲပါ**\n"
            "`git clone https://github.com/aungkhantthu799760-hub/lakaw-speedd.git && cd lakaw-speedd`\n\n"
            "**အဆင့် (၃) - Program ကို Run ပါ**\n"
            "`python lakaw.py`\n\n"
            "**အဆင့် (၄) - Key ထည့်ပါ**\n"
            "Program က Device ID တောင်းရင် ခုနက ရလာတဲ့ Key ကို Paste လုပ်ထည့်ပါ။\n\n"
            "⚠️ **သတိပြုရန်** - Key ကို Copy ကူးတဲ့အခါ အပိုကွက်လပ်တွေ မပါစေနဲ့။"
        )
        bot.send_message(user_id, guide_text, parse_mode='Markdown')
        
        bot.edit_message_caption(f"✅ Approved\nUser: {user_id}\nDevice: {dev_id}", call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, "ထပ်မံဝယ်ယူလိုပါက /start ကို နှိပ်ပါ။", reply_markup=get_main_menu())
        
    elif action == "rej":
        bot.send_message(user_id, "❌ ပြေစာ မှားယွင်းနေပါတယ်။ ပြန်လည် စစ်ဆေးပြီး ထပ်ပို့ပေးပါ။")
        bot.edit_message_caption(f"❌ Rejected\nUser: {user_id}", call.message.chat.id, call.message.message_id)

print("🤖 Bot is running...")
bot.infinity_polling()
