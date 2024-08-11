from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('',views.inicio),
    #path('register/', views.register, name='register'),
    path('login/', views.inicio, name='login'),  # Puedes usar la misma vista si manejas todo en 'inicio'
    path('register/', views.inicio, name='register'), 
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('home/', views.home, name='home'), 
  
]
