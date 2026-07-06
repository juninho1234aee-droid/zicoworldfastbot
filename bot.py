import os
import asyncio
import random
import logging
from datetime import datetime, timedelta
 
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile, WebAppInfo
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from supabase import create_client, Client
 
# ---------------------------------------------------------
# SOZLAMALAR (.env fayldan olinadi, kodga hech qachon
# tokenni yozib qo'ymang!)
# ---------------------------------------------------------
load_dotenv()
 
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
MATCH_PLAY_HOURS = float(os.getenv("MATCH_PLAY_HOURS", "24"))
 
if not BOT_TOKEN or not SUPABASE_URL or not SUPABASE_KEY or ADMIN_ID == 0:
    raise RuntimeError(
        "BOT_TOKEN, ADMIN_ID, SUPABASE_URL, SUPABASE_KEY - "
        ".env faylida to'liq to'ldirilganiga ishonch hosil qiling!"
    )
 
logging.basicConfig(level=logging.INFO)
 
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()
sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
 
BOT_NAME = "ZicoWorldFast"
TROPHY_PHOTO = os.path.join(os.path.dirname(__file__), "trophy.jpg")
 
 
class AdminStates(StatesGroup):
    waiting_deadline = State()
 
 
# ===========================================================
# DATABASE YORDAMCHI FUNKSIYALARI (Supabase)
# ===========================================================
 
def db_upsert_user(tg_id: int, username: str | None):
    sb.table("users").upsert({"telegram_id": tg_id, "username": username}).execute()
 
 
def db_get_settings():
    r = sb.table("settings").select("*").eq("id", 1).execute()
    if not r.data:
        sb.table("settings").insert({"id": 1, "maintenance": False}).execute()
        return {"id": 1, "maintenance": False}
    return r.data[0]
 
 
def db_set_maintenance(value: bool):
    sb.table("settings").update({"maintenance": value}).eq("id", 1).execute()
 
 
def db_total_users():
    r = sb.table("users").select("telegram_id", count="exact").execute()
    return r.count or 0
 
 
def db_get_active_tournament():
    r = (
        sb.table("tournaments")
        .select("*")
        .in_("status", ["registration", "ongoing"])
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    return r.data[0] if r.data else None
 
 
def db_create_tournament(size: int, deadline: datetime):
    r = sb.table("tournaments").insert({
        "size": size,
        "status": "registration",
        "deadline": deadline.isoformat()
    }).execute()
    return r.data[0]
 
 
def db_stop_tournament(tid: int):
    sb.table("tournaments").update({"status": "stopped"}).eq("id", tid).execute()
 
 
def db_set_tournament_status(tid: int, status: str):
    sb.table("tournaments").update({"status": status}).eq("id", tid).execute()
 
 
def db_is_registered(tid: int, tg_id: int) -> bool:
    r = (
        sb.table("participants").select("id")
        .eq("tournament_id", tid).eq("telegram_id", tg_id).execute()
    )
    return len(r.data) > 0
 
 
def db_register(tid: int, tg_id: int, username: str):
    sb.table("participants").insert({
        "tournament_id": tid, "telegram_id": tg_id, "username": username
    }).execute()
 
 
def db_count_participants(tid: int) -> int:
    r = sb.table("participants").select("id", count="exact").eq("tournament_id", tid).execute()
    return r.count or 0
 
 
def db_get_participants(tid: int):
    r = sb.table("participants").select("*").eq("tournament_id", tid).execute()
    return r.data
 
 
def db_all_users():
    r = sb.table("users").select("*").execute()
    return r.data
 
 
def db_save_matches(tid: int, pairs):
    rows = []
    match_deadline = (datetime.utcnow() + timedelta(hours=MATCH_PLAY_HOURS)).isoformat()
    for p1, p2 in pairs:
        rows.append({
            "tournament_id": tid,
            "player1_id": p1["telegram_id"],
            "player1_username": p1["username"],
            "player2_id": p2["telegram_id"] if p2 else None,
            "player2_username": p2["username"] if p2 else None,
            "match_deadline": match_deadline if p2 else None,
            "reminder_sent": False,
        })
    if rows:
        r = sb.table("matches").insert(rows).execute()
        return r.data
    return []
 
 
def db_get_match_for_user(tid: int, tg_id: int):
    r = (
        sb.table("matches").select("*").eq("tournament_id", tid)
        .or_(f"player1_id.eq.{tg_id},player2_id.eq.{tg_id}").execute()
    )
    return r.data[0] if r.data else None
 
 
# ===========================================================
# KLAVIATURALAR
# ===========================================================
 
def main_menu_kb(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 Asosiy turnir", callback_data="tournament")],
        [
            InlineKeyboardButton(text="👤 Profil", callback_data="profile"),
            InlineKeyboardButton(text="📜 Qoidalar", callback_data="rules"),
        ],
    ])
    if user_id == ADMIN_ID:
        kb.inline_keyboard.append(
            [InlineKeyboardButton(text="⚙️ Admin panel", callback_data="admin")]
        )
    return kb
 
 
