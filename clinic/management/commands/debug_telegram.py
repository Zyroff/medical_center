from django.core.management.base import BaseCommand
from clinic.models import Patient, Appointment
from clinic.services.telegram_service import telegram_service

class Command(BaseCommand):
    help = 'Диагностика работы Telegram бота'

    def handle(self, *args, **options):
        self.stdout.write("🔧 ДИАГНОСТИКА TELEGRAM БОТА")
        self.stdout.write("=" * 50)
        
        # 1. Проверяем токен бота
        self.stdout.write("\n1. ПРОВЕРКА ТОКЕНА БОТА:")
        self.stdout.write(f"Токен: {telegram_service.token}")
        
        # 2. Проверяем пациентов
        self.stdout.write("\n2. ПРОВЕРКА ПАЦИЕНТОВ:")
        patients = Patient.objects.all()
        
        if not patients:
            self.stdout.write("❌ Нет пациентов в базе")
        else:
            for patient in patients:
                self.stdout.write(f"👤 Пациент: {patient.user.get_full_name()}")
                self.stdout.write(f"   Username: {patient.user.username}")
                self.stdout.write(f"   Telegram ID: {patient.telegram_id or 'НЕТ'}")
                self.stdout.write(f"   Записей: {Appointment.objects.filter(patient=patient).count()}")
                self.stdout.write("")
        
        # 3. Тест отправки сообщения
        self.stdout.write("3. ТЕСТ ОТПРАВКИ СООБЩЕНИЯ:")
        
        # Найдите пациента с telegram_id или используйте ваш ID
        patient_with_tg = Patient.objects.filter(telegram_id__isnull=False).first()
        
        if patient_with_tg:
            test_chat_id = patient_with_tg.telegram_id
            self.stdout.write(f"   Отправляем пациенту: {patient_with_tg.user.get_full_name()}")
        else:
            # Используйте ваш Chat ID вручную
            test_chat_id = "ВАШ_CHAT_ID"  # ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ CHAT ID!
            self.stdout.write(f"   Отправляем на Chat ID: {test_chat_id}")
        
        if test_chat_id and test_chat_id != "ВАШ_CHAT_ID":
            success = telegram_service.send_message(
                test_chat_id, 
                "🔧 Тестовое сообщение от команды debug_telegram"
            )
            if success:
                self.stdout.write("✅ Сообщение отправлено успешно!")
            else:
                self.stdout.write("❌ Ошибка отправки сообщения")
        else:
            self.stdout.write("⚠️  Не указан Chat ID для теста")
        
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("Диагностика завершена")