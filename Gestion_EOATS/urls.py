"""
URL configuration for Gestion_EOATS project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path , include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from Moldeo import views as vistas_moldeo
from . import views as vistas_generales

urlpatterns = [
    path('admin/', admin.site.urls),
    path('eoats/', include('EOATS.urls')),
    path('index/', TemplateView.as_view(template_name='index.html'), name='index'),
    path('moldeo/', include(('Moldeo.urls', 'Moldeo'), namespace='Moldeo')),
   # --- RUTAS DE AUTENTICACIÓN (LOGIN / LOGOUT) ---
    # --- CAMBIO AQUÍ: Usamos nuestra vista personalizada ---
    path('accounts/login/', vistas_generales.custom_login_view, name='login'),
    
    # API para que el JavaScript pregunte
    path('api/check-user/', vistas_generales.check_password_status, name='api_check_user'),
    # Logout: Cierra sesión y manda al login de nuevo
    # Nota: Desde Django 5.0, LogoutView prefiere POST, pero para simplificar usamos next_page en settings
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # --- RUTAS DE APLICACIÓN ---
    path('moldeo/', include(('Moldeo.urls', 'Moldeo'), namespace='Moldeo')),
    
    # --- REDIRECCIÓN INICIAL (Tu lógica de roles) ---
    path('inicio/', vistas_generales.redireccion_inicio, name='inicio_redireccion'),
    
    # Si entran a la raíz (localhost:8000), mándalos al login directamente
    path('', vistas_generales.custom_login_view,name='login'), 
    
    path('panel/', vistas_moldeo.panel_view, name='panel_principal'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)