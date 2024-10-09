from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter

from django.utils.decorators import method_decorator
import json


from .forms import PatientForm, MedicalHistoryForm, SymptomForm, DiagnosisForm
from .models import UserProfile,Patient, MedicalHistory, Symptom, Diagnosis, Folder
import urllib.parse
import requests
from ollama import Client
from django.views.decorators.cache import cache_page
from django.conf import settings
from .forms import UserForm, UserProfileForm,RegistrationForm


def inicio(request):
    if request.user.is_authenticated:
        return redirect('home')  # Redirige a home si ya está autenticado

    next_url = request.GET.get('next', '')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', next_url)
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(next_url or 'home')
        else:
            messages.error(request, 'Nombre de usuario o contraseña incorrectos.')
    return render(request, 'index.html', {'next': next_url})
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            # Crear el usuario
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password'],
                email=form.cleaned_data['email'],
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            )

            # Obtener el perfil de usuario creado por la señal
            user_profile = user.userprofile  # Gracias a la señal, ya existe un UserProfile asociado

            # Actualizar los campos del perfil
            user_profile.rut = form.cleaned_data['rut']
            user_profile.superintendence_number = form.cleaned_data['superintendence_number']
            user_profile.region = form.cleaned_data['region']
            user_profile.commune = form.cleaned_data['commune']
            user_profile.phone_number = form.cleaned_data['phone_number']
            user_profile.mineduc_registration_number = form.cleaned_data['mineduc_registration_number']

            # Guardar el perfil actualizado
            user_profile.save()

            messages.success(request, 'Registro exitoso. Ahora puedes iniciar sesión.')
            return redirect('inicio')  # Redirige a la página de inicio de sesión
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})


@login_required
def home(request):
    trash_folder = Folder.objects.filter(user=request.user).get(is_fixed=True)
    folders = Folder.objects.filter(user=request.user).exclude(is_fixed=True)
    unassigned_patients = Patient.objects.filter(assigned_user=request.user,folder__isnull=True)
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

        return redirect('home')

    return render(request, 'home.html', {
        'trash_folder': trash_folder,
        'folders': folders,
        'unassigned_patients': unassigned_patients,
        'recent_patients': recent_patients,
    })

@login_required
def user_settings(request):
    user = request.user
    try:
        user_profile = user.userprofile
    except UserProfile.DoesNotExist:
        user_profile = UserProfile.objects.create(user=user)

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=user_profile)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            new_password = user_form.cleaned_data.get('new_password')
            if new_password:
                user.set_password(new_password)
            user.save()
            profile_form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('user_settings')

        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        # Asegúrate de pasar las instancias para que los formularios se prellenen
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user_profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }
    return render(request, 'user_settings.html', context)
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
            'age': patient.age,
            'rut': patient.rut,
            'region': patient.region,
            'ciudad': patient.ciudad,
            'comuna': patient.comuna,
            'centro_de_salud': patient.centro_de_salud,
            'phone': patient.phone,
            'email': patient.email,
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
        try:
            data = json.loads(request.body)  # Cargar el JSON del cuerpo de la petición

            diagnosis = data.get('diagnosis')
            diagnosis_details = data.get('diagnosis_details')
            additional_diagnosis = data.get('additional_diagnosis')

            if not diagnosis:
                return JsonResponse({'error': 'Faltan campos requeridos'}, status=400)

            try:
                patient = Patient.objects.get(id=patient_id)
                diagnosis_obj, created = Diagnosis.objects.get_or_create(patient=patient)
                diagnosis_obj.diagnosis = diagnosis
                diagnosis_obj.details = diagnosis_details
                diagnosis_obj.additional_diagnosis = additional_diagnosis
                diagnosis_obj.save()

                return JsonResponse({'message': 'Diagnóstico actualizado correctamente'}, status=200)
            except Patient.DoesNotExist:
                return JsonResponse({'error': 'Paciente no encontrado'}, status=404)
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Error al decodificar el JSON'}, status=400)
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
def create_folder(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        folder_name = data.get('folder_name')

        if not folder_name:
            return JsonResponse({'success': False, 'error': 'El nombre de la carpeta es obligatorio.'})

        # Verificar si ya existe una carpeta con ese nombre para el usuario
        if Folder.objects.filter(name=folder_name, user=request.user).exists():
            return JsonResponse({'success': False, 'error': 'Ya tienes una carpeta con ese nombre.'})

        # Crear nueva carpeta
        folder = Folder.objects.create(name=folder_name, user=request.user)

        return JsonResponse({'success': True, 'folder': {'id': folder.id, 'name': folder.name}})

    return JsonResponse({'success': False, 'error': 'Solicitud inválida'})
@login_required
def rename_folder(request):
    data = json.loads(request.body)
    folder_id = data.get('folder_id')
    new_name = data.get('new_name')

    if not new_name:
        return JsonResponse({'success': False, 'error': 'El nuevo nombre es obligatorio.'})

    try:
        folder = Folder.objects.get(id=folder_id, user=request.user)
        if folder.name == 'Papelera':
            return JsonResponse({'success': False, 'error': 'No puedes renombrar la carpeta Papelera.'})
        folder.name = new_name
        folder.save()
        return JsonResponse({'success': True})
    except Folder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'La carpeta no existe.'})

