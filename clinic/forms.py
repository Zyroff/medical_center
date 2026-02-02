from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model  # ← ВАЖНО!
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Appointment, Doctor, Service, Patient

# Получаем кастомную модель User
User = get_user_model()

class PatientRegistrationForm(UserCreationForm):
    """Форма регистрации пациента для кастомной модели User"""
    phone = forms.CharField(
        max_length=20,
        required=True,
        label='Телефон',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 999-99-99'
        })
    )
    birth_date = forms.DateField(
        required=True,
        label='Дата рождения',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    first_name = forms.CharField(
        required=True,
        max_length=30,
        label='Имя',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        required=True,
        max_length=30,
        label='Фамилия',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User  # Используем кастомную модель User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone', 'birth_date', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Настраиваем поля паролей
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Это имя пользователя уже занято')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Этот email уже используется')
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if Patient.objects.filter(phone=phone).exists():
            raise forms.ValidationError('Этот телефон уже зарегистрирован')
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.role = User.CLIENT  # Устанавливаем роль пациента
        
        # Сохраняем телефон в пользователе, если есть поле
        if hasattr(user, 'phone'):
            user.phone = self.cleaned_data['phone']
        
        if commit:
            user.save()
            # Создаем профиль пациента
            Patient.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                birth_date=self.cleaned_data['birth_date'],
                address=''
            )
        return user
class AppointmentForm(forms.ModelForm):
    """Форма записи на прием"""
    class Meta:
        model = Appointment
        fields = ['doctor', 'service', 'date_time', 'notes']
        widgets = {
            'doctor': forms.Select(attrs={
                'class': 'form-select',
                'id': 'doctor-select'
            }),
            'service': forms.Select(attrs={
                'class': 'form-select',
                'id': 'service-select'
            }),
            'date_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'id': 'datetime-input',
                'min': timezone.now().strftime('%Y-%m-%dT%H:%M')
            }),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control',
                'placeholder': 'Дополнительная информация, симптомы, пожелания...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['doctor'].queryset = Doctor.objects.filter(is_active=True).order_by('specialization', 'user__last_name')
        self.fields['service'].queryset = Service.objects.all().order_by('name')
        
        self.fields['doctor'].empty_label = "Выберите врача"
        self.fields['doctor'].label = "Врач"
        
        self.fields['service'].empty_label = "Выберите услугу"
        self.fields['service'].label = "Услуга"
        
        self.fields['date_time'].label = "Дата и время приема"
        self.fields['notes'].label = "Примечания"
        
        self.fields['doctor'].help_text = "Выберите врача из списка"
        self.fields['service'].help_text = "Выберите медицинскую услугу"
        self.fields['date_time'].help_text = "Выберите удобные дату и время"
        
        if user and hasattr(user, 'last_doctor'):
            self.fields['doctor'].initial = user.last_doctor

    def clean_date_time(self):
        date_time = self.cleaned_data.get('date_time')
        if date_time < timezone.now():
            raise ValidationError("Нельзя записаться на прошедшее время")
        
        hour = date_time.hour
        if hour < 8 or hour > 20:
            raise ValidationError("Запись возможна только с 8:00 до 20:00")
        
        return date_time
    
    def clean(self):
        cleaned_data = super().clean()
        doctor = cleaned_data.get('doctor')
        date_time = cleaned_data.get('date_time')
        
        if doctor and date_time:
            conflicting = Appointment.objects.filter(
                doctor=doctor,
                date_time=date_time,
                status__in=['pending', 'confirmed']
            ).exists()
            
            if conflicting:
                raise ValidationError("Врач занят в это время. Выберите другое время.")
        
        return cleaned_data