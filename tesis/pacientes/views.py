from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.utils.decorators import method_decorator


from .forms import PatientForm, MedicalHistoryForm, SymptomForm, DiagnosisForm
from .models import Patient, MedicalHistory, Symptom, Diagnosis, Folder
import urllib.parse

import ollama


def inicio(request):
    login_error = None
    register_error = None
    
    if request.method == 'POST':
        if 'login' in request.POST:
            # Proceso de inicio de sesión
            username = request.POST['username']
            password = request.POST['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')  
            else:
                messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
        
        elif 'register' in request.POST:
            username = request.POST['new_username']
            password = request.POST['new_password']
            if User.objects.filter(username=username).exists():
                register_error = 'El nombre de usuario ya está en uso. Por favor, elige otro.'
            else:
                User.objects.create_user(username=username, password=password)
                messages.success(request, 'Usuario creado satisfactoriamente. Por favor, inicia sesión.')
                return redirect('inicio')  

    return render(request, 'index.html', {'register_error': register_error})


@login_required
def home(request):
    folders = Folder.objects.filter(user=request.user)
    unassigned_patients = Patient.objects.filter(folder__isnull=True)
    recent_patients = Patient.objects.filter(assigned_user=request.user, last_view_at__isnull=False).order_by('-last_view_at')[:10]

    if request.method == 'POST':
        if request.method == 'POST' and 'create_folder' in request.POST:
            folder_name = request.POST['folder_name']
            patient_id = request.POST.get('patient_id')

            # Crear la nueva carpeta
            new_folder = Folder.objects.create(name=folder_name, user=request.user)

            # Si se seleccionó un paciente, vincularlo a la nueva carpeta
            if patient_id:
                patient = Patient.objects.get(id=patient_id)
                patient.folder = new_folder
                patient.save()

            return redirect('home')
        elif 'edit_folder' in request.POST:
            folder_id = request.POST.get('folder_id')
            folder_name = request.POST.get('folder_name')
            patient_id = request.POST.get('patient_id')

            # Editar el nombre de la carpeta
            folder = Folder.objects.get(id=folder_id, user=request.user)
            if folder_name:
                folder.name = folder_name
                folder.save()

            # Agregar paciente a la carpeta
            if patient_id:
                patient = Patient.objects.get(id=patient_id)
                patient.folder = folder
                patient.save()

        elif 'delete_folder' in request.POST:
            folder_id = request.POST.get('folder_id')
            Folder.objects.filter(id=folder_id, user=request.user).delete()

        return redirect('home')

    return render(request, 'home.html', {
        'folders': folders,
        'unassigned_patients': unassigned_patients,
        'recent_patients': recent_patients,
    })


@login_required
def get_patients_by_folder(request, folder_id):
    folder = Folder.objects.get(id=folder_id)
    patients = folder.patient_set.all()

    patient_data = [{
        'id': patient.id,
        'first_name': patient.first_name,
        'last_name': patient.last_name,
        'genre': patient.genre,
        'birth_date': patient.birth_date,
        'diagnosis': Diagnosis.objects.filter(patient=patient).last().diagnosis if Diagnosis.objects.filter(patient=patient).exists() else "No registrado"
    } for patient in patients]

    return JsonResponse({'patients': patient_data})
def get_patient(request, patient_id):
    try:
        patient = Patient.objects.get(id=patient_id)
        patient.last_view_at = timezone.now()
        patient.save()

        medical_history = MedicalHistory.objects.filter(patient=patient).first()
        symptoms = Symptom.objects.filter(patient=patient).first()
        diagnosis = Diagnosis.objects.filter(patient=patient).first()

        data = {
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'genre': patient.genre,
            'birth_date': patient.birth_date,
            'personal_history': medical_history.personal_history if medical_history else 'No hay historial personal',
            'family_history': medical_history.family_history if medical_history else 'No hay historial familiar',
            'clinical_history': medical_history.clinical_history if medical_history else 'No hay historial clínico',
            'physical_symptoms': symptoms.physical_symptoms if symptoms else 'No hay síntomas físicos',
            'social_symptoms': symptoms.social_symptoms if symptoms else 'No hay síntomas sociales',
            'emotional_symptoms': symptoms.emotional_symptoms if symptoms else 'No hay síntomas emocionales',
            'behavioral_symptoms': symptoms.behavioral_symptoms if symptoms else 'No hay síntomas de comportamiento',
            'diagnosis': diagnosis.diagnosis if diagnosis else 'Sin diagnóstico',
            'diagnosis_details': diagnosis.details if diagnosis.details else 'Sin detalles',
            'aditional_diagnosis': diagnosis.additional_diagnosis if diagnosis.additional_diagnosis else 'Sin diagnóstico adicional',
        }
        return JsonResponse(data)
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Paciente no encontrado'}, status=404)

