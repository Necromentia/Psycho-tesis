from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('',views.inicio,name='inicio'),
    #path('register/', views.register, name='register'),
    #path('login/', views.inicio, name='login'),
    path('home/', views.home, name='home'), 
    path('create_folder/', views.create_folder, name='create_folder'),
    path('rename_folder/', views.rename_folder, name='rename_folder'),
    path('delete_folder/', views.delete_folder, name='delete_folder'),
    path('get_patients_by_folder/<int:folder_id>/', views.get_patients_by_folder, name='get_patients_by_folder'),
    path('get_patient/<int:patient_id>/', views.get_patient, name='get_patient'),
    path('update_patient/<int:patient_id>/', views.update_patient, name='update_patient'),
    path('remove_patient_from_folder/', views.remove_patient_from_folder, name='remove_patient_from_folder'),
    path('get_recent_patients/', views.get_recent_patients, name='get_recent_patients'),
    path('update_diagnosis/<int:patient_id>/', views.update_diagnosis, name='update_diagnosis'),
    path('ingreso-paciente/', views.register_patient, name='ingreso-paciente'),
    path('edit_patient/<int:patient_id>/', views.edit_patient, name='edit_patient'),
    path('move_patient_to_trash/', views.move_patient_to_trash, name='move_patient_to_trash'),
    path('restore_patient_from_trash/', views.restore_patient_from_trash, name='restore_patient_from_trash'),
    path('download_patient_pdf/<int:patient_id>/', views.download_patient_pdf, name='download_patient_pdf'),
    path('get_trash_folder_id/', views.get_trash_folder_id, name='get_trash_folder_id'),
    path('chat/', views.chat_view, name='chat'),
    path('assign_patient_to_folder/', views.assign_patient_to_folder, name='assign_patient_to_folder'),

    path('get_response/', views.get_response, name='get_response'),
    path('logout/', views.user_logout, name='logout'),
  
]
