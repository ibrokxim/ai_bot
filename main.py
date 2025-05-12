import hashlib
import logging
import os
import uuid

from aiogram import F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.exceptions import TelegramAPIError
from dotenv import load_dotenv


from database_bot import BotDatabase # Faraz qilamizki, bu fayl mavjud va to'g'ri ishlaydi

log_directory = "logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
log_file_path = os.path.join(log_directory, "bot.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_file_path,
    filemode='a'
)
logger = logging.getLogger(__name__)

load_dotenv()

# Bot va dispetcherni ishga tushirish
TOKEN = os.getenv('BOT_TOKEN')
MINI_APP_URL = os.getenv('MINI_APP_URL')
REFERRAL_BONUS_REQUESTS = int(os.getenv('REFERRAL_BONUS_REQUESTS', 3)) # Taklif uchun bonus so'rovlar soni

# Token mavjudligini tekshirish
if not TOKEN:
    logger.critical("Muhit o'zgaruvchilarida BOT_TOKEN topilmadi!")
    exit("Xatolik: BOT_TOKEN o'rnatilmagan.")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Ma'lumotlar bazasini ishga tushirish
try:
    db = BotDatabase(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )
    # Ishga tushirishda ulanishni tekshiramiz
    if not db.conn or not db.conn.open:
        if not db.connect():
            logger.critical("Ishga tushirishda ma'lumotlar bazasiga ulanib bo'lmadi.")
            exit("Jiddiy xatolik: MBga ulanib bo'lmadi.")
except Exception as e:
    logger.critical(f"Ma'lumotlar bazasini ishga tushirishda jiddiy xatolik: {e}")
    exit("Jiddiy xatolik: MBni ishga tushirib bo'lmadi.")


class UserState(StatesGroup):
    waiting_for_contact = State() # Kontaktni kutish holati


