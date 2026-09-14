import asyncio
import logging
import random
import sqlite3
import string
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineQueryResultCachedDocument,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedVideo,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

# Configuration Details
BOT_TOKEN = "8741655203:AAHMqMozxrl-qYsbkG_RKOPrwRSH512gNT8"
MAIN_CHANNEL_ID = -1003871503746   # Main Channel ID
VAULT_CHANNEL_ID = -1004439489795  # Vault Channel ID
ADMIN_USER_ID = 8780228920         # Your Admin Telegram User ID
CHANNEL_INVITE_LINK = "https://t.me/+twkHr9N5_wAzOWYy" # Your Private Main Channel Link

# --- Timetable Configuration (10-B Aniq Schedule) ---
DAY_CODES = ["du", "se", "ch", "pa", "ju"]

DAY_NAMES = {
    "du": "Dushanba (Monday)",
    "se": "Seshanba (Tuesday)",
    "ch": "Chorshanba (Wednesday)",
    "pa": "Payshanba (Thursday)",
    "ju": "Juma (Friday)",
}

# Map Python weekdays (0=Mon, 1=Tue... 4=Fri) to day codes
WEEKDAY_TO_CODE = {0: "du", 1: "se", 2: "ch", 3: "pa", 4: "ju"}

TIMETABLE = {
    "du": [
        {"subject": "Algebra", "room": "218", "teachers": ["Umid", "Muhammadsodiq"]},
        {"subject": "Kelajak soati", "room": "204", "teachers": ["Umarbek"]},
        {"subject": "Ona tili", "room": "208", "teachers": ["Q.Umid"]},
        {"subject": "Informatika", "room": "220", "teachers": ["Xursand", "Umarbek"]},
        {"subject": "Ingliz tili", "room": "128", "teachers": ["Rufat", "Muzaffar"]},
        {"subject": "Rus tili", "room": "202", "teachers": ["Gulzoda", "Sevara"]},
        {"subject": "Fizika", "room": "202", "teachers": ["O'g'lijon", "Ulug'bek"]},
    ],
    "se": [
        {"subject": "O'zbek tarix", "room": "113", "teachers": ["Murod"]},
        {"subject": "Adabiyot", "room": "208", "teachers": ["Q.Umid"]},
        {"subject": "Algebra", "room": "218", "teachers": ["Umid", "Muhammadsodiq"]},
        {"subject": "Geometriya", "room": "218", "teachers": ["Umid", "Muhammadsodiq"]},
        {"subject": "CHQBT", "room": "220", "teachers": ["To'lqin"]},
        {"subject": "Ingliz tili", "room": "220", "teachers": ["Rufat", "Muzaffar"]},
        {"subject": "Fizika", "room": "202", "teachers": ["O'g'lijon", "Ulug'bek"]},
    ],
    "ch": [
        {"subject": "Ona tili", "room": "208", "teachers": ["Q.Umid"]},
        {"subject": "Algebra", "room": "218", "teachers": ["Umid", "Muhammadsodiq"]},
        {"subject": "Fizika", "room": "218", "teachers": ["O'g'lijon", "Ulug'bek"]},
        {"subject": "Rus tili", "room": "128", "teachers": ["Gulzoda", "Sevara"]},
        {"subject": "Ingliz tili", "room": "220", "teachers": ["Rufat", "Muzaffar"]},
        {"subject": "CHQBT", "room": "129", "teachers": ["To'lqin"]},
        None,
    ],
    "pa": [
        {"subject": "Tarbiya", "room": "132", "teachers": ["Azada"]},
        {"subject": "Fizika", "room": "218", "teachers": ["O'g'lijon", "Ulug'bek"]},
        {"subject": "Algebra", "room": "218", "teachers": ["Umid", "Muhammadsodiq"]},
        {"subject": "Geometriya", "room": "218", "teachers": ["Umid", "Muhammadsodiq"]},
        {"subject": "Ingliz tili", "room": "220", "teachers": ["Rufat", "Muzaffar"]},
        {"subject": "Adabiyot", "room": "208", "teachers": ["Q.Umid"]},
        None,
    ],
    "ju": [
        {"subject": "Jismoniy tarbiya", "room": "Sport zal", "teachers": ["Ulug'bek"]},
        {"subject": "Geometriya", "room": "218", "teachers": ["Umid", "Muhammadsodiq"]},
        {"subject": "O'zbek tarix", "room": "113", "teachers": ["Murod"]},
        {"subject": "Fizika", "room": "202", "teachers": ["O'g'lijon", "Ulug'bek"]},
        {"subject": "Jahon tarix", "room": "113", "teachers": ["Murod"]},
        {"subject": "Informatika", "room": None, "teachers": ["Xursand", "Umarbek"]},
        None,
    ],
}