def admin_menu_kb(maintenance: bool) -> InlineKeyboardMarkup:
    m_text = "🔴 Texnik ishlarni o'chirish" if maintenance else "🟢 Texnik ishlarni yoqish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m_text, callback_data="toggle_maint")],
        [InlineKeyboardButton(text="▶️ 32 talik turnir boshlash", callback_data="start_32")],
        [InlineKeyboardButton(text="▶️ 128 talik turnir boshlash", callback_data="start_128")],
        [InlineKeyboardButton(text="⏹ Turnirni to'xtatish", callback_data="stop_tournament")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_main")],
    ])
 
 
def register_kb(tid: int, registered: bool) -> InlineKeyboardMarkup:
    if registered:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Siz ro'yxatdan o'tgansiz", callback_data="noop")]
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ro'yxatdan o'tish", callback_data=f"reg_{tid}")]
    ])
 
 
# ===========================================================
# ASOSIY HANDLERLAR
# ===========================================================
 
@dp.message(CommandStart())
async def start_handler(message: Message):
    db_upsert_user(message.from_user.id, message.from_user.username)
    settings = db_get_settings()
 
    if settings["maintenance"] and message.from_user.id != ADMIN_ID:
        await message.answer("🛠 Hozir texnik ishlar olib borilmoqda. Iltimos, keyinroq qayting.")
        return
 
    caption = f"🏆 <b>{BOT_NAME}</b>\n\neFootball turnirlar botiga xush kelibsiz!\nQuyidagi tugma orqali ilovani oching 👇"
 
    if WEBAPP_URL:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Ilovani ochish", web_app=WebAppInfo(url=WEBAPP_URL))]
        ])
        await message.answer(caption, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(caption, parse_mode="HTML", reply_markup=main_menu_kb(message.from_user.id))
 
 
@dp.message(Command("admin"))
async def admin_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    settings = db_get_settings()
    total = db_total_users()
    tour = db_get_active_tournament()
    active_count = db_count_participants(tour["id"]) if tour else 0
 
    text = (
        f"⚙️ <b>Admin panel</b>\n\n"
        f"👥 Umumiy foydalanuvchilar: {total}\n"
        f"🎮 Faol qatnashuvchilar: {active_count}\n"
        f"🛠 Texnik ishlar: {'YOQILGAN' if settings['maintenance'] else 'O\u02bbCHIRILGAN'}\n"
    )
    if tour:
        text += f"🏆 Faol turnir: {tour['size']} talik ({tour['status']})\n"
 
    await message.answer(
        text, parse_mode="HTML", reply_markup=admin_menu_kb(settings["maintenance"])
    )
 
 
@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.message.answer("🏠 Bosh menyu", reply_markup=main_menu_kb(callback.from_user.id))
    await callback.answer()
 
 
@dp.callback_query(F.data == "rules")
async def rules_handler(callback: CallbackQuery):
    text = (
        "📜 <b>Turnir qoidalari</b>\n\n"
        "⚙️ Match Nastroyka: 8 daqiqa ✅\n"
        "⏱ Extra Time: ✅\n"
        "🥅 Penalti: ✅\n"
        "😊 Kayfiyat: Excellent ✅"
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
 
 
@dp.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    tour = db_get_active_tournament()
    tg_id = callback.from_user.id
    text = f"👤 <b>Profil</b>\nUsername: @{callback.from_user.username or 'yo\u02bbq'}\n"
 
    if tour:
        if db_is_registered(tour["id"], tg_id):
            text += f"\n🏆 Faol turnir: {tour['size']} kishilik\nHolat: ro'yxatdan o'tgansiz ✅\n"
            if tour["status"] == "ongoing":
                match = db_get_match_for_user(tour["id"], tg_id)
                if match:
                    opp = (
                        match["player2_username"]
                        if match["player1_id"] == tg_id
                        else match["player1_username"]
                    )
                    if opp:
                        text += f"\n⚔️ Raqibingiz: @{opp}"
                    else:
                        text += "\n⚔️ Sizga hozircha raqib berilmadi (bye)."
        else:
            text += "\nSiz hali faol turnirga ro'yxatdan o'tmagansiz."
    else:
        text += "\nHozircha faol turnir yo'q."
 
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()
 
 
@dp.callback_query(F.data == "tournament")
async def tournament_handler(callback: CallbackQuery):
    tour = db_get_active_tournament()
    if not tour:
        await callback.message.answer("Hozircha faol turnir yo'q. Kuting ⏳")
        await callback.answer()
        return
 
    if tour["status"] == "registration":
        count = db_count_participants(tour["id"])
        text = (
            f"🏆 <b>{tour['size']} talik turnir</b>\n"
            f"Ro'yxatdan o'tganlar: {count}/{tour['size']}\n"
            f"Muddat: {tour['deadline']}\n"
        )
        registered = db_is_registered(tour["id"], callback.from_user.id)
        await callback.message.answer(
            text, parse_mode="HTML",
            reply_markup=register_kb(tour["id"], registered)
        )
    else:
        match = db_get_match_for_user(tour["id"], callback.from_user.id)
        if match:
            tg_id = callback.from_user.id
            opp = (
                match["player2_username"]
                if match["player1_id"] == tg_id
                else match["player1_username"]
            )
            if opp:
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✉️ Raqibga yozish", url=f"https://t.me/{opp}")
                ]])
                await callback.message.answer(f"⚔️ Sizning raqibingiz: @{opp}", reply_markup=kb)
            else:
                await callback.message.answer("Sizga hozircha raqib tayinlanmadi (bye).")
        else:
            await callback.message.answer("Siz bu turnirda ro'yxatdan o'tmagansiz.")
    await callback.answer()
 
 
