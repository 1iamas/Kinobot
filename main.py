from aiogram import Bot, Dispatcher, types,F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import json
import logging
import sqlite3
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
import logging
import json
import re
CHANNEL_ID = '@asdfgheqoqq'

# API token
ADMINS = [7021509411]  # Admin IDlari ro'yxati
API_TOKEN = '7503877141:AAGS7_5sptP9CiZ1l4LHUGIHvj9IGWQFELE'
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher obyektlarini yaratish
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
def get_unique_years():
    movies = load_movies()  # JSON fayldagi barcha filmlarni yuklash
    years = set(movie['yili'] for movie in movies)  # Yillarni unikal qilish uchun set()dan foydalanamiz
    return sorted(years)  # Yillarni tartib bilan qaytaramiz

# JSON faylidan ma'lumot yuklash
def load_movies():
    with open("index.json", "r", encoding="utf-8") as file:
        return json.load(file)

def increment_movie_send_count(movie_id):
    conn = sqlite3.connect('votes.db')
    c = conn.cursor()
    
    # Film bazada borligini tekshiramiz
    c.execute("SELECT send_count FROM movie_sends WHERE movie_id = ?", (movie_id,))
    result = c.fetchone()

    if result:
        # Film bor bo'lsa, send_count ni oshiramiz
        c.execute("UPDATE movie_sends SET send_count = send_count + 1 WHERE movie_id = ?", (movie_id,))
    else:
        # Film bo'lmasa, yangi yozuv qo'shamiz
        c.execute("INSERT INTO movie_sends (movie_id, send_count) VALUES (?, 1)", (movie_id,))
    
    conn.commit()
    conn.close()

def get_movie_send_count(movie_id):
    conn = sqlite3.connect('votes.db')
    c = conn.cursor()
    c.execute("SELECT send_count FROM movie_sends WHERE movie_id = ?", (movie_id,))
    result = c.fetchone()
    conn.close()
    
    return result[0] if result else 0

# Filmlar yuborilishini hisoblash uchun jadval yaratish
def create_db():
    conn = sqlite3.connect('votes.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS votes
                 (user_id INTEGER, movie_id TEXT, vote TEXT, start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS movie_sends
                 (movie_id TEXT PRIMARY KEY, send_count INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
create_db()

@dp.message(Command("start"))
async def start_command(message: types.Message):
    with open('index.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Kino, multfilm va seriallarni hisoblash
    movie_count = sum(1 for movie in data if movie['turi'] == 'kino')
    cartoon_count = sum(1 for movie in data if movie['turi'] == 'multfilm')
    jami=movie_count+cartoon_count
    greeting = "🌟Salom! Sizga kino topishda yordam berish uchun tayyorman!🤝"
    instructions = "Kino nomini yozing yoki quyidagilardan birini tanlang:"

    search_methods = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Chiqqan yili bo'yicha qidirish", callback_data="search_year")],
        [InlineKeyboardButton(text="🌍 Davlat bo'yicha qidirish", callback_data="search_country")],
        [InlineKeyboardButton(text="🔥 Eng ko'p yuborilganlar", callback_data="search_sent")],
        [InlineKeyboardButton(text="👍 Eng ko'p like olganlar", callback_data="search_liked")],
        [InlineKeyboardButton(text="🎭 Janr bo'yicha qidirish", callback_data="search_genre")],
    ])

    await message.answer(f"{greeting}\nKino: {movie_count} ta\nMultfilm: {cartoon_count} ta\nJami: {jami} ta")
    await message.answer(instructions, reply_markup=search_methods)
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = message.from_user.id
    user_name = message.from_user.username
    full_name = message.from_user.full_name
    await bot.send_message(7021509411, f"Yangi foydalanuvchi start bosdi:\n\nID: {user_id}\nUsername: @{user_name}\nIsm: {full_name}\nVaqti: {current_time}")
    user_id = message.from_user.id
    if user_id in ADMINS:
     markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Kino soni", callback_data="movie_count")],
        [InlineKeyboardButton(text="Obunachi soni", callback_data="user_count")],
        [InlineKeyboardButton(text="Majburiy kanal", callback_data="mandatory_channel")]
    ])
    await message.answer("Salom Admin! Siz quyidagi vazifalarni bajara olasiz:", reply_markup=markup)


