from django import forms
from .models import Patient, MedicalHistory, Symptom, Diagnosis
from datetime import date


class PatientForm(forms.ModelForm):
    age = forms.IntegerField(label='Age', required=False, widget=forms.NumberInput(attrs={'readonly': 'readonly'}))

    class Meta:
        model = Patient
        fields = ['first_name', 'last_name', 'birth_date', 'genre', 'rut', 'region', 'ciudad', 'comuna', 'centro_de_salud', 'age']
        widgets = {
            'first_name': forms.TextInput(attrs={'id': 'id_first_name'}),
            'last_name': forms.TextInput(attrs={'id': 'id_last_name'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'id': 'id_birth_date'}),
            'genre': forms.TextInput(attrs={'id': 'id_genre'}),
            'rut': forms.TextInput(attrs={'id': 'id_rut'}),
            'region': forms.TextInput(attrs={'id': 'id_region'}),
            'ciudad': forms.TextInput(attrs={'id': 'id_ciudad'}),
            'comuna': forms.TextInput(attrs={'id': 'id_comuna'}),
            'centro_de_salud': forms.TextInput(attrs={'id': 'id_centro_de_salud'}),
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