@dp.callback_query(F.data.startswith("reg_"))
async def register_handler(callback: CallbackQuery):
    settings = db_get_settings()
    if settings["maintenance"] and callback.from_user.id != ADMIN_ID:
        await callback.answer("🛠 Texnik ishlar olib borilmoqda", show_alert=True)
        return
 
    tid = int(callback.data.split("_")[1])
    tour = db_get_active_tournament()
 
    if not tour or tour["id"] != tid or tour["status"] != "registration":
        await callback.answer("Ro'yxatdan o'tish muddati tugagan.", show_alert=True)
        return
 
    if db_is_registered(tid, callback.from_user.id):
        await callback.answer("Siz allaqachon ro'yxatdan o'tgansiz.", show_alert=True)
        return
 
    if db_count_participants(tid) >= tour["size"]:
        await callback.answer("Turnir joylari to'lgan.", show_alert=True)
        return
 
    if not callback.from_user.username:
        await callback.answer(
            "⚠️ Avval Telegram username o'rnating (Sozlamalar > Username)!",
            show_alert=True
        )
        return
 
    db_register(tid, callback.from_user.id, callback.from_user.username)
    await callback.message.edit_reply_markup(reply_markup=register_kb(tid, True))
    # Yashil belgi bilan yuqorida chiqadigan xabar:
    await callback.answer("✅ Ro'yxatdan o'tdingiz!")
 
 
