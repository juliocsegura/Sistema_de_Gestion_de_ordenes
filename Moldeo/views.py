from django.shortcuts import render , redirect
from django.contrib import messages
import openpyxl
from django.db import transaction, models
from .models import OrdenMCM, ItemTecnico, ItemMesa, ItemCavidad,ItemCircuito,Moldes
from django.http import JsonResponse, HttpResponseBadRequest,HttpResponse
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
    if request.method == 'POST':
        numero_orden = request.POST.get('numero_orden')
        defecto_sap = request.POST.get('defecto_sap')
        defecto_real = request.POST.get('defecto_real')
        molde_form_id = request.POST.get('molde') # Recibimos el ID (String)

        lista_tecnicos = request.POST.getlist('tecnicos')
        lista_mesas = request.POST.getlist('mesas')
        lista_cavidades = request.POST.getlist('cavidades')
        lista_circuitos = request.POST.getlist('circuitos')

        # 1. PREPARAR LA INSTANCIA DEL MOLDE (Variable Temporal)
        molde_instancia = None # Iniciamos vacía
        
        if molde_form_id:
            try:
                # Buscamos el objeto real
                molde_instancia = Moldes.objects.get(pk=molde_form_id)
            except Moldes.DoesNotExist:
                molde_instancia = None

        # 2. VALIDACIÓN
        if not (numero_orden and defecto_sap and defecto_real and molde_instancia):
            messages.error(request, 'Error: Faltan campos obligatorios o el molde no es válido.')
            return render(request, 'Moldeo/registrar_orden.html')
       
        try:
            with transaction.atomic():
                # 3. CREAR LA ORDEN (Aquí es donde nace 'nueva_orden')
                # Pasamos la variable temporal 'molde_instancia' al constructor
                nueva_orden = OrdenMCM.objects.create(
                    numero_orden=numero_orden,
                    defecto_sap=defecto_sap,
                    defecto_real=defecto_real,
                    molde=molde_instancia # <--- ASIGNACIÓN CORRECTA
                )

                # 4. GUARDAR ITEMS RELACIONADOS
                for nombre in lista_tecnicos:
                    if nombre and nombre.strip():
                        ItemTecnico.objects.create(content_object=nueva_orden, nombre=nombre)

                for nombre in lista_mesas:
                    if nombre and nombre.strip():
                        ItemMesa.objects.create(content_object=nueva_orden, nombre=nombre)

                for nombre in lista_cavidades:
                    if nombre and nombre.strip():
                        ItemCavidad.objects.create(content_object=nueva_orden, nombre=nombre)
                
                for nombre in lista_circuitos:
                    if nombre and nombre.strip():
                        ItemCircuito.objects.create(content_object=nueva_orden, nombre=nombre)

            messages.success(request, f'Orden {numero_orden} registrada con éxito.')
            return redirect('Moldeo:panel_principal')
        
        except Exception as e:
            messages.error(request, f'Error al guardar la orden: {e}')
            return render(request, 'Moldeo/registrar_orden.html') # Regresa al form correcto, no a prueba.html
        
    # GET
    return render(request, 'Moldeo/prueba.html')


def registro_cho_view(request):
    return render (request, 'Moldeo/registro_cho.html') 
def registro_tpm_view(request):
    return render (request, 'Moldeo/registro_tpm.html') 

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
    circuitos_prefetch = models.Prefetch(
        'cavidades', 
        queryset=ItemCircuito.objects.order_by('id'), 
        to_attr='first_circuito'
    )
    
    # Obtenemos las órdenes (ej. las últimas 20)
    ordenes = OrdenMCM.objects.order_by('-fecha_creacion').prefetch_related(
        tecnicos_prefetch, mesas_prefetch, cavidades_prefetch, circuitos_prefetch
    )[:20]
    
    data = []
    for orden in ordenes:
        # Lógica segura para obtener el primer item o 'N/A'
        tecnico_obj = orden.first_tecnico[0] if orden.first_tecnico else None
        mesa_obj = orden.first_mesa[0] if orden.first_mesa else None
        cavidad_obj = orden.first_cavidad[0] if orden.first_cavidad else None
        circuito_obj = orden.first_circuito[0] if orden.first_circuito else None
        data.append({
            'id': orden.id, # ¡NUEVO! Necesario para el modal
            'numero_orden': orden.numero_orden,
            'molde': orden.molde.numero_molde if orden.molde else "N/A",
            'defecto_sap': orden.defecto_sap, # ¡NUEVO!
            'defecto_real': orden.defecto_real, # ¡NUEVO!
            'estado': orden.estado, # ¡NUEVO!
            'comentarios': orden.comentarios, # ¡NUEVO!
            
            'tecnico': tecnico_obj.nombre if tecnico_obj else 'N/A',
            'mesa': mesa_obj.nombre if mesa_obj else 'N/A',
            'cavidad': cavidad_obj.nombre if cavidad_obj else 'N/A',
            'circuito': circuito_obj.nombre if circuito_obj else 'N/A',
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
@require_http_methods(["GET"])   
def api_get_moldes(request):
    # Obtenemos todos los moldes
    moldes = Moldes.objects.all().values('id_molde', 'numero_molde')
    
    data = []
    for m in moldes:
        data.append({
            # Mapeamos los datos de tu DB a lo que espera el JS
            'molde': m['numero_molde'],   # El nombre visual (ej. 21-12345)
            'pk': m['id_molde'],          # El ID único de base de datos
                       
        })
    
    return JsonResponse(data, safe=False)

def exportar_ordenes_excel(request):
    # 1. Configuración de la respuesta HTTP para descargar archivo
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Reporte_Ordenes_MCM.xlsx"'

    # 2. Crear el libro de trabajo y la hoja
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ordenes MCM"

    # 3. Escribir los Encabezados
    headers = [
        'ID', 'Número Orden', 'Molde', 'Defecto SAP', 'Defecto Real', 
        'Estado', 'Fecha Creación', 'Técnicos', 'Mesas', 'Cavidades', 'Circuitos', 'Comentarios'
    ]
    ws.append(headers)

    # 4. Obtener los datos (Optimizados para evitar lentitud)
    ordenes = OrdenMCM.objects.select_related('molde').prefetch_related(
        'tecnicos', 'mesas', 'cavidades', 'circuitos'
    ).all().order_by('-fecha_creacion')

    # 5. Escribir las filas
    for orden in ordenes:
        # A. Formatear Molde (Manejando errores de referencia)
        if orden.molde:
            try:
                nombre_molde = orden.molde.numero_molde
            except:
                nombre_molde = f"Ref Rota ({orden.molde_id})"
        else:
            nombre_molde = "N/A"

        # B. Formatear Listas (Unir con comas: "Juan, Pedro")
        str_tecnicos = ", ".join([t.nombre for t in orden.tecnicos.all()])
        str_mesas = ", ".join([m.nombre for m in orden.mesas.all()])
        str_cavidades = ", ".join([c.nombre for c in orden.cavidades.all()])
        str_circuitos = ", ".join([c.nombre for c in orden.circuitos.all()])

        # C. Formatear Fecha (Sin zona horaria para que Excel no se queje)
        fecha_str = orden.fecha_creacion.strftime('%Y-%m-%d %H:%M')

        # D. Escribir la fila
        ws.append([
            orden.id,
            orden.numero_orden,
            nombre_molde,
            orden.defecto_sap,
            orden.defecto_real,
            orden.estado,
            fecha_str,
            str_tecnicos,
            str_mesas,
            str_cavidades,
            str_circuitos,
            orden.comentarios
        ])

    # 6. Guardar el libro en la respuesta
    wb.save(response)
    return response