@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    """/start buyrug'i uchun ishlovchi"""
    user = message.from_user
    referrer_info = None # Taklif qilgan haqida ma'lumot
    referral_code_used = None # Ishlatilgan referal kod

    logger.info(f"/start buyrug'i {user.id} ({user.username}) foydalanuvchisidan qabul qilindi")

    # 1. Foydalanuvchini saqlashdan OLDIN uning mavjudligini tekshiramiz
    try:
        user_data_before_save = db.get_user(user.id)
        user_exists = user_data_before_save is not None
    except Exception as e:
        logger.error(f"{user.id} foydalanuvchisining mavjudligini tekshirishda xatolik: {e}")
        await message.answer("Sizning so'rovingizni qayta ishlashda xatolik yuz berdi. Keyinroq urinib ko'ring.")
        return

    logger.info(f"{user.id} foydalanuvchisi {'mavjud' if user_exists else 'yangi'}")

    # 2. Agar foydalanuvchi YANGI bo'lsa, referal kodni tekshiramiz
    if not user_exists:
        args = message.text.split()
        if len(args) > 1:
            potential_referral_code = args[1]
            logger.info(f"{user.id} foydalanuvchisi argument bilan keldi (potentsial referal kod): {potential_referral_code}")
            try:
                # Kod bo'yicha refererni topishga harakat qilamiz
                referrer_info = db.get_referral(potential_referral_code)

                if referrer_info:
                    # Foydalanuvchi o'zini o'zi taklif qilmaganligini tekshiramiz
                    if referrer_info['referrer_telegram_id'] == user.id:
                        logger.warning(f"{user.id} foydalanuvchisi o'zining referal kodini ishlatishga urindi.")
                        referrer_info = None # Ma'lumotni qayta tiklaymiz, o'z-o'ziga referal hisobga olinmaydi
                    else:
                        logger.info(f"{potential_referral_code} kodi bo'yicha yangi {user.id} foydalanuvchisi uchun {referrer_info['referrer_telegram_id']} refereri topildi")
                        referral_code_used = potential_referral_code
                else:
                    logger.info(f"Referal kod '{potential_referral_code}' topilmadi yoki faol emas.")
            except Exception as e:
                logger.error(f"{user.id} foydalanuvchisi uchun '{potential_referral_code}' referal kodini qidirishda xatolik: {e}")
                # Referalsiz davom etamiz, lekin xatolikni qayd etamiz

    # 3. Foydalanuvchini saqlaymiz yoki yangilaymiz (endi uning yangi yoki yo'qligini aniq bilamiz)
    try:
        save_success = db.save_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            chat_id=message.chat.id, # Bildirishnomalar uchun chat_id ni saqlaymiz
            is_bot=user.is_bot,
            language_code=user.language_code
        )
        if not save_success:
            logger.error(f"{user.id} foydalanuvchisini saqlash/yangilash muvaffaqiyatsiz tugadi")
            await message.answer("Ro'yxatdan o'tishda xatolik yuz berdi. Keyinroq urinib ko'ring.")
            return

        # Saqlash/yangilashdan SO'NG foydalanuvchining dolzarb ma'lumotlarini olamiz
        user_data = db.get_user(user.id)
        if not user_data:
            logger.error(f"Saqlashdan keyin {user.id} foydalanuvchisining ma'lumotlarini olib bo'lmadi!")
            await message.answer("Ma'lumotlarni olishda xatolik yuz berdi. Keyinroq urinib ko'ring.")
            return
    except Exception as e:
        logger.error(f"{user.id} foydalanuvchisini saqlash yoki olishda jiddiy xatolik: {e}")
        await message.answer("Jiddiy xatolik yuz berdi. Iltimos, qo'llab-quvvatlash xizmatiga murojaat qiling.")
        return

    # 4. Agar MUVOFIQIYATLI referal o'tish bo'lsa (yangi foydalanuvchi + boshqa foydalanuvchining haqiqiy kodi)
    if referrer_info and referral_code_used and not user_exists:
        referrer_telegram_id = referrer_info['referrer_telegram_id']
        referrer_user_id = referrer_info['referrer_user_id'] # users jadvalidagi referer IDsi
        referral_code_id = referrer_info['referral_code_id'] # referral_codes jadvalidagi kod IDsi
        new_user_db_id = user_data['user_id'] # users jadvalidagi yangi foydalanuvchi IDsi

        try:
            # Refererga bonuslar hisoblaymiz
            if db.add_requests(referrer_telegram_id, REFERRAL_BONUS_REQUESTS):
                logger.info(f"{referrer_telegram_id} refereriga {REFERRAL_BONUS_REQUESTS} so'rov hisoblandi")

                # Tarixga yozamiz
                record_success = db.record_referral(
                    referrer_id=referrer_user_id,
                    referred_id=new_user_db_id,
                    referral_code_id=referral_code_id,
                    referral_code=referral_code_used,
                    bonus_requests_added=REFERRAL_BONUS_REQUESTS
                )
                if not record_success:
                    logger.error(f"Referal o'tishni tarixga yozib bo'lmadi: {referrer_user_id} -> {new_user_db_id}")

                # Refererga bildirishnoma yuboramiz
                referrer_chat_id = db.get_user_chat_id(referrer_telegram_id)
                if referrer_chat_id:
                    try:
                        await bot.send_message(
                            referrer_chat_id,
                            f"🎉 Sizning referal havolangiz orqali yangi foydalanuvchi "
                            f"{user.first_name or user.username or f'ID:{user.id}'} qo'shildi!\n"
                            f"Sizga +{REFERRAL_BONUS_REQUESTS} bonus so'rovlari hisoblandi."
                        )
                        logger.info(f"{referrer_telegram_id} refereriga bildirishnoma yuborildi")
                    except TelegramAPIError as e:
                        # Ko'p uchraydigan xatolik - foydalanuvchi botni bloklagan
                        if "bot was blocked by the user" in str(e).lower(): # .lower() qo'shildi, universal bo'lishi uchun
                            logger.warning(f"{referrer_telegram_id} refereriga bildirishnoma yuborib bo'lmadi: bot bloklangan.")
                        else:
                            logger.error(f"{referrer_telegram_id} (chat_id: {referrer_chat_id}) refereriga bildirishnoma yuborib bo'lmadi: {e}")
                else:
                    logger.warning(f"{referrer_telegram_id} refereri uchun chat_id topilmadi, bildirishnoma yuborilmadi.")
            else:
                logger.error(f"{referrer_telegram_id} refereriga bonuslarni hisoblab bo'lmadi")
        except Exception as e:
            logger.error(f"{referrer_telegram_id} refereri uchun referal hisoblash/bildirishnoma bilan ishlashda xatolik: {e}")


    # 5. Agar mavjud bo'lmasa, foydalanuvchi (yangi yoki eski) uchun referal kod yaratamiz
    user_ref_code = None
    try:
        user_ref_code = db.get_user_referral_code(user.id)
        if not user_ref_code:
            logger.info(f"{user.id} foydalanuvchisida referal kod yo'q, yangisini yaratamiz.")
            ref_base = f"{user.id}_{uuid.uuid4()}"
            ref_code_new = hashlib.md5(ref_base.encode()).hexdigest()[:8] # Kod uzunligi 8 belgi
            if db.create_referral(user.id, ref_code_new):
                user_ref_code = ref_code_new
                logger.info(f"{user.id} foydalanuvchisi uchun '{user_ref_code}' referal kodi yaratildi va saqlandi")
            else:
                logger.error(f"{user.id} foydalanuvchisi uchun referal kod yaratib bo'lmadi")
        else:
            logger.info(f"{user.id} foydalanuvchisida allaqachon referal kod bor: {user_ref_code}")
    except Exception as e:
        logger.error(f"{user.id} uchun referal kodni olish/yaratishda xatolik: {e}")

    ref_link = ""
    if user_ref_code:
        try:
            # Bot nomini dinamik ravishda olamiz
            bot_info = await bot.get_me()
            ref_link = f"https://t.me/{bot_info.username}?start={user_ref_code}"
        except Exception as e:
            logger.error(f"Referal havola uchun bot nomini olib bo'lmadi: {e}")
            # Agar ma'lum bo'lsa, statik nomga qaytish yoki bo'sh satr
            # ref_link = f"https://t.me/Sizning_BOT_USERNAME?start={user_ref_code}"

    # 6. Kontakt so'rash kerakligini aniqlaymiz
    # Saqlash/yangilashdan SO'NG olingan user_data dan foydalanamiz
    has_contact = 'contact' in user_data and user_data['contact'] is not None and user_data['contact'] != ''
    logger.info(f"{user.id} foydalanuvchisida saqlangan kontakt {'mavjud' if has_contact else 'mavjud emas'}.")

    # 7. Kontakt mavjudligiga qarab xabar ko'rsatamiz
    user_display_name = user_data.get('first_name') or user.username or f"Foydalanuvchi {user.id}"
    requests_left = user_data.get('requests_left', 0)

    if has_contact:
        # Foydalanuvchi allaqachon ro'yxatdan o'tgan va kontaktini ulashgan
        balance_text = (
            f"👋 Assalomu alaykum, {user_display_name}!\n\n"
            f"🎉 Sizning balansingiz: {requests_left} so'rov.\n\n"
        )
        if ref_link:
            balance_text += (
                f"Do'stlaringizni taklif qiling va har biri uchun +{REFERRAL_BONUS_REQUESTS} so'rov oling!\n"
                f"Takliflar uchun sizning referal havolangiz:\n`{ref_link}`" # Nusxalash uchun Markdown
            )
        else:
            balance_text += "Sizning referal havolangizni yaratib bo'lmadi. Keyinroq urinib ko'ring."

        inline_keyboard = []
        if MINI_APP_URL:
            inline_keyboard.append([
                InlineKeyboardButton(
                    text="🌐 Mini-ilovochani ochish",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ])

        inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard) if inline_keyboard else None
        try:
            await message.answer(balance_text, reply_markup=inline_markup, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"{user.id} foydalanuvchisiga 'balans' xabarini yuborishda xatolik: {e}")

    else:
        # Yangi foydalanuvchi YOKI eski, lekin kontaktsiz
        welcome_text = (
            f"👋 Assalomu alaykum, {user_display_name}!\n\n"
            "Botimizga xush kelibsiz!\n"
            f"Boshlang'ich balans: {requests_left} so'rov.\n"
        )
        if ref_link:
            welcome_text += (
                f"\nDo'stlaringizni taklif qiling va har biri uchun +{REFERRAL_BONUS_REQUESTS} so'rov oling!\n"
                f"🔗 Sizning referal havolangiz:\n`{ref_link}`\n" # Nusxalash uchun Markdown
            )

        welcome_text += (
            "\n\n📱 Botdan to'liq foydalanish uchun, iltimos, telefon raqamingizni ulashing.\n"
            "Quyidagi tugmani bosing 👇\n\n"
            "🔒 Sizning raqamingiz faqat identifikatsiya uchun ishlatiladi va uchinchi shaxslarga berilmaydi."
        )

        inline_keyboard = []
        if MINI_APP_URL:
            inline_keyboard.append([
                InlineKeyboardButton(
                    text="🌐 Mini-ilovochani ochish",
                    web_app=WebAppInfo(url=MINI_APP_URL)
                )
            ])
        inline_markup = InlineKeyboardMarkup(inline_keyboard=inline_keyboard) if inline_keyboard else None

        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Kontakt bilan bo'lishish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True # Tugma bosilgandan keyin yo'qoladi
        )

        try:
            # Avval matn va inline tugmalar (agar mavjud bo'lsa)
            await message.answer(welcome_text, reply_markup=inline_markup, parse_mode="Markdown")
            # Keyin kontakt so'rovi bilan reply-tugma
            await message.answer("Iltimos, kontaktingizni ulashish uchun quyidagi tugmani bosing:", reply_markup=contact_keyboard)

            # Kontaktni kutish holatini o'rnatamiz
            await state.set_state(UserState.waiting_for_contact)
            logger.info(f"{user.id} foydalanuvchisi uchun 'waiting_for_contact' holati o'rnatildi")

        except Exception as e:
            logger.error(f"{user.id} foydalanuvchisiga salomlashuv xabari / kontakt so'rovini yuborishda xatolik: {e}")