# ===========================================================
# ADMIN PANEL (faqat ADMIN_ID uchun)
# ===========================================================
 
@dp.callback_query(F.data == "admin")
async def admin_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Ruxsat yo'q.", show_alert=True)
        return
 
    settings = db_get_settings()
    total = db_total_users()
    tour = db_get_active_tournament()
    active_count = db_count_participants(tour["id"]) if tour else 0
 
    text = (
        f"⚙️ <b>Admin panel</b>\n\n"
        f"👥 Umumiy foydalanuvchilar: {total}\n"
        f"🎮 Faol qatnashuvchilar: {active_count}\n"
        f"🛠 Texnik ishlar: {'YOQILGAN' if settings['maintenance'] else 'O\u02bbCHIRILGAN'}\n"
    )
    if tour:
        text += f"🏆 Faol turnir: {tour['size']} talik ({tour['status']})\n"
 
    await callback.message.answer(
        text, parse_mode="HTML", reply_markup=admin_menu_kb(settings["maintenance"])
    )
    await callback.answer()
 
 
@dp.callback_query(F.data == "toggle_maint")
async def toggle_maint(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    settings = db_get_settings()
    new_val = not settings["maintenance"]
    db_set_maintenance(new_val)
    await callback.message.edit_reply_markup(reply_markup=admin_menu_kb(new_val))
    await callback.answer("Yangilandi ✅")
 
 
@dp.callback_query(F.data.in_(["start_32", "start_128"]))
async def start_tournament_ask_deadline(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    if db_get_active_tournament():
        await callback.answer("Avval joriy turnirni to'xtating.", show_alert=True)
        return
 
    size = 32 if callback.data == "start_32" else 128
    await state.update_data(size=size)
    await state.set_state(AdminStates.waiting_deadline)
    await callback.message.answer(
        f"🕒 {size} talik turnir uchun ro'yxatdan o'tish necha soat davom etsin?\n"
        f"Faqat son yuboring (masalan: 3)"
    )
    await callback.answer()
 
 
@dp.message(AdminStates.waiting_deadline)
async def receive_deadline(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        hours = float(message.text.strip())
    except ValueError:
        await message.answer("❌ Iltimos, son kiriting (masalan: 2 yoki 3.5)")
        return
 
    data = await state.get_data()
    size = data["size"]
    deadline = datetime.utcnow() + timedelta(hours=hours)
    tour = db_create_tournament(size, deadline)
 
    scheduler.add_job(
        run_draw, "date", run_date=deadline,
        args=[tour["id"]], id=f"draw_{tour['id']}"
    )
 
    await state.clear()
    await message.answer(f"✅ {size} talik turnir boshlandi!\nMuddat: {hours} soat")
    await broadcast_tournament(tour)
    sb.table("tournaments").update({"broadcasted": True}).eq("id", tour["id"]).execute()
 
 
@dp.callback_query(F.data == "stop_tournament")
async def stop_tournament_handler(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    tour = db_get_active_tournament()
    if not tour:
        await callback.answer("Faol turnir yo'q.", show_alert=True)
        return
 
    db_stop_tournament(tour["id"])
    try:
        scheduler.remove_job(f"draw_{tour['id']}")
    except Exception:
        pass
    await callback.answer("⏹ Turnir to'xtatildi.", show_alert=True)
 
 
async def broadcast_tournament(tour):
    """Barcha ma'lum foydalanuvchilarga yangi turnir haqida xabar yuboradi."""
    users = db_all_users()
    text = (
        f"🏆 <b>Yangi turnir boshlandi!</b>\n"
        f"{tour['size']} talik turnir\n"
        f"Ro'yxatdan o'tish uchun tugmani bosing 👇"
    )
    for u in users:
        try:
            await bot.send_message(
                u["telegram_id"], text, parse_mode="HTML",
                reply_markup=register_kb(tour["id"], False)
            )
        except Exception as e:
            logging.warning(f"Broadcast xato {u['telegram_id']}: {e}")
 
 
async def run_draw(tournament_id: int):
    """Muddat tugaganda avtomatik qura tashlaydi va raqiblarni tayinlaydi."""
    check = sb.table("tournaments").select("*").eq("id", tournament_id).execute().data
    if not check or check[0]["status"] != "registration":
        return
 
    participants = db_get_participants(tournament_id)
    random.shuffle(participants)
 
    pairs = []
    i = 0
    while i < len(participants):
        p1 = participants[i]
        p2 = participants[i + 1] if i + 1 < len(participants) else None
        pairs.append((p1, p2))
        i += 2
 
    saved_matches = db_save_matches(tournament_id, pairs)
    db_set_tournament_status(tournament_id, "ongoing")
 
    for match in saved_matches:
        p1_id, p1_username = match["player1_id"], match["player1_username"]
        p2_id, p2_username = match["player2_id"], match["player2_username"]
 
        if p2_id:
            kb1 = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✉️ Raqibga yozish", url=f"https://t.me/{p2_username}")
            ]])
            kb2 = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="✉️ Raqibga yozish", url=f"https://t.me/{p1_username}")
            ]])
            try:
                await bot.send_message(
                    p1_id,
                    f"⚔️ Qura tashlandi!\nSizning raqibingiz: @{p2_username}\n\n"
                    f"O'ynash uchun {MATCH_PLAY_HOURS:.0f} soat vaqtingiz bor. "
                    f"O'ynab bo'lgach, ilovadagi \"📊 Hisob yozish\" tugmasi orqali natijani kiriting.",
                    reply_markup=kb1
                )
                await bot.send_message(
                    p2_id,
                    f"⚔️ Qura tashlandi!\nSizning raqibingiz: @{p1_username}\n\n"
                    f"O'ynash uchun {MATCH_PLAY_HOURS:.0f} soat vaqtingiz bor. "
                    f"O'ynab bo'lgach, ilovadagi \"📊 Hisob yozish\" tugmasi orqali natijani kiriting.",
                    reply_markup=kb2
                )
            except Exception as e:
                logging.warning(f"Xabar yuborishda xato: {e}")
 
            if match.get("match_deadline"):
                deadline = datetime.fromisoformat(match["match_deadline"].replace("Z", "+00:00")).replace(tzinfo=None)
                remind_at = deadline - timedelta(hours=2)
                if remind_at > datetime.utcnow():
                    scheduler.add_job(
                        send_match_reminder, "date", run_date=remind_at,
                        args=[match["id"], p1_id, p1_username, p2_id, p2_username],
                        id=f"reminder_{match['id']}", replace_existing=True
                    )
        else:
            try:
                await bot.send_message(
                    p1_id,
                    "🎉 Sizga bu bosqichda raqib chiqmadi (bye). Keyingi bosqichni kuting."
                )
            except Exception:
                pass
 
 