@login_required
def delete_folder(request):
    data = json.loads(request.body)
    folder_id = data.get('folder_id')

    try:
        folder = Folder.objects.get(id=folder_id, user=request.user)
        if folder.name == 'Papelera':
            return JsonResponse({'success': False, 'error': 'No puedes eliminar la carpeta Papelera.'})
        folder.delete()
        return JsonResponse({'success': True})
    except Folder.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'La carpeta no existe.'})
import requests


@csrf_exempt
def get_response(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_input = data.get('user_input', '')
            print(f"user_input: {user_input}")

            # Llamar a la función de IA
            bot_response = ollama_api(user_input)
            print(f"Bot response: {bot_response}")

            return JsonResponse({'response': bot_response})
        except json.JSONDecodeError as e:
            print(f"Error al decodificar JSON: {e}")
            return JsonResponse({'response': 'Error en los datos enviados.'}, status=400)
    else:
        return JsonResponse({'response': 'Método no permitido'}, status=405)

def ollama_api(user_input):
    OLLAMA_API_URL = f"http://{settings.OLLAMA_HOST}:{settings.OLLAMA_PORT}/api/chat"

    payload = {
        'model': 'sujatowist/tesis',
        'messages': [{'role': 'user', 'content': user_input}]
    }

    try:
        # Realiza la solicitud a la API de Ollama con streaming habilitado
        response = requests.post(OLLAMA_API_URL, json=payload, stream=True)
        response.raise_for_status()

        # Procesa la respuesta en streaming
        bot_response = ''
        for line in response.iter_lines():
            if line:
                data = json.loads(line.decode('utf-8'))
                content = data.get('message', {}).get('content', '')
                bot_response += content

        return bot_response

    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con Ollama: {e}")
        return 'Lo siento, no puedo procesar tu solicitud en este momento.'
@login_required
def chat_view(request):
    patient_id = request.GET.get('patient_id')
    patient_data = None
    recent_patients = Patient.objects.filter(assigned_user=request.user, last_view_at__isnull=False).order_by('-last_view_at')[:10]


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
        'recent_patients': recent_patients,
    })
@csrf_exempt
def assign_patient_to_folder(request):
    if request.method == 'POST':
        data = json.loads(request.body)  # Asegúrate de parsear el JSON del cuerpo
        patient_id = data.get('patient_id')
        folder_id = data.get('folder_id')

        try:
            patient = Patient.objects.get(id=patient_id)
            folder = Folder.objects.get(id=folder_id)
            patient.folder = folder  # Asigna la carpeta al paciente
            patient.save()  # Guarda el cambio en la base de datos
            return JsonResponse({'success': True})
        except Patient.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Paciente no encontrado'})
        except Folder.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Carpeta no encontrada'})
    return JsonResponse({'success': False, 'error': 'Método no permitido'})