# Nusxalash havolasi uchun callback ishlovchisi endi kerak emas,
# chunki havola matnda va Markdown yordamida oson nusxalanadi.

@dp.message(F.content_type == types.ContentType.CONTACT, UserState.waiting_for_contact)
async def process_contact(message: Message, state: FSMContext):
    """Kontaktni qabul qilishni qayta ishlash"""
    user = message.from_user
    logger.info(f"{user.id} foydalanuvchisidan kontakt qabul qilindi")

    # Kontakt xabar yuboruvchisiga tegishli ekanligini tekshiramiz
    if message.contact is not None and message.contact.user_id == user.id:
        contact_phone = message.contact.phone_number
        logger.info(f"{user.id} foydalanuvchisidan {contact_phone} kontakti qabul qilindi (ID mos keladi)")
        try:
            # Kontaktni ma'lumotlar bazasiga saqlaymiz
            if db.save_contact(user.id, contact_phone):
                logger.info(f"{user.id} foydalanuvchisi uchun {contact_phone} kontakti muvaffaqiyatli saqlandi")

                # Foydalanuvchi haqida yangilangan ma'lumotni olamiz
                user_data = db.get_user(user.id)
                requests_left = user_data.get('requests_left', 0) if user_data else 0
                ref_code = db.get_user_referral_code(user.id)

                ref_link = ""
                if ref_code:
                    try:
                        bot_info = await bot.get_me()
                        ref_link = f"https://t.me/{bot_info.username}?start={ref_code}"
                    except Exception as e:
                        logger.error(f"process_contact da referal havola uchun bot nomini olib bo'lmadi: {e}")

                complete_text = (
                    f"✅ Rahmat! Sizning kontangiz ({contact_phone}) muvaffaqiyatli saqlandi.\n\n"
                    f"🎉 Sizda {requests_left} ta mavjud so'rov bor.\n\n"
                )
                if ref_link:
                    complete_text += f"Sizning referal havolangiz:\n`{ref_link}`" # Markdown

                # Xabarni yuboramiz va kontakt so'rovi klaviaturasini olib tashlaymiz
                await message.answer(complete_text, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

                # Holatni tiklaymiz
                await state.clear()
                logger.info(f"Kontakt saqlangandan so'ng {user.id} foydalanuvchisi uchun holat tiklandi.")

            else:
                logger.error(f"{user.id} foydalanuvchisi uchun {contact_phone} kontaktini MB ga saqlashda xatolik.")
                await message.answer(
                    "❌ Sizning kontaktingizni saqlashda xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring yoki qo'llab-quvvatlash xizmatiga murojaat qiling.",
                    reply_markup=ReplyKeyboardRemove() # MB xatoligi yuz berganda tugmani olib tashlaymiz
                )
                await state.clear() # Xatolik yuz berganda holatni tiklaymiz

        except Exception as e:
            logger.error(f"{user.id} dan kontaktni qayta ishlashda jiddiy xatolik: {e}")
            await message.answer("Ichki xatolik yuz berdi. Keyinroq urinib ko'ring.", reply_markup=ReplyKeyboardRemove())
            await state.clear()

    else:
        # Kontakt emas yoki begona kontakt yuborilgan holat
        logger.warning(f"{user.id} foydalanuvchisi noto'g'ri kontakt yubordi yoki tugma orqali emas.")
        contact_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Kontakt bilan bo'lishish", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        await message.answer(
            "❌ Iltimos, aynan o'z telefon raqamingizni yuborish uchun quyidagi '📱 Kontakt bilan bo'lishish' tugmasini bosing.",
            reply_markup=contact_keyboard # Tugmani yana bir bor ko'rsatamiz
        )
        # Holatni tiklamaymiz, to'g'ri kontaktni kutamiz


