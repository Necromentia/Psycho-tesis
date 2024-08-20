from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User


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
                return redirect('home')  # Redirige a la página de inicio o la que prefieras
            else:
                login_error = 'Nombre de usuario o contraseña incorrectos'
        
        elif 'register' in request.POST:
            # Proceso de registro
            username = request.POST['new_username']
            password = request.POST['new_password']
            if User.objects.filter(username=username).exists():
                register_error = 'El nombre de usuario ya está en uso'
            else:
                User.objects.create_user(username=username, password=password)
                return redirect('inicio')  # Redirige al login después de crear el usuario

    return render(request, 'index.html', {'login_error': login_error, 'register_error': register_error})

def home(request):
    return render(request, 'home.html')