@login_required
def register_patient(request):
    error_message = None

    if request.method == 'POST':
        action = request.POST.get('action', 'register')  # Obtener la acción del campo oculto
        patient_form = PatientForm(request.POST)
        medical_history_form = MedicalHistoryForm(request.POST)
        symptom_form = SymptomForm(request.POST)
        diagnosis_form = DiagnosisForm(request.POST)
        
        if all([
            patient_form.is_valid(), 
            medical_history_form.is_valid(), 
            symptom_form.is_valid(), 
            diagnosis_form.is_valid()
        ]):
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
            if action == 'interact':
                # Redireccionar a la página de interacción con la IA
                return redirect(reverse('chat') + f'?patient_id={patient.id}')
            if action == 'register':
                # Redireccionar a una página de éxito o la misma página con un mensaje
                return redirect(reverse('home'))  # Ajusta según tu configuración
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
def edit_patient(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id, assigned_user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action', 'register')  # Obtener la acción del campo oculto
        patient_form = PatientForm(request.POST, instance=patient)
        medical_history_form = MedicalHistoryForm(request.POST, instance=patient.medicalhistory)
        symptom_form = SymptomForm(request.POST, instance=patient.symptom)
        diagnosis_form = DiagnosisForm(request.POST, instance=patient.diagnosis)
        
        if all([
            patient_form.is_valid(), 
            medical_history_form.is_valid(), 
            symptom_form.is_valid(),
            diagnosis_form.is_valid()
        ]):
            patient = patient_form.save(commit=False)
            patient.last_view_at = timezone.now()
            patient.save()
            
            medical_history_form.save()
            symptom_form.save()
            diagnosis_form.save()
            
            if action == 'interact':
                # Redireccionar a la página de interacción con la IA
                return redirect(reverse('chat') + f'?patient_id={patient.id}')
            if action == 'register':
                # Redireccionar a una página de éxito o la misma página con un mensaje
                return redirect(reverse('home'))  # Ajusta según tu configuración
        else:
            messages.error(request, 'Hubo un error en el formulario. Por favor, revisa los campos e intenta nuevamente.')
    else:
        patient_form = PatientForm(instance=patient)
        medical_history_form = MedicalHistoryForm(instance=patient.medicalhistory)
        symptom_form = SymptomForm(instance=patient.symptom)
        diagnosis_form = DiagnosisForm(instance=patient.diagnosis)
    
    return render(request, 'registrar_paciente.html', {
        'patient_form': patient_form,
        'medical_history_form': medical_history_form,
        'symptom_form': symptom_form,
        'diagnosis_form': diagnosis_form,
        'is_edit': True,
    })
@login_required
def get_recent_patients(request):
    #recent_patients = Patient.objects.filter(assigned_user=request.user, last_view_at__isnull=False).order_by('-last_view_at')[:10]
    recent_patients = Patient.objects.filter(assigned_user=request.user).exclude(folder__is_fixed=True).order_by('-last_view_at')[:5]
    data = [
        {
            'id': patient.id,
            'name': f"{patient.first_name} {patient.last_name}",
            'diagnosis': "Diagnóstico: " + patient.diagnosis.diagnosis
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

@csrf_exempt
def move_patient_to_trash(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        try:
            patient = Patient.objects.get(id=patient_id)
            # Obtener la carpeta "Papelera" del usuario
            trash_folder, created = Folder.objects.get_or_create(
                user=request.user,
                name='Papelera',
                defaults={'is_fixed': True}
            )
            patient.folder = trash_folder
            patient.save()
            return JsonResponse({'success': True})
        except Patient.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Paciente no encontrado'})
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)    
@login_required
def get_trash_folder_id(request):
    try:
        trash_folder = Folder.objects.get(user=request.user, name='Papelera')
        return JsonResponse({'folder_id': trash_folder.id})
    except Folder.DoesNotExist:
        return JsonResponse({'folder_id': None})


@csrf_exempt
@login_required
def restore_patient_from_trash(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        try:
            patient = Patient.objects.get(id=patient_id)
            # Verificar que el paciente está en la "Papelera"
            if patient.folder.name == 'Papelera' and patient.folder.user == request.user:
                patient.folder = None  # Asignar a sin carpeta
                patient.save()
                # Preparar los datos del paciente para enviarlos al cliente
                patient_data = {
                    'id': patient.id,
                    'first_name': patient.first_name,
                    'last_name': patient.last_name,
                    'genre': patient.genre,
                    'birth_date': str(patient.birth_date),
                    'diagnosis': patient.diagnosis_set.last().diagnosis if patient.diagnosis_set.exists() else 'Sin diagnóstico'
                }
                return JsonResponse({'success': True, 'patient': patient_data})
            else:
                return JsonResponse({'success': False, 'error': 'El paciente no está en la Papelera'})
        except Patient.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Paciente no encontrado'})
    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)


@login_required
def download_patient_pdf(request, patient_id):
    try:
        patient = Patient.objects.get(id=patient_id)
        diagnosis = Diagnosis.objects.filter(patient=patient).first()
        medical_history = MedicalHistory.objects.filter(patient=patient).first()
        symptoms = Symptom.objects.filter(patient=patient).first()
        # Crear el objeto HttpResponse con el tipo de contenido PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Paciente_{patient.first_name}_{patient.last_name}.pdf"'

        doc = SimpleDocTemplate(response, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        # Aquí agregaremos el contenido del PDF

        # Título Principal
        elements.append(Paragraph("Informe de paciente", styles['Title']))
        elements.append(Spacer(1, 12))
        
        # Nombre del Paciente
        elements.append(Paragraph(f"{patient.first_name} {patient.last_name}", styles['Heading2']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"RUT: {patient.rut or 'No especificado'}", styles['Heading2']))
        elements.append(Spacer(1, 12))
        # Información Personal
        elements.append(Paragraph("Información personal", styles['Heading3']))
        elements.append(Spacer(1, 12))

        personal_info = [
            f"<strong>Nombre:</strong> {patient.first_name} {patient.last_name}",
            f"<strong>Género:</strong> {patient.genre}",
            f"<strong>Fecha de nacimiento:</strong> {patient.birth_date.strftime('%d/%m/%Y')}",
            f"<strong>Edad:</strong> {patient.age} años",
            f"<strong>Dirección:</strong> {patient.address or 'No especificada'}",
            f"<strong>Teléfono:</strong> {patient.phone or 'No especificado'}",
            f"<strong>Email:</strong> {patient.email or 'No especificado'}",
            f"<strong>Región:</strong> {patient.region or 'No especificada'}",
            f"<strong>Ciudad:</strong> {patient.ciudad or 'No especificada'}",
            f"<strong>Comuna:</strong> {patient.comuna or 'No especificada'}",
            f"<strong>Centro de salud al que pertenece:</strong> {patient.centro_de_salud or 'No especificado'}",
        ]

        for info in personal_info:
            elements.append(Paragraph(info, styles['Normal']))
            elements.append(Spacer(1, 6))
        # Historial Médico
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Historial personal", styles['Heading3']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"{medical_history.personal_history or 'No hay historial personal'}", styles['Normal']))
        # Historial Familiar
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Historial familiar", styles['Heading3']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"{medical_history.family_history or 'No hay historial familiar'}", styles['Normal']))

        # Historial Clínico
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Historial clínico", styles['Heading3']))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"{medical_history.clinical_history or 'No hay historial clínico'}", styles['Normal']))
        # Síntomas
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Síntomas", styles['Heading3']))
        elements.append(Spacer(1, 12))

        symptoms = [
            f"<strong>Síntomas físicos:</strong> {symptoms.physical_symptoms or 'No hay síntomas físicos'}",
            f"<strong>Funcionamiento social:</strong> {symptoms.social_symptoms or 'No hay síntomas sociales'}",
            f"<strong>Síntomas emocionales:</strong> {symptoms.emotional_symptoms or 'No hay síntomas emocionales'}",
            f"<strong>Síntomas de comportamiento:</strong> {symptoms.behavioral_symptoms or 'No hay síntomas de comportamiento'}",
        ]

        for symptom in symptoms:
            elements.append(Paragraph(symptom, styles['Normal']))
            elements.append(Spacer(1, 6))
        # Hipótesis Diagnóstica
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Hipótesis diagnóstica", styles['Heading3']))
        elements.append(Spacer(1, 12))

        if diagnosis:
            elements.append(Paragraph(f"{diagnosis.diagnosis or 'Sin diagnóstico'}", styles['Normal']))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<strong>Detalles del diagnóstico:</strong> {diagnosis.details or 'No hay detalles'}", styles['Normal']))
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<strong>Diagnóstico adicional:</strong> {diagnosis.additional_diagnosis or 'No hay diagnósticos adicionales'}", styles['Normal']))
        else:
            elements.append(Paragraph("Sin diagnóstico", styles['Normal']))


        doc.build(elements)
        return response
    except Patient.DoesNotExist:
        return HttpResponse('Paciente no encontrado', status=404)
@csrf_exempt
def remove_patient_from_folder(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        patient_id = data.get('patient_id')

        try:
            patient = Patient.objects.get(id=patient_id)
            # Eliminar el paciente de la carpeta
            patient.folder = None
            patient.save()

            return JsonResponse({'success': True})
        except Patient.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Paciente no encontrado'})

    return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)

def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('inicio') 