# EOATS/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # La página principal (búsqueda de EOATs)
    path('', views.lista_eoats_view, name='lista_eoats'),
    
    # Las otras páginas
    path('bitacora/', views.bitacora_view, name='bitacora'),
    path('refacciones/', views.refacciones_view, name='refacciones'),
    path('entradas-salidas/', views.movimientos_view, name='movimientos_log'),
    path('movimientos/', views.movimientos_view, name='movimientos'),
    path('plan/', views.plan_view, name='plan_view'),
    path('plan/upload', views.upload_plan_view, name='upload_plan_file'),
    path('desarrollo/', views.desarrollo_view,name='desarrollo'),
    path('api/eoat/<int:eoat_id>/fotos/', views.get_eoat_fotos, name='api_get_eoat_fotos'),
    path('api/get_moldes/', views.get_moldes_api, name='api_get_moldes'),
]