from django import forms
from django.contrib.auth.models import User
from .models import UserProfile,Patient, MedicalHistory, Symptom, Diagnosis
from datetime import date

class UserForm(forms.ModelForm):
    new_password = forms.CharField(label='Nueva Contraseña', widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(label='Confirmar Nueva Contraseña', widget=forms.PasswordInput, required=False)

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'email': 'Correo Electrónico',
        }

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')

        if new_password or confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError('Las contraseñas no coinciden.')

class UserProfileForm(forms.ModelForm):
    rut = forms.CharField(label='RUT', max_length=12)
    superintendence_number = forms.CharField(label='Número de superintendencia', max_length=50)
    region = forms.CharField(label='Región', max_length=100)
    commune = forms.CharField(label='Comuna', max_length=100)
    phone_number = forms.CharField(label='Número de teléfono', max_length=20)
    mineduc_registration_number = forms.CharField(label='Número de registro de mineduc', max_length=50, required=False)

    class Meta:
        model = UserProfile
        fields = ['rut', 'superintendence_number', 'region', 'commune', 'phone_number', 'mineduc_registration_number']
# forms.py

from django import forms
from django.contrib.auth.models import User
from .models import UserProfile

class RegistrationForm(forms.ModelForm):
    # Campos del modelo User
    first_name = forms.CharField(label='Nombre', max_length=30)
    last_name = forms.CharField(label='Apellido', max_length=30)
    email = forms.EmailField(label='Correo Electrónico')
    username = forms.CharField(label='Nombre de Usuario', max_length=30)
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password_confirm = forms.CharField(label='Confirmar Contraseña', widget=forms.PasswordInput)

    # Campos del modelo UserProfile
    rut = forms.CharField(label='RUT', max_length=12)
    superintendence_number = forms.CharField(label='Número de Superintendencia', max_length=50)
    region = forms.CharField(label='Región', max_length=100)
    commune = forms.CharField(label='Comuna', max_length=100)
    phone_number = forms.CharField(label='Número de Teléfono', max_length=20)
    mineduc_registration_number = forms.CharField(
        label='Número de Registro de Mineduc',
        max_length=50,
        required=False
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password']

    def clean_password_confirm(self):
        password = self.cleaned_data.get('password')
        password_confirm = self.cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return password_confirm

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('El nombre de usuario ya está en uso.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('El correo electrónico ya está registrado.')
        return email

    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if UserProfile.objects.filter(rut=rut).exists():
            raise forms.ValidationError('Este RUT ya está registrado.')
        # Aquí puedes agregar validación adicional del RUT
        return rut


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'first_name', 
            'last_name', 
            'rut', 
            'phone', 
            'birth_date', 
            'genre', 
            'region', 
            'ciudad', 
            'comuna', 
            'centro_de_salud', 
            'email', 
            'address'
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'genre': forms.Select(choices=[
                ('Masculino', 'Masculino'),
                ('Femenino', 'Femenino'),
                ('Otro', 'Otro'),
            ]),
            'rut': forms.TextInput(attrs={'placeholder': 'Ej. 12.345.678-9'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Ej. +56912345678'}),
            'email': forms.EmailInput(attrs={'placeholder': 'ejemplo@correo.com'}),
            'address': forms.TextInput(attrs={'placeholder': 'Ej. Calle Falsa 123'}),
            # Agrega más widgets según necesidad
        }
class MedicalHistoryForm(forms.ModelForm):
    class Meta:
        model = MedicalHistory
        fields = ['personal_history', 'family_history', 'clinical_history']  # Campos del modelo MedicalHistory
        widgets = {
            'personal_history': forms.Textarea(attrs={'rows': 4, 'id': 'id_personal_history'}),
            'family_history': forms.Textarea(attrs={'rows': 4, 'id': 'id_family_history'}),
            'clinical_history': forms.Textarea(attrs={'rows': 4, 'id': 'id_clinical_history'}),
        }

class SymptomForm(forms.ModelForm):
    class Meta:
        model = Symptom
        fields = ['physical_symptoms', 'social_symptoms', 'emotional_symptoms', 'behavioral_symptoms']  # Campos del modelo Symptom
        widgets = {
            'physical_symptoms': forms.Textarea(attrs={'rows': 2, 'id': 'id_physical_symptoms'}),
            'social_symptoms': forms.Textarea(attrs={'rows': 2, 'id': 'id_social_symptoms'}),
            'emotional_symptoms': forms.Textarea(attrs={'rows': 2, 'id': 'id_emotional_symptoms'}),
            'behavioral_symptoms': forms.Textarea(attrs={'rows': 2, 'id': 'id_behavioral_symptoms'}),
        }

class DiagnosisForm(forms.ModelForm):
    class Meta:
        model = Diagnosis
        fields = ['diagnosis', 'details', 'additional_diagnosis']  # Campos del modelo Diagnosis
        widgets = {
            'diagnosis': forms.Textarea(attrs={'rows': 4, 'id': 'id_diagnosis'}),
            'details': forms.Textarea(attrs={'rows': 4, 'id': 'id_details'}),
            'additional_diagnosis': forms.Textarea(attrs={'rows': 4, 'id': 'id_additional_diagnosis'}),
        }
