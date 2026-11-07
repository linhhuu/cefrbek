import os
import asyncio
import sqlite3
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    WebAppInfo, 
    CallbackQuery
)
from aiogram.enums import ChatMemberStatus
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================= RENDER UCHUN VEB-PORT =================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"CEFR Telegram Bot is Live and Healthy!")
    def log_message(self, format, *args):
        pass  # Konsol toza turishi uchun

def start_health_check_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Render veb-porti {port}-portda ishga tushdi...")

# ================= SOZLAMALAR =================
BOT_TOKEN = "9179828460:AAFNOvJrENya-8IuVs9yuHF8wOEBs-tGygg"
CHANNEL_ID = "@uzcold"  # Bot kanalda ADMIN bo'lishi shart
CHANNEL_URL = "https://t.me/uzcold"
WEBAPP_URL = "https://cefrbek.vercel.app/"
ADMIN_ID = 1958417797  # Telegram ID raqamingiz

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Asia/Tashkent")

# ================= BAZA (SQLite) =================
def init_db():
    conn = sqlite3.connect("cefr_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            joined_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, first_name, username):
    conn = sqlite3.connect("cefr_users.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, first_name, username, joined_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, first_name, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect("cefr_users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

# ================= MAJBURIY OBUNANI TEKSHIRISH =================
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in [
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.CREATOR
        ]
    except Exception as e:
        print(f"Obuna tekshirishda xatolik: {e}")
        return True

def get_sub_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")]
        ]
    )

def get_webapp_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 30 Kunlik Trackerni Ochish", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
    )

# ================= BUYRUQLAR (HANDLERS) =================
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username or ""

    add_user(user_id, first_name, username)

    if not await is_subscribed(user_id):
        await message.answer(
            f"Salom, <b>{first_name}</b>!\n\n"
            "⚠️ Botdan to‘liq foydalanish va 30 kunlik challengega kirish uchun "
            f"avval rasmiy kanalimizga a’zo bo‘ling:",
            reply_markup=get_sub_keyboard(),
            parse_mode="HTML"
        )
        return

    await message.answer(
        f"Assalomu alaykum, <b>{first_name}</b>!\n\n"
        "🎯 <b>CEFR Multi-Level 30-Day Challenge</b> botiga xush kelibsiz.\n"
        "75 ballik rasmiy shkala asosida har kunlik mock natijalaringizni belgilab boring!\n\n"
        "Ilovani ochish uchun quyidagi tugmani bosing:",
        reply_markup=get_webapp_keyboard(),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "check_subscription")
async def check_sub_callback(call: CallbackQuery):
    if await is_subscribed(call.from_user.id):
        await call.message.delete()
        await call.message.answer(
            "✅ <b>Obuna muvaffaqiyatli tasdiqlandi!</b>\n\n"
            "Endi 30 kunlik challenge trekerini ochishingiz mumkin:",
            reply_markup=get_webapp_keyboard(),
            parse_mode="HTML"
        )
    else:
        await call.answer("❌ Siz hali kanalga a'zo bo'lmadingiz! Iltimos, kanalga obuna bo'ling.", show_alert=True)

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        users = get_all_users()
        await message.answer(f"📊 <b>Bot foydalanuvchilari soni:</b> {len(users)} ta", parse_mode="HTML")

# ================= KUNLIK AVTOMATIK ESLATMALAR =================
async def morning_reminder():
    users = get_all_users()
    msg = (
        "☀️ <b>Xayrli tong, CEFR chempioni!</b>\n\n"
        "⏰ Yangi kun boshlandi. Uyg'onish va 15 daqiqalik badantarbiyani bajardingizmi?\n"
        "Bugungi mock test va mashg'ulotlarni boshlash vaqti keldi! Intizomni saqlang! 🔥"
    )
    for u_id in users:
        try:
            await bot.send_message(u_id, msg, reply_markup=get_webapp_keyboard(), parse_mode="HTML")
            await asyncio.sleep(0.05)
        except Exception:
            pass

async def evening_reminder():
    users = get_all_users()
    msg = (
        "🌙 <b>Kun yakuni yaqinlashmoqda!</b>\n\n"
        "Bugungi mock test ballaringizni kiritdingizmi? Xatolaringizni tahlil qilib chiqdingizmi?\n"
        "Hozir ilovani
