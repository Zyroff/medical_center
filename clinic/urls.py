from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('doctors/', views.DoctorListView.as_view(), name='doctor_list'),
    path('services/', views.ServiceListView.as_view(), name='service_list'),
    path('appointment/create/', views.AppointmentCreateView.as_view(), name='appointment_create'),
    path('appointments/', views.AppointmentListView.as_view(), name='appointment_list'),
    path('profile/', views.patient_profile, name='patient_profile'),
]