@dp.message(UserState.waiting_for_contact)
async def process_invalid_input_while_waiting_contact(message: Message):
    """Kontaktni kutish holatida boshqa har qanday xabarlarni (kontaktlardan tashqari) qayta ishlash"""
    logger.warning(f"{message.from_user.id} foydalanuvchisi waiting_for_contact holatida '{message.text}' kontaktini emas, boshqa narsa yubordi.")
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Kontakt bilan bo'lishish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "⚠️ Iltimos, matn yoki boshqa fayllarni yubormang. Davom etish uchun '📱 Kontakt bilan bo'lishish' tugmasini bosing.",
        reply_markup=contact_keyboard
    )


async def main():
    """Botni ishga tushirishning asosiy funksiyasi"""
    # So'rovni ishga tushirishdan oldin MB bilan ulanishni tekshirish
    if not db.conn or not db.conn.open:
        logger.warning("Ishga tushirishdan oldin MB bilan ulanish yo'q. Qayta ulanishga urinish...")
        if not db.connect():
            logger.critical("MB bilan ulanishni tiklab bo'lmadi. Botni ishga tushirish bekor qilindi.")
            return # MB siz botni ishga tushirmaymiz

    logger.info("Botni ishga tushirish (polling)...")
    # Long pollingni ishga tushirish
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Bot ishlashi paytida jiddiy xatolik: {e}", exc_info=True)
    finally:
        # Bot sessiyasini va MB bilan ulanishni to'g'ri yopish
        await bot.session.close()
        db.close()
        logger.info("Bot to'xtatildi, resurslar bo'shatildi.")


if __name__ == '__main__':
    import asyncio
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt signali qabul qilindi. Ishni yakunlash...")
    except Exception as main_error:
        logger.critical(f"main tsiklida tutilmagan xatolik: {main_error}", exc_info=True)