# FSM states for adding movie/multfilm
class AddVideo(StatesGroup):
    waiting_for_type = State()
    waiting_for_video = State()
    confirming_data = State()
    editing_field = State()

# /start command handler
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.reply("Salom! Ma'lumot qo'shmoqchi bo'lsangiz, /add komandasini yuboring.")

# /add command handler
@dp.message(Command("add"))
async def add_command(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Kino", callback_data="kino")],
            [InlineKeyboardButton(text="Multfilm", callback_data="multfilm")],
            [InlineKeyboardButton(text="Serial", callback_data="serial")],
        ]
    )
    await message.reply("Kino yoki multfilm qo'shmoqchimisiz?", reply_markup=keyboard)
    await state.set_state(AddVideo.waiting_for_type)

# Ma'lumot turini tanlash (kino yoki multfilm)
@dp.callback_query(lambda c: c.data in ["kino", "multfilm", "serial"])
async def handle_type_callback(callback_query: CallbackQuery, state: FSMContext):
    selected_type = callback_query.data
    await state.update_data(selected_type=selected_type)

    await callback_query.message.edit_text(f"Turi: {selected_type.capitalize()}. Endi video yuboring.")
    await state.set_state(AddVideo.waiting_for_video)

# Video qabul qilish
@dp.message(F.video, AddVideo.waiting_for_video)
async def handle_video(message: types.Message, state: FSMContext):
    video = message.video
    caption = message.caption if message.caption else ""

    # Ma'lumotlarni olish
    name_match = re.search(r'Nomi:\s*(.+?)\n|🎬\s*(.+?)\n|Kino nomi:\s*(.+?)\n|^(.+)', caption)
    name = name_match.group(1) or name_match.group(2) or name_match.group(3) or name_match.group(4) if name_match else "Noma'lum"
    name = name.strip()

    genre_match = re.search(r'Janri:\s*(.+?)\n|Janr\s*(.+?)\n', caption)
    genre = genre_match.group(1) or genre_match.group(2) if genre_match else "Janrsiz"
    genre = "#" + " #".join(genre.split()) if genre != "Janrsiz" else genre

    year_match = re.search(r'Yili\s*\((\d{4})\)', caption)
    year = year_match.group(1) if year_match else "Yilsiz"

    file_size_in_bytes = video.file_size
    size_in_mb = round(file_size_in_bytes / (1024 * 1024), 2)
    size = f'{size_in_mb} MB'

    sifat = f"{video.height}p"
    age =  "Yoshsiz"
    country="Davlatsiz"

    # Holatga ma'lumotlarni saqlash
    await state.update_data(video=video, name=name, genre=genre, year=year, sifat=sifat, size=size, age=age,country=country)

    # Tahrirlash va tasdiqlash uchun tugmalar
    edit_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Nomi: {name}", callback_data="edit_name")],
            [InlineKeyboardButton(text=f"Janr: {genre}", callback_data="edit_genre")],
            [InlineKeyboardButton(text=f"Yil: {year}", callback_data="edit_year")],
            [InlineKeyboardButton(text=f"Sifat: {sifat}", callback_data="edit_quality")],
            [InlineKeyboardButton(text=f"Hajm: {size}", callback_data="edit_size")],
            [InlineKeyboardButton(text=f"Yosh chegarasi: {age}", callback_data="edit_age")],
            [InlineKeyboardButton(text=f"Davlati: {country}", callback_data="edit_country")],
            [InlineKeyboardButton(text="Tasdiqlash", callback_data="confirm")],
        ]
    )
    await message.reply("Quyidagi ma'lumotlar qo'shildi:", reply_markup=edit_keyboard)
    await state.set_state(AddVideo.confirming_data)

# Ma'lumotni o'zgartirish jarayoni
@dp.callback_query(lambda c: c.data.startswith("edit_"),AddVideo.confirming_data)
async def edit_field_callback(callback_query: CallbackQuery, state: FSMContext):
    field_to_edit = callback_query.data.split("_")[1]
    await state.update_data(field_to_edit=field_to_edit)

    # Foydalanuvchidan o'zgartirish uchun yangi qiymatni so'rash
    await callback_query.message.answer(f"{field_to_edit.capitalize()} ni o'zgartirmoqchimisiz? Yangi qiymatni kiriting.")
    await state.set_state(AddVideo.editing_field)

