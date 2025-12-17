from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json

# --- FUNCIONES DE VERIFICACIÓN ---
def es_lider(user):
    return user.groups.filter(name='Lideres').exists() or user.is_superuser

def es_tecnico(user):
    return user.groups.filter(name='Tecnicos').exists()

# --- VISTA DE REDIRECCIÓN (Login Success) ---
@login_required
def redireccion_inicio(request):
    usuario = request.user

    # 1. Si es LÍDER o ADMIN -> Va al Dashboard Principal
    if es_lider(usuario):
        # CORREGIDO: No mandar a 'index' (que es el login), mandar al Panel
        return redirect('index') 
    
    # 2. Si es TÉCNICO -> Va a la lista SAP (según tu código reciente)
    elif es_tecnico(usuario):
        return redirect('Moldeo:lista_sap')
        
    else:
        # Si el usuario no tiene grupo asignado
        return render(request, 'desarrollo.html')

# --- APIS Y LOGIN ---

@require_http_methods(["POST"])
def check_password_status(request):
    try:
        data = json.loads(request.body)
        username = data.get('username')
        
        try:
            user = User.objects.get(username=username)
            return JsonResponse({
                'exists': True, 
                'needs_password': user.has_usable_password()
            })
        except User.DoesNotExist:
            return JsonResponse({'exists': False})
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

def custom_login_view(request):
    # Si ya entró, no mostrar login, mandar a redirección
    if request.user.is_authenticated:
        return redirect('inicio_redireccion')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            user = User.objects.get(username=username)
            
            # CASO A: Sin contraseña
            if not user.has_usable_password():
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('inicio_redireccion')
            
            # CASO B: Con contraseña
            else:
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('inicio_redireccion')
                else:
                    return render(request, 'registration/login.html', {'error': 'Contraseña incorrecta', 'step': 2, 'username': username})

        except User.DoesNotExist:
            return render(request, 'registration/login.html', {'error': 'Usuario no encontrado'})

    return render(request, 'registration/login.html')