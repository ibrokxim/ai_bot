from telegram import Update
from telegram.ext import ContextTypes
from app.database.db import save_user_data
from app.config import MINI_APP_URL

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.message.from_user
    
    # Сохраняем данные пользователя
    save_user_data(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        is_bot=user.is_bot,
        language_code=user.language_code
    )
    
    welcome_text = (
        f"👋 Здравствуйте, {user.first_name}!\n\n"
        f"🔗 Вот ссылка на наше мини-приложение:\n{MINI_APP_URL}"
    )
    
    await update.message.reply_text(welcome_text) 