# O'zgartirilgan qiymatni qabul qilish
@dp.message(AddVideo.editing_field)
async def save_new_value(message: types.Message, state: FSMContext):
    new_value = message.text
    data = await state.get_data()
    field_to_edit = data['field_to_edit']

    # Ma'lumotlarni yangilash
    if field_to_edit == "name":
        await state.update_data(name=new_value)
    elif field_to_edit == "genre":
        await state.update_data(genre=new_value)
    elif field_to_edit == "year":
        await state.update_data(year=new_value)
    elif field_to_edit == "quality":
        await state.update_data(sifat=new_value)
    elif field_to_edit == "size":
        await state.update_data(size=new_value) 
    elif field_to_edit == "age":
        await state.update_data(age=new_value)
    elif field_to_edit == "country":
        await state.update_data(country=new_value)

    # Yangi tugmalar bilan yangilangan ma'lumotni qayta chiqarish
    updated_data = await state.get_data()
    name = updated_data['name']
    genre = updated_data['genre']
    year = updated_data['year']
    sifat = updated_data['sifat']
    size = updated_data['size']
    age= updated_data['age']
    country= updated_data['country']
    edit_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"Nomi: {name}", callback_data="edit_name")],
            [InlineKeyboardButton(text=f"Janr: {genre}", callback_data="edit_genre")],
            [InlineKeyboardButton(text=f"Yil: {year}", callback_data="edit_year")],
            [InlineKeyboardButton(text=f"Sifat: {sifat}", callback_data="edit_quality")],
            [InlineKeyboardButton(text=f"Hajm: {size}", callback_data="edit_size")],
            [InlineKeyboardButton(text=f"Yosh chegarasi: {age}", callback_data="edit_age")],
            [InlineKeyboardButton(text=f"Davlati: {country}", callback_data="edit_country")],
            [InlineKeyboardButton(text="Tasdiqlash", callback_data="confirm")],
        ]
    )

    await message.reply(f"Yangilangan ma'lumot: {field_to_edit.capitalize()} o'zgartirildi!", reply_markup=edit_keyboard)
    await state.set_state(AddVideo.confirming_data)

# Tasdiqlash va saqlash
@dp.callback_query(lambda c: c.data == 'confirm', AddVideo.confirming_data)
async def confirm_data(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    video = data['video']
    name = data['name']
    genre = data['genre']
    year = data['year']
    sifat = data['sifat']
    size = data['size']
    age = data['age']
    country = data['country']
    selected_type = data['selected_type']

    # Video kanalda yuborish
    sent_message = await bot.send_video(CHANNEL_ID, video.file_id, caption=(
                f"🎬 Nomi: {name}\n"
                f"📅 Yili: {year}\n"
                f"🎥 Janri: {genre}\n"
                f"📽️ Sifati: {sifat}\n"
                f"🗃 Hajmi: {size}\n"
                f"🔞 Yosh chegarasi: {age}\n"
                f"🌍 Davlati: {country}\n"
            ))

    # Kanaldagi video linkini olish
    video_link = f"https://t.me/{CHANNEL_ID.strip('@')}/{sent_message.message_id}"

    # JSON faylini o'qish yoki yaratish
    try:
        with open('index.json', 'r') as file:
            json_data = json.load(file)
    except FileNotFoundError:
        json_data = []

    # Yangi ob'ektni qo'shish
    new_entry = {
        "nomi": name,
        "turi": selected_type,
        "janri": genre,
        "yili": year,
        "id": video_link,
        "sifati": sifat,
        "hajmi": size,
        "yoshi": age,
        "davlati": country
    }
    json_data.append(new_entry)

    # O'zgartirilgan ma'lumotlarni JSON fayliga yozish
    with open('index.json', 'w') as file:
        json.dump(json_data, file, indent=4)

    await callback_query.message.reply(f"Ma'lumot muvaffaqiyatli qo'shildi! {video_link}")
    await state.clear()
# Holatni aniqlash
class MovieSearchState(StatesGroup):
    waiting_for_year = State()
    waiting_for_country=State()
    waiting_for_genre=State()
    
MOVIES_PER_PAGE = 5  # Har bir sahifada nechta yil ko'rsatilishini belgilaymiz

async def display_years(message: types.Message, years, page: int = 1):
    total_years = len(years)
    total_pages = (total_years + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE  # Umumiy sahifalar soni

    # Sahifa uchun yillarni ajratib olamiz
    start_idx = (page - 1) * MOVIES_PER_PAGE
    end_idx = start_idx + MOVIES_PER_PAGE

    current_years = years[start_idx:end_idx]

    # Inline tugmalarni yaratamiz
    builder = InlineKeyboardBuilder()
    for year in current_years:
        builder.add(InlineKeyboardButton(text=str(year), callback_data=f"year_{year}"))

    # Paginatsiya tugmalari
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"page_year_{page - 1}"))
    if page < total_pages:
        pagination_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"page_year_{page + 1}"))

    pagination_buttons.append(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))

    # Tugmalarni qo'shamiz
    builder.row(*pagination_buttons)

    # Xabarni yuborish yoki tahrir qilish
    if message.reply_markup is None:
        await message.answer("Tanlang:", reply_markup=builder.as_markup())
    else:
        await message.edit_reply_markup(reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == 'search_year')
