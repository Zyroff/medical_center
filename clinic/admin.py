from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Doctor, Patient, Service, 
    Appointment, MedicalRecord, 
    TelegramAuthToken, DoctorAccessCode, ServiceCategory
)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('role', 'phone', 'telegram_id', 'login_method', 'doctor_profile')
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {
            'fields': ('role', 'phone', 'telegram_id', 'login_method')
        }),
    )

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'specialization', 'room', 'is_active')
    list_filter = ('specialization', 'is_active')
    search_fields = ('user__first_name', 'user__last_name', 'specialization')
    
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'birth_date')
    search_fields = ('user__first_name', 'user__last_name', 'phone')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'duration', 'is_popular', 'is_active']
    list_filter = ['category', 'is_popular', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['doctors']
    ordering = ['order', 'name']

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'service', 'date_time', 'status')
    list_filter = ('status', 'date_time')
    search_fields = ('patient__user__first_name', 'doctor__user__first_name')

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'created_at')
    
@admin.register(TelegramAuthToken)
class TelegramAuthTokenAdmin(admin.ModelAdmin):
    list_display = ('token', 'telegram_id', 'role', 'is_used', 'expires_at')
    list_filter = ('is_used', 'role')

@admin.register(DoctorAccessCode)
class DoctorAccessCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'created_by', 'is_used', 'expires_at')

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']