from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin  # ← исправлено: было loginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy  # ← исправлено: было django.utils
from django.utils import timezone
from .models import Patient, Doctor, Service, Appointment, MedicalRecord
from .forms import AppointmentForm  # ← ДОБАВИТЬ этот импорт
from django.contrib import messages  # ← ДОБАВИТЬ этот импорт

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
class AppointmentCreateView(LoginRequiredMixin, CreateView):  # ← исправлено: было LoginRequire@Mixin
    model = Appointment
    form_class = AppointmentForm  # ← используем нашу форму
    template_name = 'clinic/appointment_create.html'  # ← исправлено: было appointment.create.html
    success_url = reverse_lazy('appointment_list')
    
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
    patient = get_object_or_404(Patient, user=request.user)
    appointments = Appointment.objects.filter(patient=patient)[:5]
    return render(request, 'clinic/patient_profile.html', {
        'patient': patient,
        'appointments': appointments
    })