async def show_years(callback_query: types.CallbackQuery):
    years = get_unique_years()  # Yillarni olish
    if years:
        await display_years(callback_query.message, years)
    else:
        await callback_query.message.answer("Hech qanday yil topilmadi.")

@dp.callback_query(lambda c: c.data.startswith('page_year_'))
async def handle_year_pagination(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split('_')[2])
    years = get_unique_years()  # Yillarni qayta yuklaymiz
    await display_years(callback_query.message, years, page)

# 3. Foydalanuvchi yilni tanlaganda, o'sha yilga tegishli filmlarni ko'rsatish
@dp.callback_query(lambda c: c.data.startswith('year_'))
async def show_movies_by_year(callback_query: types.CallbackQuery):
    selected_year = callback_query.data.split('_')[1]
    movies = load_movies()  # Barcha filmlarni yuklash
    filtered_movies = [movie for movie in movies if movie['yili'] == selected_year]  # Tanlangan yil bo'yicha filtr
    
    if filtered_movies:
        await display_movies(callback_query.message, filtered_movies)
    else:
        await callback_query.message.answer(f"{selected_year}-yil uchun hech qanday film topilmadi.")
    
    await callback_query.answer()


@dp.callback_query(lambda c: c.data == "search_country")
async def show_countries(callback_query: types.CallbackQuery):
    countries = [
        "AQSH", 
        "Rossiya", 
        "Xitoy", 
        "Britaniya", 
        "Hindiston", 
        "Janubiy Koreya", 
    ]
# Siz kerakli davlatlar ro'yxatini qo'shishingiz mumkin

    country_buttons = [
        [InlineKeyboardButton(text=country, callback_data=f"country_{country}")]
        for country in countries
    ]
    country_buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search")])

    country_keyboard = InlineKeyboardMarkup(inline_keyboard=country_buttons)

    await callback_query.message.edit_text("Davlatni tanlang:", reply_markup=country_keyboard)

# Davlat bo'yicha film ko'rsatish
@dp.callback_query(lambda c: c.data.startswith('country_'))
async def show_movies_by_country(callback_query: types.CallbackQuery):
    selected_country = callback_query.data.split('_')[1]
    movies = load_movies()
    filtered_movies = [movie for movie in movies if movie['davlati'] == selected_country]  # Tanlangan davlat bo'yicha filtr

    if filtered_movies:
        await display_movies(callback_query.message, filtered_movies)
    else:
        # Agar kino topilmasa, matnni yangilash
        response_message = f"{selected_country} davlatida hech qanday film topilmadi."
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))

        await callback_query.message.edit_text(response_message, reply_markup=builder.as_markup())


@dp.callback_query(lambda c: c.data == 'search_liked')
async def search_most_liked(callback_query: types.CallbackQuery, page: int = 1):
    conn = sqlite3.connect('votes.db')
    c = conn.cursor()

    # Eng ko'p like olgan 10 ta kinoni olish
    c.execute("""
        SELECT movie_id, COUNT(*) as like_count 
        FROM votes 
        WHERE vote = 'like' 
        GROUP BY movie_id 
        ORDER BY like_count DESC 
        LIMIT ?, ?
    """, ((page - 1) * MOVIES_PER_PAGE, MOVIES_PER_PAGE))
    liked_movies = c.fetchall()

    conn.close()

    # Kino ma'lumotlarini yuklash va filtr
    if liked_movies:
        movies = load_movies()
        filtered = [movie for movie in movies if movie['id'] in [m[0] for m in liked_movies]]
        
        if filtered:
            await display_movies(callback_query.message, filtered, page)
        else:
            response_message = "Hozircha yo'q, like olgan kinolar topilmadi."
            builder = InlineKeyboardBuilder()
            builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))
            await callback_query.message.edit_text(response_message, reply_markup=builder.as_markup())
    else:
        response_message = "Hozircha yo'q, like olgan kinolar topilmadi."
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))
        await callback_query.message.edit_text(response_message, reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data == 'search_sent')
