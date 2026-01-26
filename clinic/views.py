from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.utils import timezone
import json
import logging

from .models import Patient, Doctor, Service, Appointment, MedicalRecord, User, TelegramAuthToken
from .forms import AppointmentForm
from .services.telegram_service import telegram_service

logger = logging.getLogger(__name__)


# ========== ОСНОВНЫЕ СТРАНИЦЫ ==========

def home(request):
    """Главная страница"""
    # Если пользователь не авторизован - показываем выбор входа
    if not request.user.is_authenticated:
        return render(request, 'clinic/login_choice.html')
    
    # Если авторизован - показываем соответствующую страницу
    if request.user.role == User.DOCTOR or request.user.role == User.ADMIN:
        return redirect('doctor_dashboard')
    else:
        return redirect('patient_profile')


# ========== АВТОРИЗАЦИЯ ==========

class CustomLoginView(View):
    """Кастомная страница входа для клиентов и работников"""
    
    def get(self, request):
        # Если пользователь уже авторизован - редирект
        if request.user.is_authenticated:
            if request.user.role == User.DOCTOR or request.user.role == User.ADMIN:
                return redirect('doctor_dashboard')
            return redirect('patient_profile')
        
        form = AuthenticationForm()
        return render(request, 'clinic/login.html', {'form': form})
    
    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Добро пожаловать, {user.username}!')
                
                # Редирект в зависимости от роли
                if user.role == User.DOCTOR or user.role == User.ADMIN:
                    return redirect('doctor_dashboard')
                else:
                    return redirect('patient_profile')
            else:
                messages.error(request, 'Неверные данные для входа')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки ниже')
        
        return render(request, 'clinic/login.html', {'form': form})


def custom_logout(request):
    """Выход из системы с полной очисткой сессии"""
    # Очищаем все данные сессии
    request.session.flush()
    
    # Выход из системы
    logout(request)
    
    # Добавляем сообщение
    messages.success(request, 'Вы успешно вышли из системы.')
    
    # Редирект на главную страницу с принудительным обновлением
    response = redirect('home')
    
    # Добавляем заголовки для предотвращения кеширования
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


def telegram_auth(request):
    """Авторизация через Telegram"""
    token = request.GET.get('token')
    
    if not token:
        return redirect('login_failed')
    
    try:
        auth_token = TelegramAuthToken.objects.get(
            token=token,
            is_used=False,
            expires_at__gt=timezone.now()
        )
        
        # Создаем/находим пользователя
        user, created = User.objects.get_or_create(
            telegram_id=auth_token.telegram_id,
            defaults={
                'username': f'tg_{auth_token.telegram_id}',
                'role': auth_token.role,
                'login_method': User.TELEGRAM
            }
        )
        
        # Если пользователь уже есть, но роль изменилась
        if not created and user.role != auth_token.role:
            user.role = auth_token.role
            user.save()
        
        # Логиним пользователя
        login(request, user)
        auth_token.is_used = True
        auth_token.save()
        
        messages.success(request, f'Добро пожаловать, {user.username}!')
        
        # Редирект по роли
        if user.role == User.DOCTOR or user.role == User.ADMIN:
            return redirect('doctor_dashboard')
        return redirect('patient_profile')
        
    except TelegramAuthToken.DoesNotExist:
        return redirect('login_failed')


def login_failed(request):
    """Страница неудачного входа"""
    return render(request, 'clinic/login_failed.html', {
        'error': 'Недействительная или просроченная ссылка для входа. Попробуйте снова.'
    })


def access_denied(request):
    """Страница "Доступ запрещен" """
    return render(request, 'clinic/access_denied.html')


# ========== ВРАЧИ И УСЛУГИ ==========

class DoctorListView(ListView):
    """Список всех врачей"""
    model = Doctor
    template_name = 'clinic/doctor_list.html'
    context_object_name = 'doctors'
    queryset = Doctor.objects.filter(is_active=True).order_by('specialization')


class DoctorDetailView(DetailView):
    """Детальная информация о враче"""
    model = Doctor
    template_name = 'clinic/doctor_detail.html'
    context_object_name = 'doctor'


class ServiceListView(ListView):
    """Список всех услуг"""
    model = Service
    template_name = 'clinic/service_list.html'
    context_object_name = 'services'
    queryset = Service.objects.all().order_by('name')


