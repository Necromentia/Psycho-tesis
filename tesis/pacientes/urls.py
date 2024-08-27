from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('',views.inicio,name='inicio'),
    #path('register/', views.register, name='register'),
    #path('login/', views.inicio, name='login'),
    path('home/', views.home, name='home'), 
    path('create_or_edit_folder/', views.create_or_edit_folder, name='create_or_edit_folder'),
    path('delete_folder/', views.delete_folder, name='delete_folder'),
    path('get_patients_by_folder/<int:folder_id>/', views.get_patients_by_folder, name='get_patients_by_folder'),
    path('update_diagnosis/', views.update_diagnosis, name='update_diagnosis'),
    path('ingreso-paciente/', views.register_patient, name='ingreso-paciente'),
    path('chat/', views.chat_view, name='chat'),
    path('get_response/', views.get_response, name='get_response'),
    path('logout/', views.user_logout, name='logout'),
  
]