async def search_most_sent(callback_query: types.CallbackQuery, page: int = 1):
    conn = sqlite3.connect('votes.db')
    c = conn.cursor()

    # Eng ko'p yuborilgan kinolarni olish
    c.execute("""
        SELECT movie_id, send_count 
        FROM movie_sends 
        ORDER BY send_count DESC 
        LIMIT ?, ?
    """, ((page - 1) * MOVIES_PER_PAGE, MOVIES_PER_PAGE))
    sent_movies = c.fetchall()

    conn.close()

    # Kino ma'lumotlarini yuklash
    if sent_movies:
        movies = load_movies()
        sent_dict = {movie_id: send_count for movie_id, send_count in sent_movies}

        # Filtrlangan kinolarni olish
        filtered = [
            {**movie, 'send_count': sent_dict.get(movie['id'], 0)} 
            for movie in movies if movie['id'] in sent_dict
        ]

        # Kino ro'yxatini tayyorlash
        response_message = "Eng ko'p yuborilgan kinolar:\n\n"
        for index, movie in enumerate(filtered, start=(page - 1) * MOVIES_PER_PAGE + 1):
            response_message += f"{index}. {movie['nomi']} ({movie['yili']}) - Yuborilgan: {movie['send_count']} marta\n"

        # Inline tugmalarni yaratish
        movie_buttons = [
            InlineKeyboardButton(text=str(index), callback_data=f"movie_{movie['id']}")
            for index, movie in enumerate(filtered, start=(page - 1) * MOVIES_PER_PAGE + 1)
        ]

        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"sent_page_{page - 1}"))
        if len(filtered) == MOVIES_PER_PAGE:
            pagination_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"sent_page_{page + 1}"))
        pagination_buttons.append(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))

        # Inline tugmalarni yangilash
        builder = InlineKeyboardBuilder()
        builder.row(*movie_buttons)
        builder.row(*pagination_buttons)

        await callback_query.message.edit_text(response_message, reply_markup=builder.as_markup())
    else:
        await callback_query.answer("Hech qanday yuborilgan film topilmadi.")


# Janr bo'yicha qidirish
@dp.callback_query(lambda c: c.data == "search_genre")
async def show_genres(callback_query: types.CallbackQuery):
    # builder =InlineKeyboardBuilder()
        # builder.add(InlineKeyboardButton(text=f'\n{genre}', callback_data=f"genre_{genre}"))
    search_methods = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Jangari", callback_data="genre_Jangari")],
            [InlineKeyboardButton(text="🌍 Sarguzasht", callback_data="genre_Sarguzasht")],
            [InlineKeyboardButton(text="📚 Tarixiy", callback_data="genre_Tarixiy")],
            [InlineKeyboardButton(text="🌌 Fantastika", callback_data="genre_Fantastika")],
            [InlineKeyboardButton(text="🕵️‍♂️ Kriminal", callback_data="genre_Kriminal")],
            [InlineKeyboardButton(text="👻 Qo'rqinchli", callback_data="genre_Qorqinchli")],
            [InlineKeyboardButton(text="🎭 Drama", callback_data="genre_Drama")],
            [InlineKeyboardButton(text="🎼 Klasika", callback_data="genre_Klasika")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search")],
        ])
    await callback_query.message.edit_text("Janrni tanlang:", reply_markup=search_methods)

# Janr bo'yicha film ko'rsatish
@dp.callback_query(lambda c: c.data.startswith('genre_'))
async def show_movies_by_genre(callback_query: types.CallbackQuery):
    selected_genre = callback_query.data.split('_')[1]
    movies = load_movies()
    filtered_movies = [movie for movie in movies if selected_genre in movie['janri']]  # Tanlangan janr bo'yicha filtr

    if filtered_movies:
        await display_movies(callback_query.message, filtered_movies)
    else:
        # Agar kino topilmasa, matnni yangilash
        response_message = f"{selected_genre} janri bo'yicha hech qanday film topilmadi."
        
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))

        await callback_query.message.edit_text(response_message, reply_markup=builder.as_markup())
