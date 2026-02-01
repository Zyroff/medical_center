from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from clinic.models import Patient, Doctor, Service

class Command(BaseCommand):
    help = 'Заполняет базу тестовыми данными'

    def handle(self, *args, **options):
        services = [
            {'name': 'Консультация терапевта', 'duration': 30, 'price': 1500},
            {'name': 'Консультация кардиолога', 'duration': 45, 'price': 2000},
            {'name': 'УЗИ брюшной полости', 'duration': 60, 'price': 2500},
            {'name': 'ЭКГ', 'duration': 30, 'price': 1200},
        ]
        
        for service_data in services:
            Service.objects.get_or_create(**service_data)
        
        doctors_data = [
            {'username': 'therapist', 'first_name': 'Иван', 'last_name': 'Петров', 'specialization': 'Терапевт', 'room': '101', 'experience': 10},
            {'username': 'cardiologist', 'first_name': 'Мария', 'last_name': 'Сидорова', 'specialization': 'Кардиолог', 'room': '102', 'experience': 15},
            {'username': 'surgeon', 'first_name': 'Алексей', 'last_name': 'Козлов', 'specialization': 'Хирург', 'room': '201', 'experience': 8},
        ]
        
        for doc_data in doctors_data:
            user, created = User.objects.get_or_create(
                username=doc_data['username'],
                defaults={'first_name': doc_data['first_name'], 'last_name': doc_data['last_name']}
            )
            if created:
                user.set_password('12345')
                user.save()
            
            Doctor.objects.get_or_create(
                user=user,
                defaults={
                    'specialization': doc_data['specialization'],
                    'room': doc_data['room'],
                    'experience': doc_data['experience']
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Тестовые данные успешно добавлены!'))