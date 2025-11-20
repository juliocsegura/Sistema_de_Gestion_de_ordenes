from django.urls import path
from . import views

urlpatterns = [
  
    path('', views.panel_view, name='panel_principal'),
    path('registro/', views.Registrar_Orden_view, name='registrar_orden'),
    path('registro_mcm/', views.mcm_view, name='registrar_mcm'),
    path('registro_cho/', views.registro_cho_view, name='registrar_cho'),
    path('registro_tpm/', views.registro_tpm_view, name='registrar_tpm'),
    path('api/ordenes-recientes/', views.api_ordenes_recientes_view, name='api_ordenes_recientes'),
    path('api/orden/<int:orden_id>/actualizar/', views.api_actualizar_orden_view, name='api_actualizar_orden'),
    path('exportar-excel/', views.exportar_ordenes_excel, name='exportar_excel'),
    path('api/get-moldes/', views.api_get_moldes, name='api_get_moldes'),
    # --- Rutas Placeholder ---
    # (Añade las vistas para estas rutas que ya tienes en base.html)
    path('ordenes/', views.panel_view, name='ordenes_lista'), # Temporal
    path('ordenes/buscar/', views.panel_view, name='ordenes_buscar'), # Temporal
    path('ordenes/reportes/', views.panel_view, name='ordenes_reportes'), # Temporal
    path('clientes/', views.panel_view, name='clientes_lista'), # Temporal
    path('configuracion/', views.panel_view, name='configuracion'), # Temporal

]