async def send_match_reminder(match_id: int, p1_id: int, p1_username: str, p2_id: int, p2_username: str):
    """Match muddatiga 2 soat qolganda ikkala o'yinchiga eslatma yuboradi."""
    try:
        r = sb.table("matches").select("reminder_sent").eq("id", match_id).execute()
        if not r.data or r.data[0].get("reminder_sent"):
            return
        kb1 = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✉️ Raqibga yozish", url=f"https://t.me/{p2_username}")
        ]])
        kb2 = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✉️ Raqibga yozish", url=f"https://t.me/{p1_username}")
        ]])
        text = (
            "⏰ <b>Diqqat!</b> O'yiningizni tugatishga <b>2 soat</b> qoldi!\n\n"
            "Agar belgilangan vaqtda o'ynamasangiz, turnirdan chetlatilishingiz mumkin. "
            "Raqibingiz bilan tezroq bog'laning ⚡"
        )
        await bot.send_message(p1_id, text, parse_mode="HTML", reply_markup=kb1)
        await bot.send_message(p2_id, text, parse_mode="HTML", reply_markup=kb2)
        sb.table("matches").update({"reminder_sent": True}).eq("id", match_id).execute()
    except Exception as e:
        logging.warning(f"Eslatma yuborishda xato: {e}")
 
 