BELL_SCHEDULE = [
    {"lesson": 1, "start": "09:00", "end": "09:45", "break_after": "5 min break"},
    {"lesson": 2, "start": "09:50", "end": "10:35", "break_after": "5 min break"},
    {"lesson": 3, "start": "10:40", "end": "11:25", "break_after": "5 min break"},
    {"lesson": 4, "start": "11:30", "end": "12:15", "break_after": "30 min lunch break"},
    {"lesson": 5, "start": "12:45", "end": "13:30", "break_after": "5 min break"},
    {"lesson": 6, "start": "13:35", "end": "14:20", "break_after": "5 min break"},
    {"lesson": 7, "start": "14:25", "end": "15:10", "break_after": "End of school day"},
]

REMINDER_HOUR = 8
REMINDER_MINUTE = 45

# --- Database Setup ---
conn = sqlite3.connect("vault.db")
cursor = conn.cursor()

# Files table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS files (
        passcode TEXT PRIMARY KEY,
        file_id TEXT,
        file_type TEXT,
        downloads INTEGER DEFAULT 0
    )
""")

# Reminders table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        text TEXT,
        remind_at TEXT
    )
""")
conn.commit()

# --- Database Helper Functions ---
def save_file(passcode: str, file_id: str, file_type: str):
    cursor.execute("INSERT OR REPLACE INTO files (passcode, file_id, file_type, downloads) VALUES (?, ?, ?, 0)", (passcode, file_id, file_type))
    conn.commit()

def get_file(passcode: str):
    cursor.execute("SELECT file_id, file_type, downloads FROM files WHERE passcode = ?", (passcode,))
    return cursor.fetchone()

def increment_download(passcode: str):
    cursor.execute("UPDATE files SET downloads = downloads + 1 WHERE passcode = ?", (passcode,))
    conn.commit()

def delete_file_record(passcode: str) -> bool:
    cursor.execute("DELETE FROM files WHERE passcode = ?", (passcode,))
    conn.commit()
    return cursor.rowcount > 0

def get_all_files():
    cursor.execute("SELECT passcode, file_type, downloads FROM files")
    return cursor.fetchall()

def generate_passcode(length=6) -> str:
    chars = string.ascii_uppercase + string.digits
    return f"DOC-{''.join(random.choices(chars, k=length))}"

