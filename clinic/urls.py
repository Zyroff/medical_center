from django.urls import path
from . import views
from .views import CustomLoginView

urlpatterns = [
    path('', views.home, name='home'),

    path('login/', CustomLoginView.as_view(), name='custom_login'),
    path('register/', views.register_patient, name='register'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('telegram-auth/', views.telegram_auth, name='telegram_auth'),

    path('doctors/', views.DoctorListView.as_view(), name='doctor_list'),
    path('services/', views.ServiceListView.as_view(), name='service_list'),

    path('appointments/new/', views.AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/', views.AppointmentListView.as_view(), name='appointment_list'),

    path('patient-profile/', views.patient_profile, name='patient_profile'),
    path('doctor-dashboard/', views.doctor_dashboard, name='doctor_dashboard'),

    path('login-failed/', views.login_failed, name='login_failed'),
    path('access-denied/', views.access_denied, name='access_denied'),
]