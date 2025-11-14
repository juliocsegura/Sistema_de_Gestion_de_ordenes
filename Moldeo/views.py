from django.shortcuts import render , redirect
from django.contrib import messages
from django.db import transaction, models
from .models import OrdenMCM, ItemTecnico, ItemMesa, ItemCavidad
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods 
import json

# --- VISTA DEL PANEL PRINCIPAL (Dashboard) ---
def panel_view(request):
    """
    Renderiza el template principal. El template se encargará
    de llamar a la API para obtener los datos.
    """
    return render(request, 'Moldeo/panel_principal.html')

# --- VISTAS DE REGISTRO ---

def Registrar_Orden_view(request):
    """
    Vista genérica de registro. Redirige al formulario MCM
    o podría mostrar una página para elegir qué tipo de orden registrar.
    Por ahora, apunta al formulario MCM.
    """
    return render(request, 'Moldeo/registrar_orden.html')

@require_http_methods(["GET", "POST"])
def mcm_view(request):
    """ 
    Maneja el formulario de registro de órdenes MCM.
    GET: Muestra el formulario.
    POST: Procesa y guarda los datos de la orden.
    """
    
    # --- PROCESAMIENTO POST (Guardar Datos) ---
    if request.method == 'POST':
        numero_orden = request.POST.get('numero_orden')
        defecto_sap = request.POST.get('defecto_sap')
        defecto_real = request.POST.get('defecto_real')
        molde_form = request.POST.get('molde') 

        lista_tecnicos = request.POST.getlist('tecnicos')
        lista_mesas = request.POST.getlist('mesas')
        lista_cavidades = request.POST.getlist('cavidades')
        
        # Validación básica
        if not (numero_orden and defecto_sap and defecto_real and molde_form):
            messages.error(request, 'Error: Faltan campos obligatorios.')
            # Devolver al formulario con los datos ya llenos (pendiente)
            return render(request, 'Moldeo/registrar_orden.html')

        try:
            with transaction.atomic():
                # Crear la orden principal
                nueva_orden = OrdenMCM.objects.create(
                    numero_orden=numero_orden,
                    defecto_sap=defecto_sap,
                    defecto_real=defecto_real,
                    molde=molde_form
                    # El estado se pone 'Activa' por defecto (definido en el modelo)
                )

                # Guardar items relacionados
                for nombre_tecnico in lista_tecnicos:
                    if nombre_tecnico and nombre_tecnico.strip():
                        ItemTecnico.objects.create(content_object=nueva_orden, nombre=nombre_tecnico)

                for nombre_mesa in lista_mesas:
                    if nombre_mesa and nombre_mesa.strip():
                        ItemMesa.objects.create(content_object=nueva_orden, nombre=nombre_mesa)

                for nombre_cavidad in lista_cavidades:
                    if nombre_cavidad and nombre_cavidad.strip():
                        ItemCavidad.objects.create(content_object=nueva_orden, nombre=nombre_cavidad)
            
            messages.success(request, f'Orden {numero_orden} registrada con éxito.')
            # Redirigir al dashboard (panel_principal)
            return redirect('Moldeo:panel_principal')

        except Exception as e:
            messages.error(request, f'Error al guardar la orden: {e}')
            return render(request, 'Moldeo/prueba.html')

    # --- PETICIÓN GET (Mostrar Formulario) ---
    return render(request, 'Moldeo/prueba.html')


def registro_cho_view(request):
    return render (request, 'Moldeo/registro_cho.html') # Asumiendo que tienes este template
def registro_tpm_view(request):
    return render (request, 'Moldeo/registro_tpm.html') # Asumiendo que tienes este template

# --- VISTAS DE API ---

@require_http_methods(["GET"])
def api_ordenes_recientes_view(request):
    """
    API que devuelve las órdenes activas/recientes en formato JSON.
    Esta es la versión robusta y eficiente.
    """
    
    # Prefetch para cargar solo el primer item de cada relación
    tecnicos_prefetch = models.Prefetch(
        'tecnicos', 
        queryset=ItemTecnico.objects.order_by('id'), 
        to_attr='first_tecnico'
    )
    mesas_prefetch = models.Prefetch(
        'mesas', 
        queryset=ItemMesa.objects.order_by('id'), 
        to_attr='first_mesa'
    )
    cavidades_prefetch = models.Prefetch(
        'cavidades', 
        queryset=ItemCavidad.objects.order_by('id'), 
        to_attr='first_cavidad'
    )
    
    # Obtenemos las órdenes (ej. las últimas 20)
    ordenes = OrdenMCM.objects.order_by('-fecha_creacion').prefetch_related(
        tecnicos_prefetch, mesas_prefetch, cavidades_prefetch
    )[:20]
    
    data = []
    for orden in ordenes:
        # Lógica segura para obtener el primer item o 'N/A'
        tecnico_obj = orden.first_tecnico[0] if orden.first_tecnico else None
        mesa_obj = orden.first_mesa[0] if orden.first_mesa else None
        cavidad_obj = orden.first_cavidad[0] if orden.first_cavidad else None
        
        data.append({
            'id': orden.id, # ¡NUEVO! Necesario para el modal
            'numero_orden': orden.numero_orden,
            'molde': orden.molde,
            'defecto_sap': orden.defecto_sap, # ¡NUEVO!
            'defecto_real': orden.defecto_real, # ¡NUEVO!
            'estado': orden.estado, # ¡NUEVO!
            'comentarios': orden.comentarios, # ¡NUEVO!
            
            'tecnico': tecnico_obj.nombre if tecnico_obj else 'N/A',
            'mesa': mesa_obj.nombre if mesa_obj else 'N/A',
            'cavidad': cavidad_obj.nombre if cavidad_obj else 'N/A',
            
            'fecha_creacion_iso': orden.fecha_creacion.isoformat(),
        })
    
    return JsonResponse({'ordenes': data})


@require_http_methods(["POST"])
@transaction.atomic
def api_actualizar_orden_view(request, orden_id):
    """
    API para manejar las actualizaciones del modal (Pausar, Finalizar, Comentar).
    """
    try:
        orden = OrdenMCM.objects.get(id=orden_id)
        
        # Seguridad: no permitir cambios en órdenes finalizadas
        if orden.estado == OrdenMCM.ESTADO_FINALIZADA:
             return JsonResponse({'message': 'Error: La orden ya está finalizada.'}, status=400)

        data = json.loads(request.body)
        
        campos_actualizados = []

        # Actualizar estado si se proporcionó
        if 'estado' in data:
            nuevo_estado = data['estado']
            if nuevo_estado in [OrdenMCM.ESTADO_ACTIVA, OrdenMCM.ESTADO_PAUSADA, OrdenMCM.ESTADO_FINALIZADA]:
                orden.estado = nuevo_estado
                campos_actualizados.append('estado')
            else:
                return JsonResponse({'message': f'Error: Estado "{nuevo_estado}" no válido.'}, status=400)
        
        # Actualizar comentarios si se proporcionaron
        if 'comentarios' in data:
            orden.comentarios = data['comentarios']
            campos_actualizados.append('comentarios')
            
        if not campos_actualizados:
             return JsonResponse({'message': 'Error: No se proporcionaron datos para actualizar.'}, status=400)

        orden.save()
        
        return JsonResponse({
            'success': True, 
            'message': f'Orden actualizada ({", ".join(campos_actualizados)}).',
            'orden_id': orden.id,
            'nuevo_estado': orden.estado
        })

    except OrdenMCM.DoesNotExist:
        return JsonResponse({'message': 'Error: Orden no encontrada.'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'message': 'Error: JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Error interno del servidor: {e}'}, status=500)