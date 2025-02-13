from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart,Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import sqlite3
import logging
import asyncio
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
API_TOKEN = '7700338122:AAEGk9G4LVzzVR5tTFfCHl2nZPnYsfrwVlQ'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# SQLite Database connection
db = sqlite3.connect("KinoMan.db")
cursor = db.cursor()

# Create movies table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        video_file_id TEXT,
        file_size INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
""")

# Create blocked users table if not exists
cursor.execute("""
    CREATE TABLE IF NOT EXISTS blocked_users (
        user_id INTEGER PRIMARY KEY
    );
""")
db.commit()

class PostStates(StatesGroup):
    waiting_for_video = State()

class PostS(StatesGroup):
    waiting_for_user_id = State()
class States(StatesGroup):
    waiting_for_movie_name = State()
    waiting_for_new_movie_name = State()
# Admin IDs
ADMINS = {7660718520}  # Admin ID

MOVIES_PER_PAGE = 5  # Number of movies per page
# Foydalanuvchini ma'lumotlar bazasiga qo'shish
def add_user_to_db(user_id, username):
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    db.commit()

# Save movie to database
def save_movie_to_db(name, video_file_id, file_size):
    cursor.execute(
        "INSERT INTO movies (name, video_file_id, file_size) VALUES (?, ?, ?)",
        (name, video_file_id, file_size)
    )
    db.commit()


@dp.message(CommandStart())
async def start_command(message: types.Message, state: FSMContext):

    # Add user to database
    add_user_to_db(message.from_user.id, message.from_user.username)
    # Foydalanuvchi kanalga obuna bo'lsa
    if message.from_user.id in ADMINS:
        await message.reply("/del - Kino o'chirish\n/conv - Kinoni nomi o'zgartirish")
    else:
        await message.reply("🛑Diqqat qiling\n 1️⃣Kino yoki serial nomini aniq kiriting. To‘g‘ri yozilgan nom qidiruv natijalarini aniqlashtiradi va kerakli filmni tezroq topadi.\n2️⃣ Agar natija topilmasa: O‘xshash natijalar ko‘rsatilishi mumkin. Agar izlagan narsangiz topilmasa, bizning qo‘llab-quvvatlash guruhimizga yozing: @KinoSuhbatuz.")
@dp.message(F.video)
async def handle_video(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMINS:
        video_file_id = message.video.file_id
        file_size = message.video.file_size
        await state.update_data(file_id=video_file_id, file_size=file_size)  # Fayl ma'lumotlarini holatda saqlash

        caption = message.caption
        if caption:
            match = re.search(r'"(.*?)"', caption)  # Qoʻshtirnoq ichidagi matnni olish
            if match:
                movie_name = match.group(1)  # Faqat qoʻshtirnoq ichidagi qismni olish
            else:
                movie_name = caption  # Agar qoʻshtirnoq ichida matn bo‘lmasa, to‘liq captionni olish

            # Kino ma'lumotlarini ma'lumotlar bazasiga saqlash
            save_movie_to_db(movie_name, video_file_id, file_size)
            await message.answer(f"Kino nomi saqlandi: {movie_name}")
            
            await state.clear()  # Holatni tozalash
        else:
            await message.answer("Iltimos, video bilan birga kino nomini qo‘shing.")
    else:
        print("Salom")
# Update movie name in database
def update_movie_name(old_name, new_name):
    cursor.execute("UPDATE movies SET name = ? WHERE name = ?", (new_name, old_name))
    db.commit()
@dp.message(Command("del"))
async def delete_movie_start(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMINS:
        await message.answer("🗑 Iltimos, o‘chirmoqchi bo‘lgan kino nomini kiriting:")
        await state.set_state(States.waiting_for_movie_name)  # Set state to wait for movie name
    else:
        await message.answer("Siz admin emassiz.")

@dp.message(States.waiting_for_movie_name, F.text)
async def confirm_movie_deletion(message: types.Message, state: FSMContext):
    movie_name = message.text.strip()
    cursor.execute("SELECT id, name FROM movies WHERE name = ?", (movie_name,))
    movie = cursor.fetchone()

    if movie:
        # Show confirmation message with buttons
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Ha", callback_data=f"delete_confirm_{movie[0]}"),
                    InlineKeyboardButton(text="❌ Yo'q", callback_data="delete_cancel")
                ]
            ]
        )
        await message.answer(f"Kino nomi '{movie_name}' topildi. O‘chirishni tasdiqlaysizmi?", reply_markup=keyboard)
        await state.clear()
    else:
        await message.answer(f"Kino nomi '{movie_name}' topilmadi. Iltimos, boshqa nom kiriting yoki /del buyrug‘ini qayta urinib ko‘ring.")
        await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delete_confirm_"))
async def delete_movie_confirmed(callback_query: types.CallbackQuery):
    movie_id = int(callback_query.data.split('_')[2])
    cursor.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
    db.commit()

    await callback_query.message.edit_text("✅ Kino muvaffaqiyatli o‘chirildi.")
    await callback_query.answer()

@dp.callback_query(lambda c: c.data == "delete_cancel")
async def delete_movie_canceled(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("❌ Kino o‘chirish bekor qilindi.")
    await callback_query.answer()

# /conv command handler
@dp.message(Command("conv"))
async def start_conv(message: types.Message, state: FSMContext):
    if message.from_user.id in ADMINS:
        await message.answer("🎬 Iltimos, o'zgartirmoqchi bo'lgan kino nomini kiriting.")
        await state.set_state(States.waiting_for_movie_name)
    else:
        await message.answer("Siz admin emassiz.")

# Handle movie name input
@dp.message(States.waiting_for_movie_name, F.text)
async def handle_movie_name(message: types.Message, state: FSMContext):
    movie_name = message.text.strip()

    # Check if the movie exists in the database
    cursor.execute("SELECT name FROM movies WHERE name = ?", (movie_name,))
    movie = cursor.fetchone()

    if movie:
        await message.answer(f"Kino '{movie_name}' topildi. Iltimos, yangi kino nomini kiriting.")
        await state.update_data(existing_movie_name=movie_name)  # Save the existing movie name to state
        await state.set_state(States.waiting_for_new_movie_name)
    else:
        await message.answer(f"Kino nomi '{movie_name}' topilmadi. Iltimos, boshqa kino nomini kiriting.")
        await state.set_state(States.waiting_for_movie_name)

# Handle new movie name input
@dp.message(States.waiting_for_new_movie_name, F.text)
async def handle_new_movie_name(message: types.Message, state: FSMContext):
    new_movie_name = message.text.strip()

    # Get the existing movie name from state
    data = await state.get_data()
    existing_movie_name = data.get('existing_movie_name')

    if existing_movie_name:
        # Update the movie name in the database
        update_movie_name(existing_movie_name, new_movie_name)
        await message.answer(f"Kino nomi '{existing_movie_name}' yangilandi: {new_movie_name}")
        await state.clear()
    else:
        await message.answer("Ma'lumotlar topilmadi. Iltimos, qayta urinib ko‘ring.")
        await state.clear()
import logging

# Loggerni sozlash
logger = logging.getLogger(__name__)

def get_pagination_keyboard(current_page, total_pages):
    """Generate pagination buttons."""
    keyboard = InlineKeyboardBuilder()

    if current_page > 1:
        keyboard.add(InlineKeyboardButton(text="◀️", callback_data=f"page_{current_page - 1}"))
    if current_page < total_pages:
        keyboard.add(InlineKeyboardButton(text="▶️", callback_data=f"page_{current_page + 1}"))

    return keyboard.as_markup()

MOVIES_PER_PAGE = 10  # Number of movies per page

async def show_movies_page(chat_id: int, movies: list, current_page: int, message_id: int, state: FSMContext):
    total_pages = (len(movies) + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE
    start_idx = (current_page - 1) * MOVIES_PER_PAGE
    end_idx = min(current_page * MOVIES_PER_PAGE, len(movies))

    movie_list_text = ""
    builder = InlineKeyboardBuilder()

    for idx, movie in enumerate(movies[start_idx:end_idx], start=start_idx + 1):
        movie_name = movie[1]
        file_size = round(movie[2] / (1024 * 1024), 2)  # MBga aylantirish va yaxlitlash
        movie_list_text += f"{idx}. <b>{movie_name}</b> - {file_size} MB\n"
        builder.add(InlineKeyboardButton(text=f"{idx}", callback_data=f"movie_{movie[0]}"))

    pagination_keyboard = get_pagination_keyboard(current_page, total_pages)

    if pagination_keyboard.inline_keyboard:
        builder.row(*pagination_keyboard.inline_keyboard[0])

    keyboard = builder.as_markup()

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"Topilgan kinolar ro‘yxati:\n\n{movie_list_text}",
            reply_markup=keyboard,
            parse_mode="html"
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        new_message = await bot.send_message(
            chat_id=chat_id,
            text=f"Topilgan kinolar ro'yxati:\n{movie_list_text}",
            reply_markup=keyboard,
            parse_mode="html"
        )
        await state.update_data(message_id=new_message.message_id)
        return new_message
    return None

@dp.callback_query(lambda c: c.data.startswith("page_"))
async def on_page_select(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        page_number = int(callback_query.data.split('_')[1])
        user_data = await state.get_data()
        movies = user_data.get("movies", [])
        message_id = user_data.get("message_id")
        await show_movies_page(callback_query.message.chat.id, movies, page_number, message_id, state)
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Error in on_page_select: {e}")
        await callback_query.answer("Xatolik yuz berdi. Keyinroq urinib ko'ring.")
       
async def suggest_movies(chat_id: int, message_id: int, suggested_movies: list):
    """Kino topilmaganda taklif qilinadigan kinolarni ko'rsatish."""
    movie_list_text = "Kino topilmadi. Lekin quyidagilarni birisi bo'lishi mumkin:\n\n"
    builder = InlineKeyboardBuilder()

    # Taklif qilinadigan kinolarni ro'yxatga olish va tugmalarni qo'shish
    for idx, movie in enumerate(suggested_movies, start=1):
        movie_name = movie[1]
        file_size = round(movie[2] / (1024 * 1024), 2)  # Fayl hajmini MB ga aylantirish
        movie_list_text += f"{idx}. <b>{movie_name}</b> - {file_size} MB\n"
        builder.add(InlineKeyboardButton(text=f"{idx}", callback_data=f"movie_{movie[0]}"))

    keyboard = builder.as_markup()

    try:
        # Eski xabarni yangilash
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=movie_list_text,
            reply_markup=keyboard,
            parse_mode="html"  # HTML formatdan foydalanish
        )
    except Exception as e:
        # Agar xabarni tahrirlashda xato bo'lsa, yangi xabar yuborish
        logger.error(f"Error editing suggestion message: {e}")
        new_message = await bot.send_message(
            chat_id=chat_id,
            text=movie_list_text,
            reply_markup=keyboard,
            parse_mode="html"
        )
        return new_message

    return None

