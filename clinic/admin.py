from django.contrib import admin
from .models import Patient, Doctor, Service, Appointment, MedicalRecord

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'birth_date']
    search_fields = ['user__first_name', 'user__last_name', 'phone']

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'room', 'experience']
    list_filter = ['specialization']
    search_fields = ['user__first_name', 'user__last_name']

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'duration', 'price']
    search_fields = ['name']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'service', 'date_time', 'status']
    list_filter = ['status', 'date_time', 'doctor__specialization']
    date_hierarchy = 'date_time'
    search_fields = ['patient__user__first_name', 'patient__user__last_name']

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'created_at']
    list_filter = ['created_at']
    search_fields = ['patient__user__first_name', 'patient__user__last_name']