# Xabarni tahrirlashda paginatsiya
async def display_movies(message: types.Message, movies, sahifa: int = 1):
    total_movies = len(movies)
    
    if total_movies == 0:
        await message.answer("Hech qanday kino topilmadi.")
        return

    total_pages = (total_movies + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE
    
    # Ensure sahifa is within valid bounds
    sahifa = max(1, min(sahifa, total_pages))

    start_idx = (sahifa - 1) * MOVIES_PER_PAGE
    end_idx = start_idx + MOVIES_PER_PAGE
    current_movies = movies[start_idx:end_idx]

    movie_list_text = "\n".join(
        [f"{i + 1 + start_idx}. {movie['nomi']} ({movie['yili']}) - {movie['sifati']}" for i, movie in enumerate(current_movies)]
    )
    
    builder = InlineKeyboardBuilder()
    for movie in current_movies:
        builder.add(InlineKeyboardButton(text=movie['nomi'], callback_data=f"movie_{movie['id']}"))

    pagination_buttons = []
    if sahifa > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"sahifa_{sahifa - 1}"))
    if sahifa < total_pages:
        pagination_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"sahifa_{sahifa + 1}"))

    pagination_buttons.append(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))

    builder.row(*pagination_buttons)

    await message.answer(f"Quyidagi kinolar topildi:\n\n{movie_list_text}", reply_markup=builder.as_markup())

# Paginatsiya uchun callback
@dp.callback_query(lambda c: c.data.startswith('sahifa_'))
async def change_page(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split('_')[1])
    # Filtred movies bilan qayta chaqirishingiz mumkin, bu erda load_movies() bilan olingan barcha filmlar yuklanadi
    selected_genre = callback_query.message.reply_markup.inline_keyboard[0][0].callback_data.split('_')[1]
    movies = load_movies()
    filtered_movies = [movie for movie in movies if selected_genre in movie['janri']]
    
    await display_movies(callback_query.message, filtered_movies, page)


    await callback_query.answer()
@dp.callback_query(lambda c: c.data == "back_to_search")
async def handle_back_to_search(callback_query: types.CallbackQuery):
    # Xabarni tahrirlab, qidiruv tizimiga qaytarish
    instructions = "Kino nomini yozing yoki quyidagilardan birini tanlang:"

    search_methods = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Chiqqan yili bo'yicha qidirish", callback_data="search_year")],
        [InlineKeyboardButton(text="🌍 Davlat bo'yicha qidirish", callback_data="search_country")],
        [InlineKeyboardButton(text="🔥 Eng ko'p yuborilganlar", callback_data="search_sent")],
        [InlineKeyboardButton(text="👍 Eng ko'p like olganlar", callback_data="search_liked")],
        [InlineKeyboardButton(text="🎭 Janr bo'yicha qidirish", callback_data="search_genre")],
    ])

    # Xabarni tahrirlash
    await callback_query.message.edit_text(f"{instructions}", reply_markup=search_methods)

@dp.callback_query(lambda c: c.data == "user_count")
async def user_count(callback_query: types.CallbackQuery):
    if callback_query.from_user.id in ADMINS:
        today = datetime.datetime.now().date()
        conn = sqlite3.connect('votes.db')
        c = conn.cursor()
        
        # Bugun start bosgan foydalanuvchilar sonini olish
        c.execute("SELECT COUNT(DISTINCT user_id) FROM votes WHERE DATE(start_time) = ?", (today,))
        user_count = c.fetchone()[0]
        
        # Yuborilgan kinolar sonini olish
        c.execute("SELECT COUNT(*) FROM movie_sends")
        movie_count = c.fetchone()[0]
        
        conn.close()
        
        await callback_query.message.answer(f"Bugun start bosgan foydalanuvchilar: {user_count}\nYuborilgan kinolar soni: {movie_count}")
    else:
        await callback_query.answer("Siz admin emassiz.")

@dp.callback_query(lambda c: c.data == "movie_count")
async def movie_count(callback_query: types.CallbackQuery):
    if callback_query.from_user.id in ADMINS:
        movies = load_movies()  # O'zgarishsiz qolgan
        movie_count = len(movies)
        
        await callback_query.message.answer(f"Jami kinolar soni: {movie_count}")
    else:
        await callback_query.answer("Siz admin emassiz.")

