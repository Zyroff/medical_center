class TelegramService:
    """Сервис для работы с Telegram (заглушка)"""
    
    @staticmethod
    def create_inline_keyboard(buttons):
        """Создает inline-клавиатуру"""
        return {"inline_keyboard": buttons}
    
    @staticmethod
    def create_button(text, callback_data):
        """Создает кнопку"""
        return {"text": text, "callback_data": callback_data}
    
    @staticmethod
    def send_message(telegram_id, message, keyboard=None):
        """Отправляет сообщение"""
        # Заглушка - в реальности здесь будет отправка в Telegram
        print(f"Отправка в Telegram ID {telegram_id}: {message[:50]}...")
        return True

# Создаем экземпляр сервиса
telegram_service = TelegramService()