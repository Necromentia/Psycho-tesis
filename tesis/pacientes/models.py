
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=255)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
class Folder(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    
class Patient(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    genre = models.CharField(max_length=10)
    assigned_user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, null=True, blank=True)  # Aquí se permite que sea nulo
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_view_at = models.DateTimeField(null=True)
    
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"



class MedicalHistory(models.Model):
    id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    personal_history = models.TextField()
    family_history = models.TextField()
    clinical_history = models.TextField()

    def __str__(self):
        return f"Historial clínico de {self.patient}"
    
class Symptom(models.Model):
    id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    emotional_symptoms = models.TextField()
    behavioral_symptoms = models.TextField()
    social_symptoms = models.TextField()
    physical_symptoms = models.TextField()

    def __str__(self):
        return f"Síntomas de {self.patient}"

class Diagnosis(models.Model):
    id = models.AutoField(primary_key=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    diagnosis = models.CharField(max_length=255)
    details = models.TextField(null=True, blank=True)
    additional_diagnosis = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Diagnóstico de {self.patient}"