async def restore_jobs():
    """Bot qayta ishga tushganda faol turnirlar uchun deadline joblarini tiklaydi."""
    r = sb.table("tournaments").select("*").eq("status", "registration").execute()
    for tour in r.data:
        deadline = datetime.fromisoformat(tour["deadline"].replace("Z", "+00:00")).replace(tzinfo=None)
        if deadline <= datetime.utcnow():
            await run_draw(tour["id"])
        else:
            scheduler.add_job(
                run_draw, "date", run_date=deadline,
                args=[tour["id"]], id=f"draw_{tour['id']}", replace_existing=True
            )
 
 
async def sync_tournaments():
    """
    Har 30 soniyada tekshiradi: Mini App (webapp) orqali admin yangi turnir
    yaratgan bo'lsa, buni bot avtomatik payqab, hammaga xabar yuboradi va
    muddat tugaganda qura tashlashni rejalashtiradi. Shuningdek, qayta ishga
    tushgandan keyin yo'qolib qolgan eslatma joblarini ham tiklaydi.
    """
    try:
        r = sb.table("tournaments").select("*").eq("status", "registration").execute()
        for tour in r.data:
            job_id = f"draw_{tour['id']}"
            deadline = datetime.fromisoformat(tour["deadline"].replace("Z", "+00:00")).replace(tzinfo=None)
 
            if not scheduler.get_job(job_id):
                if deadline <= datetime.utcnow():
                    await run_draw(tour["id"])
                else:
                    scheduler.add_job(
                        run_draw, "date", run_date=deadline,
                        args=[tour["id"]], id=job_id, replace_existing=True
                    )
 
            if not tour.get("broadcasted"):
                await broadcast_tournament(tour)
                sb.table("tournaments").update({"broadcasted": True}).eq("id", tour["id"]).execute()
 
        # Eslatma joblarini tiklash (bot qayta ishga tushganda)
        mr = (
            sb.table("matches").select("*")
            .eq("reminder_sent", False)
            .not_.is_("match_deadline", "null")
            .not_.is_("player2_id", "null")
            .execute()
        )
        for match in mr.data:
            job_id = f"reminder_{match['id']}"
            if scheduler.get_job(job_id):
                continue
            deadline = datetime.fromisoformat(match["match_deadline"].replace("Z", "+00:00")).replace(tzinfo=None)
            remind_at = deadline - timedelta(hours=2)
            if remind_at <= datetime.utcnow():
                await send_match_reminder(
                    match["id"], match["player1_id"], match["player1_username"],
                    match["player2_id"], match["player2_username"]
                )
            else:
                scheduler.add_job(
                    send_match_reminder, "date", run_date=remind_at,
                    args=[match["id"], match["player1_id"], match["player1_username"],
                          match["player2_id"], match["player2_username"]],
                    id=job_id, replace_existing=True
                )
    except Exception as e:
        logging.warning(f"sync_tournaments xato: {e}")
 
 
async def main():
    db_get_settings()
    await restore_jobs()
    scheduler.add_job(sync_tournaments, "interval", seconds=30, id="sync_tournaments")
    scheduler.start()
    logging.info("Bot ishga tushdi...")
    await dp.start_polling(bot)
 
 
if __name__ == "__main__":
    asyncio.run(main())