def add_reminder(user_id: int, text: str, remind_at: datetime):
    cursor.execute(
        "INSERT INTO reminders (user_id, text, remind_at) VALUES (?, ?, ?)",
        (user_id, text, remind_at.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

def get_due_reminders():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT id, user_id, text FROM reminders WHERE remind_at <= ?", (now_str,))
    return cursor.fetchall()

def delete_reminder(reminder_id: int):
    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()

# --- Formatting Helper for Timetable ---
def format_day_schedule(day_code: str) -> str:
    if day_code not in TIMETABLE:
        return "❌ Dars jadvali topilmadi."

    day_name = DAY_NAMES.get(day_code, day_code.upper())
    lessons = TIMETABLE[day_code]
    
    text = f"📅 **Dars Jadvali: {day_name}**\n\n"
    for idx, item in enumerate(lessons):
        bell = BELL_SCHEDULE[idx]
        if item is None:
            text += f"**{bell['lesson']}-dars ({bell['start']} - {bell['end']}):** — *Dars yo'q*\n\n"
        else:
            room_str = f"| xona: {item['room']}" if item.get('room') else ""
            teachers_str = ", ".join(item['teachers']) if item.get('teachers') else ""
            text += f"**{bell['lesson']}-dars ({bell['start']} - {bell['end']}):** {item['subject']}\n"
            text += f"└ 👨‍🏫 *O'qituvchi:* {teachers_str} {room_str}\n\n"
    return text

# --- Channel Membership Verification Helper ---
async def is_channel_member(bot: Bot, user_id: int) -> bool:
    if user_id == ADMIN_USER_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=MAIN_CHANNEL_ID, user_id=user_id)
        return member.status in ["creator", "administrator", "member"]
    except Exception:
        return False

# --- Bot Initialization ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ----------------------------------------------------
# Background Task: Schedule Alerts, Bell Alerts & Reminders
# ----------------------------------------------------
async def background_scheduler():
    last_processed_minute = ""
    
    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        current_date_str = now.strftime("%Y-%m-%d")
        minute_key = f"{current_date_str}_{current_time_str}"
        weekday = now.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

        # 1. Process custom user reminders
        due_reminders = get_due_reminders()
        for rem_id, user_id, text in due_reminders:
            try:
                await bot.send_message(user_id, f"⏰ **ESLATMA:**\n\n{text}", parse_mode="Markdown")
            except Exception as e:
                logging.error(f"Reminder delivery failed: {e}")
            finally:
                delete_reminder(rem_id)

        # 2. Automated School Day Alerts (Monday - Friday)
        if weekday in WEEKDAY_TO_CODE and minute_key != last_processed_minute:
            day_code = WEEKDAY_TO_CODE[weekday]
            today_lessons = TIMETABLE[day_code]

            # Morning schedule alert at 08:45 AM
            if now.hour == REMINDER_HOUR and now.minute == REMINDER_MINUTE:
                schedule_msg = f"☀️ **Xayrli kun! Bugungi dars jadvalingiz:**\n\n" + format_day_schedule(day_code)
                try:
                    await bot.send_message(ADMIN_USER_ID, schedule_msg, parse_mode="Markdown")
                except Exception as e:
                    logging.error(f"Morning alert error: {e}")

            # Check lesson end times & school end notifications
            for idx, bell in enumerate(BELL_SCHEDULE):
                lesson_num = bell["lesson"]
                lesson_end_time = bell["end"]
                lesson_info = today_lessons[idx] if idx < len(today_lessons) else None

                if current_time_str == lesson_end_time:
                    # Check if this was the last active lesson of the day
                    is_last_lesson = (
                        idx == len(BELL_SCHEDULE) - 1 or 
                        (idx < len(today_lessons) - 1 and today_lessons[idx + 1] is None)
                    )

                    if lesson_info is not None:
                        msg = f"🔔 **{lesson_num}-dars ({lesson_info['subject']}) tugadi!**\n"
                        msg += f"ℹ️ Keyingi: {bell['break_after']}"
                        
                        try:
                            await bot.send_message(ADMIN_USER_ID, msg, parse_mode="Markdown")
                        except Exception as e:
                            logging.error(f"Lesson end alert error: {e}")

                    # If school is over, send the final end message
                    if is_last_lesson:
                        end_msg = "🎉 **Bugungi darslar yakunlandi! Maktab kuni tugadi. Maroqli hordiq chiqaring!**"
                        try:
                            await bot.send_message(ADMIN_USER_ID, end_msg, parse_mode="Markdown")
                        except Exception as e:
                            logging.error(f"School end alert error: {e}")

            last_processed_minute = minute_key

        await asyncio.sleep(15)

# ----------------------------------------------------
# 1. TIMETABLE COMMANDS
# ----------------------------------------------------
@dp.message(Command("schedule", "timetable"))
async def cmd_schedule(message: types.Message):
    args = message.text.split()
    
    if len(args) > 1:
        query_day = args[1].lower()
        if query_day in DAY_CODES:
            day_code = query_day
        else:
            await message.answer("❌ Noto'g'ri kun kodi! Foydalanish: `/schedule du` (du, se, ch, pa, ju)", parse_mode="Markdown")
            return
    else:
        weekday = datetime.now().weekday()
        if weekday in WEEKDAY_TO_CODE:
            day_code = WEEKDAY_TO_CODE[weekday]
        else:
            await message.answer("🎉 **Bugun dam olish kuni! Darslar yo'q.**\n\nKungi darslarni ko'rish uchun: `/schedule du`", parse_mode="Markdown")
            return

    text = format_day_schedule(day_code)
    await message.answer(text, parse_mode="Markdown")

# ----------------------------------------------------
# 2. ADMIN VAULT MANAGEMENT & ANALYTICS
# ----------------------------------------------------
@dp.message(Command("listfiles"))
async def cmd_list_files(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID:
        return

    files = get_all_files()
    if not files:
        await message.answer("📂 Vault is currently empty.")
        return

    text = "📊 **Vault Files & Download Analytics:**\n\n"
    for code, f_type, downloads in files:
        text += f"• `{code}` | Type: `{f_type}` | 📥 Downloads: **{downloads}**\n"

    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("deletecode"))
async def cmd_delete_code(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID:
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("⚠️ Usage: `/deletecode DOC-XXXXXX`", parse_mode="Markdown")
        return

    target_code = args[1].upper()
    if delete_file_record(target_code):
        await message.answer(f"✅ Passcode `{target_code}` deleted successfully.", parse_mode="Markdown")
    else:
        await message.answer(f"❌ Passcode `{target_code}` not found in vault database.", parse_mode="Markdown")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID:
        return

    cursor.execute("SELECT COUNT(*), SUM(downloads) FROM files")
    total_files, total_downloads = cursor.fetchone()
    total_downloads = total_downloads or 0

    await message.answer(
        f"📈 **Vault Performance Metrics:**\n\n"
        f"• Total Files Stored: **{total_files}**\n"
        f"• Total Downloads Served: **{total_downloads}**",
        parse_mode="Markdown"
    )

# ----------------------------------------------------
# 3. CHANNEL POST FORMATTING TOOL (/post)
# ----------------------------------------------------
@dp.message(Command("post"))
async def cmd_post_to_channel(message: types.Message):
    if message.from_user.id != ADMIN_USER_ID:
        return

    raw_content = message.text[5:].strip()
    if not raw_content:
        await message.answer(
            "⚠️ **Channel Formatting Tool Usage:**\n\n"
            "`/post Your message here`\n"
            "`/post Your text | Button Text | https://example.com`",
            parse_mode="Markdown"
        )
        return

    parts = [p.strip() for p in raw_content.split("|")]
    post_text = parts[0]
    reply_markup = None

    if len(parts) >= 3:
        btn_text = parts[1]
        btn_url = parts[2]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn_text, url=btn_url)]
        ])

    try:
        sent = await bot.send_message(
            chat_id=MAIN_CHANNEL_ID,
            text=post_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        await message.answer(f"✅ Broadcast published successfully to Main Channel! (Message ID: {sent.message_id})")
    except Exception as e:
        await message.answer(f"❌ Broadcast failed: {e}")

# ----------------------------------------------------
# 4. VAULT CHANNEL: Auto-generate code on upload
# ----------------------------------------------------
@dp.channel_post(F.chat.id == VAULT_CHANNEL_ID)
async def index_vault_post(post: types.Message):
    file_id, file_type = None, None
    if post.document:
        file_id, file_type = post.document.file_id, "document"
    elif post.photo:
        file_id, file_type = post.photo[-1].file_id, "photo"
    elif post.video:
        file_id, file_type = post.video.file_id, "video"

    if file_id:
        code = generate_passcode()
        save_file(code, file_id, file_type)
        
        caption = f"{post.caption or ''}\n\n🔑 **Vault Passcode:** `{code}`".strip()
        try:
            await bot.edit_message_caption(
                chat_id=VAULT_CHANNEL_ID,
                message_id=post.message_id,
                caption=caption,
                parse_mode="Markdown"
            )
        except Exception as e:
            logging.error(f"Failed to edit vault caption: {e}")

# ----------------------------------------------------
# 5. MAIN CHANNEL: Auto-approve join requests
# ----------------------------------------------------
@dp.chat_join_request(F.chat.id == MAIN_CHANNEL_ID)
async def approve_main_channel_join(request: types.ChatJoinRequest):
    await request.approve()
    try:
        await bot.send_message(
            chat_id=request.from_user.id,
            text=(
                f"🎉 **Welcome to {request.chat.title}!**\n\n"
                f"Your request to join was approved.\n"
                f"Send your file passcode (e.g., `DOC-XXXXXX`) directly to me here in DM to access files."
            ),
            parse_mode="Markdown"
        )
    except Exception:
        pass

# ----------------------------------------------------
# 6. DM RETRIEVAL WITH MEMBERSHIP VERIFICATION
# ----------------------------------------------------
@dp.message(F.chat.type == "private", ~F.text.startswith("/"))
async def dm_file_retrieval(message: types.Message):
    user_id = message.from_user.id
    
    # Membership Check Guard
    if not await is_channel_member(bot, user_id):
        join_btn = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 Join Main Channel", url=CHANNEL_INVITE_LINK)]
        ])
        await message.answer(
            "🔒 **Access Restricted!**\n\n"
            "You must be a subscriber of our Main Channel to retrieve vault files.",
            reply_markup=join_btn
        )
        return

    query_code = message.text.strip().upper()
    file_data = get_file(query_code)

    if file_data:
        file_id, file_type, _ = file_data
        increment_download(query_code)
        
        if file_type == "document":
            await message.answer_document(document=file_id, caption=f"📄 Access Granted (`{query_code}`)")
        elif file_type == "photo":
            await message.answer_photo(photo=file_id, caption=f"🖼 Access Granted (`{query_code}`)")
        elif file_type == "video":
            await message.answer_video(video=file_id, caption=f"🎥 Access Granted (`{query_code}`)")
    else:
        await message.answer("❌ Invalid passcode. Please check the code and try again.")

