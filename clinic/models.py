from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings


# ========== КАСТОМНАЯ МОДЕЛЬ ПОЛЬЗОВАТЕЛЯ ==========
class User(AbstractUser):
    """Кастомная модель пользователя для клиники"""
    
    # Типы входа
    TELEGRAM = 'telegram'
    EMAIL = 'email'
    LOGIN_CHOICES = [
        (TELEGRAM, 'Telegram'),
        (EMAIL, 'Email'),
    ]
    
    # Роли пользователей
    CLIENT = 'client'
    DOCTOR = 'doctor'
    ADMIN = 'admin'
    ROLE_CHOICES = [
        (CLIENT, 'Клиент'),
        (DOCTOR, 'Врач'),
        (ADMIN, 'Администратор'),
    ]
    
    # Поля пользователя
    telegram_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    login_method = models.CharField(max_length=10, choices=LOGIN_CHOICES, default=TELEGRAM)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=CLIENT)
    phone = models.CharField(max_length=20, blank=True, null=True)
    
    # Используем settings.AUTH_USER_MODEL вместо прямого импорта User
    # Для врачей - связь с профилем врача
    doctor_profile = models.OneToOneField(
        'Doctor', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='user_account'
    )
    
    # Исправляем related_name для избежания конфликтов
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='clinic_user_groups',  # Уникальное имя
        related_query_name='clinic_user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='clinic_user_permissions',  # Уникальное имя
        related_query_name='clinic_user',
    )
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# ========== МОДЕЛИ ТЕЛЕГРАМ АВТОРИЗАЦИИ ==========
class TelegramAuthToken(models.Model):
    """Токен для авторизации через Telegram"""
    token = models.CharField(max_length=100, unique=True)
    telegram_id = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=User.ROLE_CHOICES, default=User.CLIENT)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Token {self.token[:8]}... for {self.telegram_id}"


class DoctorAccessCode(models.Model):
    """Коды доступа для врачей"""
    code = models.CharField(max_length=20, unique=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': User.ADMIN}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='used_codes'
    )
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Code {self.code} (expires: {self.expires_at.date()})"


# ========== ОСНОВНЫЕ МОДЕЛИ КЛИНИКИ ==========
class Patient(models.Model):
    """Пациент"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='patient_profile_rel'
    )
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    birth_date = models.DateField(verbose_name='Дата рождения')
    address = models.TextField(verbose_name='Адрес', blank=True)
    telegram_id = models.CharField(max_length=100, blank=True, verbose_name='Telegram ID')

    def send_telegram_reminder(self, appointment):
        """Отправка напоминания о приеме"""
        if not self.telegram_id:
            return False
        
        from .services.telegram_service import telegram_service
        
        message = f"""
🏥 <b>Напоминание о приеме</b>

📅 Дата: {appointment.date_time.strftime('%d.%m.%Y %H:%M')}
👨‍⚕️ Врач: {appointment.doctor.user.get_full_name()}
🩺 Услуга: {appointment.service.name}

Подтвердите вашу запись:
        """
        
        keyboard = telegram_service.create_inline_keyboard([
            telegram_service.create_button('✅ Подтвердить', f'confirm_{appointment.id}'),
            telegram_service.create_button('🔄 Перенести', f'reschedule_{appointment.id}')
        ])
        
        return telegram_service.send_message(self.telegram_id, message, keyboard)
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.phone})"
    
    class Meta:
        verbose_name = 'Пациент'
        verbose_name_plural = 'Пациенты'


class Doctor(models.Model):
    """Врач"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='doctor_profile_rel'
    )
    specialization = models.CharField(max_length=100, verbose_name='Специализация')
    room = models.CharField(max_length=10, verbose_name='Кабинет')
    experience = models.IntegerField(verbose_name='Стаж (лет)', default=0)
    education = models.TextField(verbose_name='Образование', blank=True)
    
    description = models.TextField(verbose_name='О враче', blank=True)
    photo = models.ImageField(
        upload_to='doctors/', 
        verbose_name='Фото',
        blank=True, 
        null=True
    )
    phone = models.CharField(
        max_length=20, 
        verbose_name='Телефон', 
        blank=True
    )
    email = models.EmailField(verbose_name='Email', blank=True)
    rating = models.FloatField(
        verbose_name='Рейтинг', 
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    is_active = models.BooleanField(
        verbose_name='Активен', 
        default=True
    )
    
    def __str__(self):
        return f"Доктор {self.user.get_full_name()} - {self.specialization}"
    
    @property
    def full_name(self):
        return self.user.get_full_name()
    
    @property
    def short_description(self):
        if self.description:
            return self.description[:100] + "..." if len(self.description) > 100 else self.description
        return ""
    
    class Meta:
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'
        ordering = ['-rating', 'specialization']


class Service(models.Model):
    """Услуга"""
    name = models.CharField(max_length=200, verbose_name='Название услуги')
    duration = models.IntegerField(verbose_name='Длительность (мин)', default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'


class Appointment(models.Model):
    """Запись на прием"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтвержден'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    patient = models.ForeignKey(
        Patient, 
        on_delete=models.CASCADE, 
        verbose_name='Пациент'
    )
    doctor = models.ForeignKey(
        Doctor, 
        on_delete=models.CASCADE, 
        verbose_name='Врач'
    )
    service = models.ForeignKey(
        Service, 
        on_delete=models.CASCADE, 
        verbose_name='Услуга'
    )
    date_time = models.DateTimeField(verbose_name='Дата и время приема')
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending', 
        verbose_name='Статус'
    )
    notes = models.TextField(verbose_name='Заметки', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f"Запись {self.patient} к {self.doctor} на {self.date_time}"

    def is_time_available(self):
        """Проверяет, свободно ли время у врача"""
        conflicting_appointments = Appointment.objects.filter(
            doctor=self.doctor,
            date_time=self.date_time,
            status__in=['pending', 'confirmed']
        ).exclude(id=self.id)
        
        return not conflicting_appointments.exists()

    def clean(self):
        """Валидация данных перед сохранением"""
        # Проверяем, что время не в прошлом
        if self.date_time and self.date_time < timezone.now():
            raise ValidationError('Нельзя записаться на прошедшее время')
        
        # Проверяем доступность времени
        if self.doctor and self.date_time and not self.is_time_available():
            raise ValidationError('Врач занят в это время. Выберите другое время.')

    def save(self, *args, **kwargs):
        """Переопределяем save для автоматической валидации"""
        self.clean()  # Вызываем валидацию перед сохранением
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Запись на прием'
        verbose_name_plural = 'Записи на прием'
        ordering = ['-date_time']


class MedicalRecord(models.Model):
    """Медицинская запись"""
    patient = models.ForeignKey(
        Patient, 
        on_delete=models.CASCADE, 
        verbose_name='Пациент'
    )
    doctor = models.ForeignKey(
        Doctor, 
        on_delete=models.CASCADE, 
        verbose_name='Врач'
    )
    appointment = models.ForeignKey(
        Appointment, 
        on_delete=models.CASCADE, 
        verbose_name='Запись'
    )
    diagnosis = models.TextField(verbose_name='Диагноз')
    treatment = models.TextField(verbose_name='Лечение')
    prescription = models.TextField(verbose_name='Назначения', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f"Медкарта: {self.patient} - {self.diagnosis[:50]}..."

    class Meta:
        verbose_name = 'Медицинская запись'
        verbose_name_plural = 'Медицинские записи'