@csrf_exempt
def update_diagnosis(request, patient_id):
    if request.method == 'POST':
        diagnosis = request.POST.get('diagnosis')
        diagnosis_details = request.POST.get('diagnosis_details')
        additional_diagnosis = request.POST.get('additional_diagnosis')

        if not diagnosis:
            return JsonResponse({'error': 'Faltan campos requeridos'}, status=400)

        try:
            patient = Patient.objects.get(id=patient_id)
            diagnosis_obj, created = Diagnosis.objects.get_or_create(patient=patient)
            diagnosis_obj.diagnosis = diagnosis
            diagnosis_obj.details = diagnosis_details
            diagnosis_obj.additional_diagnosis = additional_diagnosis
            diagnosis_obj.save()

            # Redirigir a la página de inicio después de la actualización
            return HttpResponseRedirect(reverse('home'))
        except Patient.DoesNotExist:
            return JsonResponse({'error': 'Paciente no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)
def delete_patient(request, patient_id):
    if request.method == 'POST':
        patient = get_object_or_404(Patient, id=patient_id)
        
        # Eliminar todos los datos relacionados al paciente
        MedicalHistory.objects.filter(patient=patient).delete()
        Symptom.objects.filter(patient=patient).delete()
        Diagnosis.objects.filter(patient=patient).delete()

        # Finalmente, eliminar el paciente
        patient.delete()

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
@login_required
def create_or_edit_folder(request):
    if request.method == 'POST':
        folder_id = request.POST.get('folder_id')
        folder_name = request.POST.get('folder_name')
        patient_id = request.POST.get('patient_id')

        if folder_id:  # Editar carpeta existente
            folder = get_object_or_404(Folder, id=folder_id, user=request.user)
            folder.name = folder_name
            folder.save()
        else:  # Crear nueva carpeta
            folder = Folder.objects.create(name=folder_name, user=request.user)

        if patient_id:
            patient = get_object_or_404(Patient, id=patient_id)
            patient.folder = folder
            patient.save()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def delete_folder(request):
    if request.method == 'POST':
        folder_id = request.POST.get('folder_id')
        folder = get_object_or_404(Folder, id=folder_id, user=request.user)
        folder.delete()

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request'})


@csrf_exempt 
def get_response(request):
    if request.method == 'POST':
        user_input = request.POST.get('user_input', '')
        try:
            stream = ollama.chat(
                model='psicoia', 
                messages=[{'role': 'user', 'content': user_input}],
                stream=True,
            ).get('message', {}).get('content', 'Respuesta por defecto si falla')
            
            bot_response = ''.join(chunk['message']['content'] for chunk in stream)
        
        except Exception as e:
            print(f"Error al conectar con Ollama: {e}")
            bot_response = 'Lo siento, no puedo procesar tu solicitud en este momento.'
        
        return JsonResponse({'response': bot_response})
    return JsonResponse({'response': 'Método no permitido'}, status=405)
@login_required
def chat_view(request):
    patient_id = request.GET.get('patient_id')
    patient_data = None

    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
        patient.last_view_at = timezone.now()
        patient.save()

        medical_history = MedicalHistory.objects.filter(patient=patient).first()
        diagnosis = Diagnosis.objects.filter(patient=patient).first()
        symptoms = Symptom.objects.filter(patient=patient).first()

        patient_data = {
            'id': patient.id,  # Asegúrate de que `id` esté presente
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'birth_date': patient.birth_date,
            'genre': patient.genre,
            'sintomas': {
                'fisicos': symptoms.physical_symptoms if symptoms else '',
                'sociales': symptoms.social_symptoms if symptoms else '',
                'emocionales': symptoms.emotional_symptoms if symptoms else '',
                'comportamiento': symptoms.behavioral_symptoms if symptoms else '',
            },
            'diagnostico': diagnosis.diagnosis if diagnosis else 'Sin diagnóstico',
            'diagnosis_details': diagnosis.details if diagnosis else 'No hay detalles',
            'additional_diagnosis': diagnosis.additional_diagnosis if diagnosis else 'No hay diagnósticos adicionales',
            'medical_history': {
                'personal': medical_history.personal_history if medical_history else 'No hay historial personal',
                'family': medical_history.family_history if medical_history else 'No hay historial familiar',
                'clinical': medical_history.clinical_history if medical_history else 'No hay historial clínico',
            }
        }

    return render(request, 'chat.html', {
        'patient_data': patient_data,
    })

def register_patient(request):
    error_message = None

    if request.method == 'POST':
        patient_form = PatientForm(request.POST)
        medical_history_form = MedicalHistoryForm(request.POST)
        symptom_form = SymptomForm(request.POST)
        diagnosis_form = DiagnosisForm(request.POST)
        
        if all([patient_form.is_valid(), medical_history_form.is_valid(), symptom_form.is_valid()]):
            patient = patient_form.save(commit=False)  # No guardar todavía para poder asignar más campos
            patient.assigned_user = request.user  # Asignar el usuario actual
            patient.last_view_at = timezone.now()  # Actualizar el campo last_view_at
            patient.save()  # Guardar el paciente ahora

            medical_history = medical_history_form.save(commit=False)
            medical_history.patient = patient
            medical_history.save()

            symptoms = symptom_form.save(commit=False)
            symptoms.patient = patient
            symptoms.save()

            diagnosis = diagnosis_form.save(commit=False)
            diagnosis.patient = patient
            diagnosis.save()

            # Redireccionar a la página de interacción con la IA
            return redirect(reverse('chat') + f'?patient_id={patient.id}')
        else:
            error_message = "Hubo un error en el formulario. Por favor, revisa los campos e intenta nuevamente."

    else:
        patient_form = PatientForm()
        medical_history_form = MedicalHistoryForm()
        symptom_form = SymptomForm()
        diagnosis_form = DiagnosisForm()

    return render(request, 'registrar_paciente.html', {
        'patient_form': patient_form,
        'medical_history_form': medical_history_form,
        'symptom_form': symptom_form,
        'diagnosis_form': diagnosis_form,
        'error_message': error_message,
    })
@login_required
def get_recent_patients(request):
    recent_patients = Patient.objects.filter(assigned_user=request.user, last_view_at__isnull=False).order_by('-last_view_at')[:10]
    data = [
        {
            'id': patient.id,
            'name': f"{patient.first_name} {patient.last_name}",
            'diagnosis': "Diagnóstico: " + patient.diagnosis_set.last().diagnosis if patient.diagnosis_set.exists() else 'Sin diagnóstico'
        }
        for patient in recent_patients
    ]
    return JsonResponse({'recent_patients': data})
@csrf_exempt
def update_patient(request, patient_id):
    if request.method == 'POST':
        diagnosis = request.POST.get('diagnosis')
        diagnosis_details = request.POST.get('diagnosis_details')
        additional_diagnosis = request.POST.get('additional_diagnosis')

        if not diagnosis:
            return JsonResponse({'error': 'Faltan campos requeridos'}, status=400)

        try:
            patient = Patient.objects.get(id=patient_id)
            diagnosis_obj, created = Diagnosis.objects.get_or_create(patient=patient)
            diagnosis_obj.diagnosis = diagnosis
            diagnosis_obj.details = diagnosis_details
            diagnosis_obj.additional_diagnosis = additional_diagnosis
            diagnosis_obj.save()

            return JsonResponse({'success': 'Diagnóstico actualizado correctamente'})
        except Patient.DoesNotExist:
            return JsonResponse({'error': 'Paciente no encontrado'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)
def user_logout(request):
    logout(request)
    return redirect('inicio') 