# ========== ЗАПИСИ НА ПРИЕМ ==========

class AppointmentCreateView(LoginRequiredMixin, CreateView):
    """Создание новой записи на прием"""
    model = Appointment
    form_class = AppointmentForm
    template_name = 'clinic/appointment_create.html'
    success_url = reverse_lazy('appointment_list')
    
    def get_form_kwargs(self):
        """Передаем пользователя в форму"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Автоматически привязываем запись к текущему пациенту
        try:
            patient = Patient.objects.get(user=self.request.user)
            form.instance.patient = patient
            form.instance.status = 'pending'
            
            # Проверяем доступность времени
            if not form.instance.is_time_available():
                messages.error(self.request, 'Врач занят в это время. Выберите другое время.')
                return self.form_invalid(form)
            
            response = super().form_valid(form)
            
            # Отправляем уведомление в Telegram
            if patient.telegram_id:
                patient.send_telegram_reminder(form.instance)
            
            messages.success(self.request, 'Запись успешно создана! Уведомление отправлено в Telegram.')
            return response
            
        except Patient.DoesNotExist:
            messages.error(self.request, 'Профиль пациента не найден.')
            return redirect('patient_profile')


class AppointmentListView(LoginRequiredMixin, ListView):
    """Список записей текущего пациента"""
    model = Appointment
    template_name = 'clinic/appointment_list.html'
    context_object_name = 'appointments'
    
    def get_queryset(self):
        try:
            patient = Patient.objects.get(user=self.request.user)
            return Appointment.objects.filter(
                patient=patient
            ).order_by('-date_time')
        except Patient.DoesNotExist:
            return Appointment.objects.none()


# ========== ЛИЧНЫЕ КАБИНЕТЫ ==========

@login_required
def patient_profile(request):
    """Профиль пациента - ТОЛЬКО для пациентов"""
    # Проверяем, что пользователь действительно пациент
    if request.user.role != User.CLIENT:
        messages.warning(request, 'Эта страница только для пациентов')
        
        # Редирект в зависимости от роли
        if request.user.is_superuser:
            return redirect('/admin/')  # Админа в админку
        elif request.user.role == User.DOCTOR:
            return redirect('doctor_dashboard')  # Врача в его панель
        else:
            return redirect('home')  # Остальных на главную
    
    try:
        patient = Patient.objects.get(user=request.user)
        appointments = Appointment.objects.filter(
            patient=patient
        ).order_by('-date_time')[:5]
        
        return render(request, 'clinic/patient_profile.html', {
            'patient': patient,
            'appointments': appointments,
            'user': request.user
        })
        
    except Patient.DoesNotExist:
        # Создаем профиль пациента если его нет
        patient = Patient.objects.create(
            user=request.user,
            phone=request.user.phone or '',
            birth_date=timezone.now().date(),
            address=''
        )
        return redirect('patient_profile')

@login_required
def doctor_dashboard(request):
    """Панель управления врача"""
    if request.user.role not in [User.DOCTOR, User.ADMIN]:
        return redirect('access_denied')
    
    try:
        doctor = Doctor.objects.get(user=request.user)
        
        # Статистика для врача
        today = timezone.now().date()
        appointments_today = Appointment.objects.filter(
            doctor=doctor,
            date_time__date=today,
            status__in=['confirmed', 'pending']
        ).count()
        
        total_appointments = Appointment.objects.filter(doctor=doctor).count()
        recent_appointments = Appointment.objects.filter(
            doctor=doctor
        ).order_by('-date_time')[:5]
        
        return render(request, 'clinic/doctor_dashboard.html', {
            'doctor': doctor,
            'user': request.user,
            'appointments_today': appointments_today,
            'total_appointments': total_appointments,
            'recent_appointments': recent_appointments
        })
        
    except Doctor.DoesNotExist:
        # Если врач не найден, но у пользователя роль врача
        if request.user.role == User.DOCTOR:
            doctor = Doctor.objects.create(
                user=request.user,
                specialization='Терапевт',
                room='101',
                experience=0
            )
            messages.info(request, 'Создан новый профиль врача.')
            return redirect('doctor_dashboard')
        
        return redirect('access_denied')


# ========== TELEGRAM WEBHOOK ==========

@csrf_exempt
def telegram_webhook(request):
    """Webhook для обработки сообщений от Telegram"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Telegram webhook data: {data}")
            
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
            
            # Обработка текстовых сообщений
            elif 'message' in data:
                message = data['message']
                chat_id = message['chat']['id']
                text = message.get('text', '')
                
                # Обработка команды /start
                if text.startswith('/start'):
                    return handle_telegram_start_command(chat_id, text)
            
            return JsonResponse({'status': 'ok'})
            
        except Exception as e:
            logger.error(f"Ошибка в webhook: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)


def handle_telegram_start_command(chat_id, text):
    """Обработка команды /start в Telegram"""
    try:
        # Проверяем, есть ли пользователь в БД
        try:
            user = User.objects.get(telegram_id=str(chat_id))
            
            # Если пользователь уже есть
            telegram_service.send_message(
                chat_id,
                f"👋 С возвращением, {user.username}!\n"
                f"Ваша роль: {user.get_role_display()}\n\n"
                f"Для входа на сайт перейдите в личный кабинет."
            )
            return JsonResponse({'status': 'welcome_back'})
            
        except User.DoesNotExist:
            # Новый пользователь - отправляем выбор роли
            buttons = [
                [{"text": "👤 Я пациент", "callback_data": "role_client"}],
                [{"text": "👨‍⚕️ Я врач/сотрудник", "callback_data": "role_staff"}]
            ]
            
            keyboard = telegram_service.create_inline_keyboard(buttons)
            
            telegram_service.send_message(
                chat_id,
                "👋 Добро пожаловать в медицинский центр 'Здоровье'!\n\n"
                "Пожалуйста, выберите вашу роль:",
                keyboard
            )
            return JsonResponse({'status': 'role_selection_sent'})
            
    except Exception as e:
        logger.error(f"Ошибка обработки /start: {e}")
        telegram_service.send_message(
            chat_id,
            "❌ Произошла ошибка. Пожалуйста, обратитесь в поддержку."
        )
        return JsonResponse({'status': 'error'})


def handle_appointment_confirmation(appointment_id, chat_id):
    """Обработка подтверждения записи через Telegram"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Проверяем, что пациент подтверждает свою запись
        if str(appointment.patient.telegram_id) != str(chat_id):
            telegram_service.send_message(
                chat_id, 
                "❌ Вы не можете подтвердить эту запись."
            )
            return JsonResponse({'status': 'unauthorized'})
        
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
    """Обработка запроса на перенос записи"""
    telegram_service.send_message(
        chat_id, 
        "🔄 Для переноса записи свяжитесь с администрацией по телефону: +7-XXX-XXX-XX-XX\n\n"
        "Или отмените текущую запись и создайте новую в личном кабинете."
    )
    return JsonResponse({'status': 'reschedule_requested'})


# ========== ТЕСТОВЫЕ ФУНКЦИИ ==========

def test_telegram(request):
    """Тестовая функция для проверки Telegram бота"""
    try:
        # Получите ваш реальный Chat ID
        test_chat_id = "1431152303"  # ← ЗАМЕНИТЕ НА ВАШ РЕАЛЬНЫЙ CHAT ID!
        
        # Отправляем тестовое сообщение
        success = telegram_service.send_message(
            test_chat_id, 
            "✅ Тестовое сообщение от медицинского центра!\n\n"
            "Это проверка работы Telegram бота."
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


def set_telegram_webhook(request):
    """Установка вебхука для Telegram бота"""
    try:
        # URL вашего вебхука
        webhook_url = "https://ваш-домен.ру/telegram-webhook/"
        
        # Устанавливаем вебхук
        telegram_service.set_webhook(webhook_url)
        
        return JsonResponse({
            'status': 'success',
            'message': f'Вебхук установлен: {webhook_url}'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Ошибка: {str(e)}'
        })


# ========== ДОПОЛНИТЕЛЬНЫЕ СТРАНИЦЫ ==========

def about(request):
    """Страница "О клинике" """
    return render(request, 'clinic/about.html')


def contacts(request):
    """Страница "Контакты" """
    return render(request, 'clinic/contacts.html')


def privacy_policy(request):
    """Политика конфиденциальности"""
    return render(request, 'clinic/privacy_policy.html')