@dp.callback_query(lambda c: c.data == "mandatory_channel")
async def mandatory_channel(callback_query: types.CallbackQuery):
    if callback_query.from_user.id in ADMINS:
        # Majburiy kanal linkini va kanallar ro'yxatini olish
        mandatory_channel_link = "https://t.me/joinchat/XXXXXXX"  # Sizning kanal linkingiz
        mandatory_channels = ["@example_channel1", "@example_channel2"]  # Majburiy kanallar ro'yxati
        
        channels_list = "\n".join(mandatory_channels)
        
        await callback_query.message.answer(
            f"Majburiy kanal: {mandatory_channel_link}\n\n"
            f"Majburiy kanallar:\n{channels_list}"
        )


@dp.message(Command('admin'))
async def admin_contact(message: types.Message):
    await message.answer("Adminga murojaat bot manzili : @tv11uzadminbot")

@dp.message(Command('reklama'))
async def reklama(message: types.Message):
    await message.answer("Kanalda reklamaning hammasi yozilgan: @tv11uzreklama")

@dp.message(Command('help'))
async def help_command(message: types.Message):
    await message.answer("""/start - Botni ishga tushirish\n/buyurtma - Kino buyurtma qilish \n/admin - Adminga murojaat""")

@dp.message(Command('buyurtma'))
async def buyurtma(message: types.Message):
    await message.answer("Video yoki rasmni yuboring")

@dp.message(F.photo or F.video)
async def mmm(message: types.Message):
    photo = message.photo[-1].file_id
    await bot.send_photo(chat_id=7021509411, photo=photo)
    await message.answer("Tez orada javob beriladi")
MOVIES_PER_PAGE = 15
@dp.message(F.text)
async def search_movie(message: types.Message):
    movie_name = message.text
    movies = load_movies()
    filtered_movies = [movie for movie in movies if movie_name.lower() in movie['nomi'].lower()]
    
    if filtered_movies:
        await display_movies(message, filtered_movies)
    else:
        await message.answer(f"{movie_name} bo'yicha hech qanday mos keladigan film topilmadi.")

