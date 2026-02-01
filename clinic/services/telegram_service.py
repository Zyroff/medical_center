import requests
import logging
import secrets
import json
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from clinic.models import User, TelegramAuthToken

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        self.token = "8565788967:AAEC04r37NEfM4v1c12-3oHF2lJb5dgU_CM8"
        self.base_url = f"https://api.telegram.org/bot{self.token}"
    
    def send_message(self, chat_id, text, keyboard=None, parse_mode="HTML"):
        """Отправка сообщения пользователю"""
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
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
        """Создание inline-клавиатуры"""
        return {
            "inline_keyboard": buttons
        }
    
    def create_button(self, text, callback_data):
        """Создание кнопки"""
        return {"text": text, "callback_data": callback_data}
    
    def create_reply_keyboard(self, buttons, resize_keyboard=True):
        """Создание reply-клавиатуры"""
        return {
            "keyboard": buttons,
            "resize_keyboard": resize_keyboard,
            "one_time_keyboard": False
        }
    
    
    def generate_auth_token(self, telegram_id, role="client"):
        """Генерация токена для авторизации"""
        token = secrets.token_urlsafe(32)
        
        TelegramAuthToken.objects.create(
            token=token,
            telegram_id=telegram_id,
            role=role,
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        return token
    
    def send_auth_link(self, chat_id, role="client"):
        """Отправка ссылки для авторизации"""
        token = self.generate_auth_token(chat_id, role)
        
        auth_url = f"{settings.SITE_URL}/telegram-auth?token={token}"
        
        message = (
            f"🔐 <b>Ссылка для входа</b>\n\n"
            f"Нажмите на ссылку ниже, чтобы войти на сайт:\n"
            f"<a href='{auth_url}'>{auth_url}</a>\n\n"
            f"⚠️ Ссылка действительна 15 минут"
        )
        
        return self.send_message(chat_id, message)
    
    def send_role_selection(self, chat_id):
        """Отправка выбора роли пользователю"""
        buttons = [
            [self.create_button("👤 Я клиент", "role_client")],
            [self.create_button("👨‍⚕️ Я врач/сотрудник", "role_staff")]
        ]
        
        keyboard = self.create_inline_keyboard(buttons)
        message = (
            "👋 <b>Добро пожаловать в медицинский центр 'Здоровье'!</b>\n\n"
            "Пожалуйста, выберите вашу роль:"
        )
        
        return self.send_message(chat_id, message, keyboard)
    
    def send_doctor_code_request(self, chat_id):
        """Запрос кода доступа у врача"""
        message = (
            "🔐 <b>Вход для сотрудников</b>\n\n"
            "Пожалуйста, введите код доступа, выданный администратором:"
        )
        
        return self.send_message(chat_id, message)
    
    def verify_doctor_code(self, code):
        """Проверка кода доступа врача"""
        valid_codes = getattr(settings, 'DOCTOR_CODES', [])
        
        try:
            from clinic.models import DoctorAccessCode
            return DoctorAccessCode.objects.filter(
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).exists()
        except:
            return code in valid_codes
    
    def create_main_menu(self, user_role="client"):
        """Создание главного меню в зависимости от роли"""
        if user_role == "doctor":
            buttons = [
                [{"text": "📅 Мое расписание"}],
                [{"text": "👥 Мои пациенты"}],
                [{"text": "🔔 Уведомления"}],
                [{"text": "⚙️ Настройки"}]
            ]
        else:
            buttons = [
                [{"text": "🩺 Записаться на прием"}],
                [{"text": "📋 Мои записи"}],
                [{"text": "👤 Мой профиль"}],
                [{"text": "ℹ️ О клинике"}]
            ]
        
        return self.create_reply_keyboard(buttons)
    
    def send_welcome_back(self, chat_id, username, role):
        """Приветствие для вернувшегося пользователя"""
        role_text = "👨‍⚕️ Врач" if role == "doctor" else "👤 Клиент"
        
        message = (
            f"👋 <b>С возвращением, {username}!</b>\n\n"
            f"Ваша роль: {role_text}\n"
            f"Что вы хотите сделать?"
        )
        
        keyboard = self.create_main_menu(role)
        return self.send_message(chat_id, message, keyboard)

telegram_service = TelegramService()



def handle_telegram_update(update):
    """Обработка входящих сообщений от Telegram"""
    try:
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            if text.startswith('/start'):
                handle_start_command(chat_id, text)
            
            elif is_waiting_for_code(chat_id):
                handle_doctor_code(chat_id, text)
                
        elif 'callback_query' in update:
            callback = update['callback_query']
            chat_id = callback['message']['chat']['id']
            data = callback['data']
            
            if data.startswith('role_'):
                handle_role_selection(chat_id, data)
                
    except Exception as e:
        logger.error(f"Ошибка обработки Telegram update: {e}")

def handle_start_command(chat_id, text):
    """Обработка команды /start"""
    try:
        user = User.objects.get(telegram_id=str(chat_id))
        telegram_service.send_welcome_back(chat_id, user.username, user.role)
        return
    except User.DoesNotExist:
        pass
    
    if len(text.split()) > 1:
        param = text.split()[1]
        if param.startswith('code_'):
            code = param.replace('code_', '')
            if telegram_service.verify_doctor_code(code):
                telegram_service.send_auth_link(chat_id, "doctor")
                return
    
    telegram_service.send_role_selection(chat_id)

def handle_role_selection(chat_id, role_data):
    """Обработка выбора роли"""
    role = role_data.replace('role_', '')
    
    if role == 'client':
        telegram_service.send_auth_link(chat_id, "client")
    elif role == 'staff':
        telegram_service.send_doctor_code_request(chat_id)

def is_waiting_for_code(chat_id):
    """Проверяет, ожидает ли пользователь ввода кода"""
    return False

def handle_doctor_code(chat_id, code):
    """Обработка введенного кода врача"""
    if telegram_service.verify_doctor_code(code):
        telegram_service.send_auth_link(chat_id, "doctor")
    else:
        telegram_service.send_message(
            chat_id, 
            "❌ Неверный код доступа. Попробуйте еще раз или обратитесь к администратору."
        )

def set_webhook(self, webhook_url):
    """Установка вебхука для Telegram бота"""
    url = f"{self.base_url}/setWebhook"
    data = {
        "url": webhook_url
    }
    
    try:
        response = requests.post(url, json=data, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Ошибка установки вебхука: {e}")
        return False