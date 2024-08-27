from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
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
        'birth_date': patient.birth_date
    } for patient in patients]

    return JsonResponse({'patients': patient_data})

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
            )
            
            bot_response = ''.join(chunk['message']['content'] for chunk in stream)
        
        except Exception as e:
            print(f"Error al conectar con Ollama: {e}")
            bot_response = 'Lo siento, no puedo procesar tu solicitud en este momento.'
        
        return JsonResponse({'response': bot_response})
    return JsonResponse({'response': 'Método no permitido'}, status=405)


@login_required
def chat_view(request):
    if request.method == 'POST':
        user_input = request.POST.get('user_input', '')
        try:
            stream = ollama.chat(
                model='psicoia',
                messages=[{'role': 'user', 'content': user_input}],
                stream=True,
            )
            bot_response = ''.join(chunk['message']['content'] for chunk in stream)
            
            return JsonResponse({'response': bot_response})

        except Exception as e:
            print(f"Error al conectar con Ollama: {e}")
            return JsonResponse({'response': 'Lo siento, no puedo procesar tu solicitud en este momento.'})

    elif request.method == 'GET':
        patient_data = request.GET.get('data')
        if patient_data:
            patient_data = urllib.parse.unquote(patient_data)
            patient_data = eval(patient_data)  # Convertir la cadena de datos en un diccionario
        else:
            patient_data = {}

        return render(request, 'chat.html', {
            'patient_data': patient_data,  # Pasar los datos del paciente al template
        })

    return JsonResponse({'response': 'Método no permitido'}, status=405)
def register_patient(request):
    error_message = None

    if request.method == 'POST':
        patient_form = PatientForm(request.POST)
        medical_history_form = MedicalHistoryForm(request.POST)
        symptom_form = SymptomForm(request.POST)
        diagnosis_form = DiagnosisForm(request.POST)
        
        if all([patient_form.is_valid(), medical_history_form.is_valid(), symptom_form.is_valid(), diagnosis_form.is_valid()]):
            patient = patient_form.save()
            medical_history = medical_history_form.save(commit=False)
            medical_history.patient = patient
            medical_history.save()

            symptoms = symptom_form.save(commit=False)
            symptoms.patient = patient
            symptoms.save()

            diagnosis = diagnosis_form.save(commit=False)
            diagnosis.patient = patient
            diagnosis.save()

            # Datos del paciente como diccionario para pasarlos como parámetro
            patient_data = {
                'first_name': patient.first_name,
                'last_name': patient.last_name,
                'birth_date': patient.birth_date.strftime('%Y-%m-%d'),
                'genre': patient.genre,
                'sintomas': {
                    'fisicos': symptom_form.cleaned_data['physical_symptoms'],
                    'sociales': symptom_form.cleaned_data['social_symptoms'],
                    'emocionales': symptom_form.cleaned_data['emotional_symptoms'],
                    'comportamiento': symptom_form.cleaned_data['behavioral_symptoms'],
                },
                'diagnostico': diagnosis_form.cleaned_data['diagnosis'],
            }

            # Verificar la acción seleccionada
            action = request.POST.get('action')
            if action == 'interact':
                # Serializar los datos del paciente para pasarlos en la URL
                serialized_data = urllib.parse.quote(str(patient_data))
                return redirect(reverse('chat') + f"?data={serialized_data}")
            else:
                return redirect('home')
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
    
@csrf_exempt
def update_diagnosis(request):
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        new_diagnosis = request.POST.get('new_diagnosis')
        
        try:
            # Buscar el paciente por ID
            patient = Patient.objects.get(id=patient_id)
            # Actualizar el diagnóstico
            patient.diagnosis_set.update_or_create(
                defaults={'diagnosis': new_diagnosis},
                patient=patient
            )
            return JsonResponse({'success': True, 'message': 'Diagnóstico actualizado correctamente.'})
        except Patient.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Paciente no encontrado.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error al actualizar diagnóstico: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Método no permitido.'})


def user_logout(request):
    logout(request)
    return redirect('inicio') 