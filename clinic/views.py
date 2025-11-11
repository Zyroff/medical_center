from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .services.telegram_service import telegram_service
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin  # ← исправлено: было loginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy  # ← исправлено: было django.utils
from django.utils import timezone
from .models import Patient, Doctor, Service, Appointment, MedicalRecord
from .forms import AppointmentForm  # ← ДОБАВИТЬ этот импорт
from django.contrib import messages  # ← ДОБАВИТЬ этот импорт
import requests

# Главная страница
def home(request):
    return render(request, 'clinic/home.html')

# Список врачей
class DoctorListView(ListView):
    model = Doctor
    template_name = 'clinic/doctor_list.html'
    context_object_name = 'doctors'

# Список услуг
class ServiceListView(ListView):
    model = Service
    template_name = 'clinic/service_list.html'
    context_object_name = 'services'

# Запись на прием
class AppointmentCreateView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = 'clinic/appointment_create.html'
    success_url = reverse_lazy('appointment_list')
    
    def form_valid(self, form):
        patient = get_object_or_404(Patient, user=self.request.user)
        form.instance.patient = patient
        form.instance.status = 'pending'
        
        response = super().form_valid(form)
        
        # ОТПРАВКА УВЕДОМЛЕНИЯ В TELEGRAM
        if patient.telegram_id:
            patient.send_appointment_notification(self.object)
        
        messages.success(self.request, 'Запись успешно создана! Уведомление отправлено в Telegram.')
        return response
    
    def form_valid(self, form):
        # Автоматически привязываем запись к текущему пациенту
        patient = get_object_or_404(Patient, user=self.request.user)
        form.instance.patient = patient  # ← исправлено: было form_instance
        form.instance.status = 'pending'  # ← исправлено: было form_instance
        messages.success(self.request, 'Запись успешно создана! Ожидайте подтверждения.')
        return super().form_valid(form)

# Список записей пациента
class AppointmentListView(LoginRequiredMixin, ListView):  # ← исправлено: было LoginRequire@Mixin
    model = Appointment
    template_name = 'clinic/appointment_list.html'
    context_object_name = 'appointments'
    
    def get_queryset(self):
        patient = get_object_or_404(Patient, user=self.request.user)
        return Appointment.objects.filter(patient=patient).order_by('-date_time')  # ← ДОБАВИТЬ эту строку

# Личный кабинет пациента
@login_required
def patient_profile(request):
    try:
        patient = Patient.objects.get(user=request.user)
        appointments = Appointment.objects.filter(patient=patient)[:5]  # последние 5 записей
        return render(request, 'clinic/patient_profile.html', {
            'patient': patient,
            'appointments': appointments
        })
    except Patient.DoesNotExist:
        # Если профиля нет, показываем сообщение
        return render(request, 'clinic/patient_profile.html', {
            'patient': None,
            'appointments': []
        })
    
@csrf_exempt
def telegram_webhook(request):
    """Webhook для обработки сообщений от Telegram"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Обработка callback от кнопок
            if 'callback_query' in data:
                callback_data = data['callback_query']
                chat_id = callback_data['from']['id']
                callback_data_text = callback_data['data']
                
                # Обработка действий
                if callback_data_text.startswith('confirm_'):
                    appointment_id = callback_data_text.split('_')[1]
                    return handle_appointment_confirmation(appointment_id, chat_id)
                elif callback_data_text.startswith('reschedule_'):
                    appointment_id = callback_data_text.split('_')[1]
                    return handle_appointment_reschedule(appointment_id, chat_id)
            
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            logger.error(f"Ошибка в webhook: {e}")
            return JsonResponse({'status': 'error'}, status=500)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)

def handle_appointment_confirmation(appointment_id, chat_id):
    """Обработка подтверждения записи"""
    from .models import Appointment
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        appointment.status = 'confirmed'
        appointment.save()
        
        telegram_service.send_message(
            chat_id, 
            "✅ Запись подтверждена! Ждем вас на прием."
        )
        return JsonResponse({'status': 'confirmed'})
    except Appointment.DoesNotExist:
        telegram_service.send_message(chat_id, "❌ Запись не найдена")
        return JsonResponse({'status': 'error'})

def handle_appointment_reschedule(appointment_id, chat_id):
    """Обработка запроса на перенос"""
    telegram_service.send_message(
        chat_id, 
        "🔄 Для переноса записи свяжитесь с администрацией по телефону: +7-XXX-XXX-XX-XX"
    )
    return JsonResponse({'status': 'reschedule_requested'})

from django.http import JsonResponse
from .services.telegram_service import telegram_service

def test_telegram(request):
    """Тестовая функция для проверки Telegram бота"""
    try:
        # Получите ваш реальный Chat ID из предыдущего шага
        # Например: 664727534 или другое число
        test_chat_id = "1431152303"  # ← ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ CHAT ID!
        
        # Отправляем тестовое сообщение
        success = telegram_service.send_message(
            test_chat_id, 
            "✅ Тестовое сообщение от медицинского центра!\n\nЭто проверка работы Telegram бота."
        )
        
        if success:
            return JsonResponse({
                'status': 'success', 
                'message': 'Тестовое сообщение отправлено в Telegram!'
            })
        else:
            return JsonResponse({
                'status': 'error', 
                'message': 'Не удалось отправить сообщение. Проверьте токен бота.'
            })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': f'Ошибка: {str(e)}'
        })