@dp.message(F.text)
async def search_movie_by_name(message: types.Message, state: FSMContext):
    query = message.text.lower()  # Qidiruv so'rovini kichik harflarga o'zgartirish
    cursor.execute("SELECT id, name, file_size FROM movies WHERE LOWER(name) LIKE ?", ('%' + query + '%',))
    movies = cursor.fetchall()  # Asosiy mos kinolarni olish

    if not movies:
        # Adminlarga xabar yuborish
        admin_message = f"Kino topilmadi: So'rov: {message.text}"
        for admin_id in ADMINS:
            await bot.send_message(admin_id, admin_message)

        # So'rovning dastlabki 3 harfini olib, boshqa takliflar uchun foydalanish
        if len(query) >= 3:
            prefix = query[:3]
            cursor.execute("SELECT id, name, file_size FROM movies WHERE LOWER(name) LIKE ?", (prefix + '%',))
            suggested_movies = cursor.fetchall()

            if suggested_movies:
                # Taklif qilinadigan kinolarni InlineKeyboard bilan chiqarish
                await suggest_movies(chat_id=message.chat.id, message_id=message.message_id, suggested_movies=suggested_movies)
            else:
                await message.answer("Hech qanday mos kino topilmadi.")
        else:
            await message.answer("Qidiruv so'rovi juda qisqa.")
        return

    # Topilgan kinolarni saqlash va ko'rsatish
    await state.update_data(movies=movies, current_page=1)
    new_message = await show_movies_page(message.chat.id, movies, 1, message.message_id, state)
    await state.update_data(message_id=new_message.message_id)


@dp.callback_query(lambda c: c.data.startswith("movie_"))
async def send_movie_video(callback_query: types.CallbackQuery):
    try:
        movie_id = int(callback_query.data.split('_')[1])
        cursor.execute("SELECT name, video_file_id, file_size FROM movies WHERE id = ?", (movie_id,))
        movie = cursor.fetchone()

        if movie:
            movie_name, video_file_id, file_size = movie
            file_size_mb = round(file_size / (1024 * 1024), 2)
            caption = (
                f"🎬 Nomi: {movie_name}\n"
                f"📦 Hajmi: {file_size_mb} MB\n\n"
                f"©️ Kanalimiz: @UZHDFilmsRasmiy\n"
                f"🤖 Botimiz: @UZHDFilmsBot"
            )
            await bot.send_video(callback_query.from_user.id, video_file_id, caption=caption)
        else:
            await callback_query.answer("Kino topilmadi.", show_alert=True)
    except Exception as e:
        logger.error(f"Error in send_movie_video: {e}")
        await callback_query.answer("Xatolik yuz berdi. Keyinroq urinib ko'ring.")
    finally:
        await callback_query.answer()



async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
