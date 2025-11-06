from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    birth_date = models.DateField(verbose_name='Дата рождения')
    address = models.TextField(verbose_name='Адрес', blank=True)
    telegram_id = models.CharField(max_length=100, blank=True, verbose_name='Telegram ID')
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.phone})"
    
    class Meta:
        verbose_name = 'Пациент'
        verbose_name_plural = 'Пациенты'

class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=100, verbose_name='Специализация')
    room = models.CharField(max_length=10, verbose_name='Кабинет')
    experience = models.IntegerField(verbose_name='Стаж (лет)', default=0)
    education = models.TextField(verbose_name='Образование', blank=True)
    
    def __str__(self):
        return f"Доктор {self.user.get_full_name()} - {self.specialization}"
    
    class Meta:
        verbose_name = 'Врач'
        verbose_name_plural = 'Врачи'

class Service(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название услуги')
    duration = models.IntegerField(verbose_name='Длительность (мин)', default=30)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Услуга'
        verbose_name_plural = 'Услуги'

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтвержден'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name='Пациент')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Врач')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, verbose_name='Услуга')
    date_time = models.DateTimeField(verbose_name='Дата и время приема')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
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
        verbose_name_plural = 'Записи на прием'  # ← исправлено: было 'piural'
        ordering = ['-date_time']

class MedicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name='Пациент')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Врач')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, verbose_name='Запись')
    diagnosis = models.TextField(verbose_name='Диагноз')
    treatment = models.TextField(verbose_name='Лечение')
    prescription = models.TextField(verbose_name='Назначения', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    def __str__(self):
        return f"Медкарта: {self.patient} - {self.diagnosis[:50]}..."

    class Meta:
        verbose_name = 'Медицинская запись'
        verbose_name_plural = 'Медицинские записи'  # ← исправлено: было 'piural'