# ----------------------------------------------------
# 7. INLINE RETRIEVAL WITH MEMBERSHIP VERIFICATION
# ----------------------------------------------------
@dp.inline_query()
async def inline_file_retrieval(inline_query: types.InlineQuery):
    user_id = inline_query.from_user.id
    query_code = inline_query.query.strip().upper()
    results = []

    if not await is_channel_member(bot, user_id):
        results.append(InlineQueryResultArticle(
            id="join_required",
            title="🔒 Membership Required",
            description="You must join the Main Channel to access vault files.",
            input_message_content=InputTextMessageContent(message_text="Please join our Main Channel to use this bot!")
        ))
        await bot.answer_inline_query(inline_query.id, results=results, cache_time=1)
        return

    file_data = get_file(query_code)
    if file_data:
        file_id, file_type, _ = file_data
        increment_download(query_code)
        if file_type == "document":
            results.append(InlineQueryResultCachedDocument(id=query_code, title=f"Send Document ({query_code})", document_file_id=file_id))
        elif file_type == "photo":
            results.append(InlineQueryResultCachedPhoto(id=query_code, title=f"Send Photo ({query_code})", photo_file_id=file_id))
        elif file_type == "video":
            results.append(InlineQueryResultCachedVideo(id=query_code, title=f"Send Video ({query_code})", video_file_id=file_id))
    else:
        results.append(InlineQueryResultArticle(
            id="not_found",
            title="Enter a valid Vault Passcode",
            description="Format: DOC-XXXXXX",
            input_message_content=InputTextMessageContent(message_text="Invalid vault passcode.")
        ))

    await bot.answer_inline_query(inline_query.id, results=results, cache_time=1)

