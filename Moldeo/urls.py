from django.urls import path
from . import views

urlpatterns = [
  
    path('', views.panel_view, name='panel_principal'),
    path('registro/', views.Registrar_Orden_view, name='registrar_orden'),
    
]