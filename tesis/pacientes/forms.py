from django import forms
from .models import Patient, MedicalHistory, Symptom, Diagnosis
from datetime import date

class PatientForm(forms.ModelForm):
    age = forms.IntegerField(label='Age', required=False, widget=forms.NumberInput(attrs={'readonly': 'readonly'}))
    class Meta:
        model = Patient
        fields = [
            'first_name', 
            'last_name', 
            'rut', 
            'phone', 
            'birth_date',
            'age',
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
    def clean(self):
        cleaned_data = super().clean()
        birth_date = cleaned_data.get('birth_date')
        if birth_date:
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            cleaned_data['age'] = age
        return cleaned_data
    
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