async def display_movies(message: types.Message, movies, page: int = 1):
    total_movies = len(movies)
    total_pages = (total_movies + MOVIES_PER_PAGE - 1) // MOVIES_PER_PAGE

    # Sahifa uchun kinolarni ajratib olamiz
    start_idx = (page - 1) * MOVIES_PER_PAGE
    end_idx = start_idx + MOVIES_PER_PAGE
    current_movies = movies[start_idx:end_idx]

    # Kino nomlarini ro'yxatda raqamlar bilan chiqaramiz
    movie_list_text = "\n".join(
        [f"{i + 1 + start_idx}. {movie['nomi']} ({movie['yili']}) - {movie['sifati']}" for i, movie in enumerate(current_movies)]
    )
    # Inline tugmalarni yaratamiz
    builder = InlineKeyboardBuilder()
    for i, movie in enumerate(current_movies):
        builder.add(InlineKeyboardButton(text=f"{i + 1 + start_idx}", callback_data=f"movie_{movie['id']}"))

    # Paginatsiya tugmalari
    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"bet_{page - 1}"))
    if page < total_pages:
        pagination_buttons.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"bet_{page + 1}"))
    pagination_buttons.append(InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_search"))
    

    if pagination_buttons:
        builder.row(*pagination_buttons)

    try:
        # Xabarni tahrirlashga urinamiz
        await message.edit_text(f"Quyidagi kinolar topildi:\n\n{movie_list_text}", reply_markup=builder.as_markup())
    except :
        # Agar tahrir qilish muvaffaqiyatsiz bo'lsa, yangi xabar yuboramiz
        await message.answer(f"Quyidagi kinolar topildi:\n\n{movie_list_text}", reply_markup=builder.as_markup())
# Callback query handler for movie selection
@dp.callback_query(lambda c: c.data.startswith('movie_'))
async def handle_callback_query(callback_query: types.CallbackQuery):
    movie_id = callback_query.data.split('_')[1]
    movie = next((m for m in load_movies() if m['id'] == movie_id), None)

    if movie:
        # Ovozlar sonini olish
        like_count = get_vote_count(movie_id, "like")
        dislike_count = get_vote_count(movie_id, "dislike")

        # Film yuborilganligini hisoblash
        increment_movie_send_count(movie_id)
        send_count = get_movie_send_count(movie_id)

        # Ovoz berish tugmalari
        like_btn = InlineKeyboardButton(text=f"👍 Like: {like_count}", callback_data=f"like_{movie_id}")
        dislike_btn = InlineKeyboardButton(text=f"👎 Dislike: {dislike_count}", callback_data=f"dislike_{movie_id}")
        btn = InlineKeyboardMarkup(inline_keyboard=[[like_btn, dislike_btn]])

        # Film haqida to'liq ma'lumot yuborish
        await bot.send_video(
            chat_id=callback_query.from_user.id,
            video=movie['id'],  # Bu yerda 'id' video havolasi bo'lib ishlatiladi
            caption=(
                f"🎬 Nomi: {movie['nomi']}\n"
                f"📅 Yili: {movie['yili']}\n"
                f"🎥 Janri: {movie['janri']}\n"
                f"📽️ Sifati: {movie['sifati']}\n"
                f"🗃 Hajmi: {movie['hajmi']}\n"
                f"🔞 Yosh chegarasi: {movie['yoshi']}\n"
                f"🌍 Davlati: {movie['davlati']}\n"
                f"📤 Yuborilgan: {send_count} marta"
            ),
            reply_markup=btn
        )
        await callback_query.answer(f"{movie['nomi']} Sizga yuborildi.")
    else:
        await callback_query.answer("Film topilmadi.")
@dp.callback_query(lambda c: c.data.startswith('bet_'))
async def handle_pagination(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split('_')[1])
    movies = load_movies()
    # Xabarni tahrirlash orqali yangilash
    await display_movies(callback_query.message, movies, page)
    await callback_query.answer()

@dp.callback_query(lambda c: c.data.startswith('page_'))
async def handle_pagination(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split('_')[1])
    movies = load_movies()
    # Xabarni tahrirlash orqali yangilash
    await display_movies(callback_query.message, movies, page)
    await callback_query.answer()
# Ovoz berish funksiyasi
@dp.callback_query(lambda c: c.data.startswith('like_') or c.data.startswith('dislike_'))
async def handle_vote(callback_query: types.CallbackQuery):
    movie_id = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    vote_type = 'like' if callback_query.data.startswith('like_') else 'dislike'

    conn = sqlite3.connect('votes.db')
    c = conn.cursor()

    # Foydalanuvchi ovoz berishni tekshirish
    c.execute("SELECT * FROM votes WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
    existing_vote = c.fetchone()

    if existing_vote:
        if existing_vote[2] == vote_type:
            c.execute("DELETE FROM votes WHERE user_id = ? AND movie_id = ?", (user_id, movie_id))
            await callback_query.answer(f"Sizning ovozingiz olib tashlandi.")
        else:
            c.execute("UPDATE votes SET vote = ? WHERE user_id = ? AND movie_id = ?", (vote_type, user_id, movie_id))
            await callback_query.answer(f"Ovoz yangilandi: {vote_type}.")
    else:
        c.execute("INSERT INTO votes (user_id, movie_id, vote) VALUES (?, ?, ?)", (user_id, movie_id, vote_type))
        await callback_query.answer(f"Ovoz berildi: {vote_type}.")

    conn.commit()
    conn.close()

    # Yangilangan ovozlar soni
    like_count = get_vote_count(movie_id, "like")
    dislike_count = get_vote_count(movie_id, "dislike")

    # Tugmalarni yangilash
    like_btn = InlineKeyboardButton(text=f"👍 Like: {like_count}", callback_data=f"like_{movie_id}")
    dislike_btn = InlineKeyboardButton(text=f"👎 Dislike: {dislike_count}", callback_data=f"dislike_{movie_id}")
    btn = InlineKeyboardMarkup(inline_keyboard=[[like_btn, dislike_btn]])

    await callback_query.message.edit_reply_markup(reply_markup=btn)

# Ovozlar sonini olish funksiyasi
def get_vote_count(movie_id, vote_type):
    conn = sqlite3.connect('votes.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM votes WHERE movie_id = ? AND vote = ?", (movie_id, vote_type))
    count = c.fetchone()[0]
    conn.close()
    return count

# Botni ishga tushirish
async def main():
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
