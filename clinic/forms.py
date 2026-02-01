from django import forms
from .models import Appointment, Patient, User
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from datetime import date
from .models import User, Patient, Doctor, Service, Appointment

class AppointmentForm(forms.ModelForm):
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
        
        self.fields['doctor'].queryset = Doctor.objects.filter(is_active=True)
        self.fields['doctor'].empty_label = "Выберите врача"
        self.fields['doctor'].label = "Врач"
        
        self.fields['service'].queryset = Service.objects.all()
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
    


class PatientRegistrationForm(UserCreationForm):
    phone = forms.CharField(
        max_length=20, 
        label="Телефон", 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '+7 (999) 123-45-67'})
    )
    
    birth_date = forms.DateField(
        label="Дата рождения", 
        widget=forms.SelectDateWidget(
            years=range(1920, date.today().year + 1),
            empty_label=("Год", "Месяц", "День")
        ),
        required=True
    )
    
    first_name = forms.CharField(
        max_length=30, 
        label="Имя", 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Иван'})
    )
    
    last_name = forms.CharField(
        max_length=30, 
        label="Фамилия", 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Иванов'})
    )
    
    email = forms.EmailField(
        label="Email", 
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'ivan@example.com'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'birth_date', 'password1', 'password2']
    
    def clean_birth_date(self):
        """Валидация даты рождения"""
        birth_date = self.cleaned_data.get('birth_date')
        
        if not birth_date:
            raise ValidationError("Пожалуйста, выберите дату рождения")
        
        if birth_date > date.today():
            raise ValidationError("Дата рождения не может быть в будущем")
        
        age = (date.today() - birth_date).days / 365.25
        
        if age < 1:
            raise ValidationError("Возраст должен быть не менее 1 года")
        if age > 150:
            raise ValidationError("Пожалуйста, проверьте дату рождения")
        
        return birth_date
    
    def clean_phone(self):
        """Валидация телефона"""
        phone = self.cleaned_data.get('phone')
        
        digits = ''.join(filter(str.isdigit, phone))
        
        if len(digits) < 10 or len(digits) > 15:
            raise ValidationError("Введите корректный номер телефона")
        
        return phone
    
    def clean_email(self):
        """Проверка уникальности email"""
        email = self.cleaned_data.get('email')
        
        if User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email уже зарегистрирован")
        
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.CLIENT
        user.phone = self.cleaned_data['phone']
        user.login_method = User.EMAIL
        
        if commit:
            user.save()
            Patient.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                birth_date=self.cleaned_data['birth_date']
            )
        return user