# ----------------------------------------------------
# 8. REMINDER & START COMMANDS
# ----------------------------------------------------
@dp.message(Command("remind"))
async def cmd_remind(message: types.Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("⚠️ Format: `/remind 10m Review math notes`", parse_mode="Markdown")
        return

    time_str, reminder_text = args[1].lower(), args[2]
    now = datetime.now()

    if time_str.endswith("m") and time_str[:-1].isdigit():
        delta = timedelta(minutes=int(time_str[:-1]))
    elif time_str.endswith("h") and time_str[:-1].isdigit():
        delta = timedelta(hours=int(time_str[:-1]))
    elif time_str.endswith("d") and time_str[:-1].isdigit():
        delta = timedelta(days=int(time_str[:-1]))
    else:
        await message.answer("❌ Invalid time unit. Use `m`, `h`, or `d`.")
        return

    remind_at = now + delta
    add_reminder(message.from_user.id, reminder_text, remind_at)
    await message.answer(f"✅ **Reminder set for {remind_at.strftime('%H:%M on %Y-%m-%d')}**", parse_mode="Markdown")

@dp.message(Command("reminders"))
async def cmd_list_reminders(message: types.Message):
    cursor.execute("SELECT id, text, remind_at FROM reminders WHERE user_id = ? ORDER BY remind_at ASC", (message.from_user.id,))
    user_rems = cursor.fetchall()
    if not user_rems:
        await message.answer("ℹ️ You have no active reminders.")
        return

    text = "📋 **Your Active Reminders:**\n\n"
    for _, r_text, r_time in user_rems:
        text += f"• `{r_time}` — {r_text}\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 **Xush kelibsiz!**\n\n"
        "• Fayl yuklash kodi: `DOC-A1B2C3`\n"
        "• Dars jadvalini ko'rish: `/schedule` yoki `/schedule du`\n"
        "• Eslatma o'rnatish: `/remind 30m Uyga vazifa bajarish`\n"
        "• Faol eslatmalar: `/reminders`",
        parse_mode="Markdown"
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(background_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())