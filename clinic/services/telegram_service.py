import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.token = "8565788967:AAEXokz57WER4zVcH2-3oHF2Lh3ckgULGA0"  # Замените на реальный токен
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, chat_id, text, keyboard=None):
        """Отправка сообщения пользователю"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if keyboard:
            data["reply_markup"] = keyboard
        
        try:
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки Telegram сообщения: {e}")
            return False
    
    def create_inline_keyboard(self, buttons):
        """Создание инлайн-клавиатуры"""
        return {
            "inline_keyboard": buttons
        }
    
    def create_button(self, text, callback_data):
        """Создание кнопки"""
        return [{"text": text, "callback_data": callback_data}]

# Создаем экземпляр сервиса
telegram_service = TelegramService()