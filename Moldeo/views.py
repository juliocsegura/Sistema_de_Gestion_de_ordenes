from django.shortcuts import render , redirect, get_object_or_404
from django.contrib import messages
import openpyxl
from django.db.models import Q
from django.db import transaction, models
from .models import Moldmakers,OrdenMCM, OrdenCHO,OrdenTPM,OrdenPREP, ItemTecnico, ItemMesa, ItemCavidad,ItemCircuito,Moldes,OrdenSAP
from django.http import JsonResponse, HttpResponseBadRequest,HttpResponse
from django.views.decorators.http import require_http_methods 
from django.utils import timezone
import json
from itertools import chain
from operator import attrgetter

# --- VISTA DEL PANEL PRINCIPAL (Dashboard) ---
def panel_view(request):
    """
    Renderiza el template principal. El template se encargará
    de llamar a la API para obtener los datos.
    """
    return render(request, 'Moldeo/panel_principal.html')

# --- VISTAS DE REGISTRO ---

def Registrar_Orden_view(request):
   lista_tecnicos = Moldmakers.objects.all().order_by('nombre')
   ctx = {
        'pre_orden': request.GET.get('orden_sap', ''),
        'pre_defecto': request.GET.get('defecto', ''),
        'pre_molde': request.GET.get('molde', ''),
        'moldmakers': lista_tecnicos
    }
   
   return render(request, 'Moldeo/registrar_orden.html', ctx)

def Orden_en_curso_view(request):
   
    # 1. Buscamos los técnicos (Asegúrate de tener importado el modelo Moldmakers)
    lista_tecnicos = Moldmakers.objects.all().order_by('nombre')
    
    context = {
        'moldmakers': lista_tecnicos  # <--- Esto es lo que faltaba
    }
    
    # 2. Enviamos el contexto al renderizar
    return render(request, 'Moldeo/Ordenes_en_curso.html', context)
def btn_status_ordenmcm_view(request):
   context = {
        'pre_orden': request.GET.get('numero_orden', ''),
        'pre_defecto': request.GET.get('defecto_sap', ''),
        'pre_molde': request.GET.get('molde', '')
    }
    # Renderizamos el template de los botones
   return render(request, 'Moldeo/btn_status_mcm.html', context)


@require_http_methods(["GET", "POST"])
def mcm_view(request):
    status_actual = request.POST.get('statusmcm') or request.GET.get('status', '')
    tipo_mntn= 'MCM'
    pre_orden = request.GET.get('numero_orden', '')
    pre_defecto = request.GET.get('defecto_sap', '')
    pre_molde_nombre = request.GET.get('molde', '')
    tecnicos_list = Moldmakers.objects.all().order_by('nombre')
    pre_molde_pk = ''
    # Si viene un nombre de molde (ej: 21-5045), buscamos su ID real para el input oculto
    if pre_molde_nombre:
        try:
            m = Moldes.objects.filter(numero_molde=pre_molde_nombre).first()
            if m:
                pre_molde_pk = m.id_molde
        except:
            pass
    if request.method == 'POST':
        numero_orden = request.POST.get('numero_orden')
        defecto_sap = request.POST.get('defecto_sap')
        defecto_real = request.POST.get('defecto_real')
        molde_form_id = request.POST.get('molde') # Recibimos el ID (String)
        lista_tecnicos_ids = request.POST.getlist('tecnicos')
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
                    molde=molde_instancia, # <--- ASIGNACIÓN CORRECTA
                    status= status_actual,
                    tipo_mntn= tipo_mntn,
                )

                # 4. GUARDAR ITEMS RELACIONADOS
                for tec_id in lista_tecnicos_ids:
                    if tec_id:
                        nombre_a_guardar = tec_id # Por defecto (si falla la búsqueda)
                        try:
                            # Buscamos el nombre usando el ID que viene del HTML
                            tec_obj = Moldmakers.objects.get(id_mold_m=tec_id)
                            nombre_a_guardar = tec_obj.nombre
                        except:
                            pass # Si no lo encuentra, guarda el ID como string
                        
                        ItemTecnico.objects.create(content_object=nueva_orden, nombre=nombre_a_guardar)
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
            return redirect('Moldeo:ordenes_en_curso')
        
        except Exception as e:
            messages.error(request, f'Error al guardar la orden: {e}')
            return render(request, 'Moldeo/prueba.html',{'moldmakers': tecnicos_list}) 
    context = {
        'status_actual': status_actual,
        'tipo_mntn' : tipo_mntn,
        'pre_orden': pre_orden,
        'pre_defecto': pre_defecto,
        'pre_molde_nombre': pre_molde_nombre,
        'pre_molde_pk': pre_molde_pk,
        'moldmakers': tecnicos_list

        }
    # GET
    return render(request, 'Moldeo/prueba.html',context) # html temporal


def registro_cho_view(request):
    return render (request, 'Moldeo/registro_cho.html') 
def registro_tpm_view(request):
    return render (request, 'Moldeo/registro_tpm.html') 

# --- VISTAS DE API ---

@require_http_methods(["GET"])
def api_ordenes_recientes_view(request):
    # Prefetch
    
    p_mesas = models.Prefetch('mesas', queryset=ItemMesa.objects.order_by('id'), to_attr='first_mesa')
    p_cavidades = models.Prefetch('cavidades', queryset=ItemCavidad.objects.order_by('id'), to_attr='first_cavidad')
    p_circuitos = models.Prefetch('circuitos', queryset=ItemCircuito.objects.order_by('id'), to_attr='first_circuito')
    p_tecnicos = models.Prefetch('tecnicos', queryset=ItemTecnico.objects.order_by('-activo', 'id'))
    # Consulta a TODAS las tablas
    qs_mcm = OrdenMCM.objects.exclude(estado='Finalizada').select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()
    qs_cho = OrdenCHO.objects.exclude(estado='Finalizada').select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()
    qs_tpm = OrdenTPM.objects.exclude(estado='Finalizada').select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()
    qs_prep = OrdenPREP.objects.exclude(estado='Finalizada').select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()

    # El resto de la función sigue igual...

    todas = list(chain(qs_mcm, qs_cho, qs_tpm, qs_prep))
    todas.sort(key=attrgetter('fecha_creacion'), reverse=True)
    ordenes = todas[:50]
    
    data = []
    for orden in ordenes:
        tecnicos_data = []
        nombres_visibles = [] # Para la celda de la tabla (solo mostramos los activos)
        
        for t in orden.tecnicos.all():
            tecnicos_data.append({
                'id': t.id,
                'nombre': t.nombre,
                'activo': t.activo,
                'fecha_fin': t.fecha_fin.strftime('%H:%M') if t.fecha_fin else None
            })
            if t.activo:
                nombres_visibles.append(t.nombre)
        
        # String para la tabla (Ej: "Juan, Pedro")
        tecnico_str = ", ".join(nombres_visibles) if nombres_visibles else "Sin técnico activo"
        mesa_obj = orden.first_mesa[0] if orden.first_mesa else None
        cavidad_obj = orden.first_cavidad[0] if orden.first_cavidad else None
        circuito_obj = orden.first_circuito[0] if orden.first_circuito else None
        fecha_local = timezone.localtime(orden.fecha_creacion)
        fecha_str = fecha_local.strftime('%d/%m/%Y %H:%M')
        if orden.molde:
            try: nombre_molde = orden.molde.numero_molde
            except: nombre_molde = "Ref Error"
        else: nombre_molde = "N/A"

        data.append({
            'id': orden.id,
            'numero_orden': orden.numero_orden,
            'status': orden.status,         # 203, 204
            'tipo': orden.tipo_mntn,        # MCM, CHO            
            'fecha_creacion': fecha_str,
            'molde': nombre_molde,
            'defecto_sap': getattr(orden, 'defecto_sap', '-'),
            'defecto_real': getattr(orden, 'defecto_real', '-'),
            'estado': orden.estado, 
            'comentarios': orden.comentarios, 
            'tecnico': tecnico_str,       # Para mostrar en la tabla principal
            'tecnicos_lista': tecnicos_data,
            'mesa': mesa_obj.nombre if mesa_obj else 'N/A',
            'cavidad': cavidad_obj.nombre if cavidad_obj else 'N/A',
            'circuito': circuito_obj.nombre if circuito_obj else 'N/A',
            'fecha_creacion_iso': orden.fecha_creacion.isoformat(),
            'duracion_segundos': getattr(orden, 'duracion_segundos', 0),
            'ultima_actualizacion_iso': orden.ultima_actualizacion.isoformat() if hasattr(orden, 'ultima_actualizacion') and orden.ultima_actualizacion else None,
        })
    
    return JsonResponse({'ordenes': data})
def historial_finalizadas_view(request):
    def format_duration(seconds):
        if not seconds: return "00:00:00"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # Traemos todos los técnicos, mesas, etc.
    p_tecnicos = models.Prefetch('tecnicos', queryset=ItemTecnico.objects.order_by('id'))
    p_mesas = models.Prefetch('mesas', queryset=ItemMesa.objects.order_by('id'))
    
    # Consultamos las órdenes finalizadas
    qs_mcm = OrdenMCM.objects.filter(estado='Finalizada').select_related('molde').prefetch_related(p_tecnicos, p_mesas).all()
    # (Agrega aquí tus otros modelos: qs_cho, qs_tpm, etc.)

    todas = list(chain(qs_mcm)) # Agrega las otras listas
    todas.sort(key=attrgetter('ultima_actualizacion'), reverse=True)
    
    datos = []
    for orden in todas:
        # 1. Construir lista completa de técnicos para el modal
        lista_tecnicos = []
        nombres_simples = []
        for t in orden.tecnicos.all():
            lista_tecnicos.append({
                'nombre': t.nombre,
                'activo': t.activo,
                'inicio': t.fecha_inicio.strftime('%d/%m %H:%M') if t.fecha_inicio else '-',
                'fin': t.fecha_fin.strftime('%d/%m %H:%M') if t.fecha_fin else 'Activo'
            })
            if t.activo: nombres_simples.append(t.nombre) # Solo para la vista rápida de la tabla
        
        # Si no hay activos (porque finalizó), mostramos el último que estuvo
        tecnico_tabla = nombres_simples[0] if nombres_simples else (lista_tecnicos[-1]['nombre'] if lista_tecnicos else 'N/A')

        fecha_fin = orden.ultima_actualizacion
        
        datos.append({
            'id': orden.id,
            'tipo': orden.tipo_mntn, # Importante para imprimir
            'numero_orden': orden.numero_orden,
            'molde': orden.molde.numero_molde if orden.molde else 'N/A',
            'defecto': getattr(orden, 'defecto_sap', '-'),
            'defecto_real': getattr(orden, 'defecto_real', '-'), # Agregado para el modal
            'tecnico': tecnico_tabla,
            'lista_tecnicos': lista_tecnicos, # Lista completa para el modal
            'mesa': orden.mesas.first().nombre if orden.mesas.exists() else 'N/A',
            'fecha_inicio': orden.fecha_creacion,
            'fecha_fin': fecha_fin,
            'duracion_fmt': format_duration(orden.duracion_segundos),
            'comentarios': orden.comentarios
        })

    return render(request, 'Moldeo/ordenes_finalizadas.html', {'ordenes': datos})

@require_http_methods(["POST"])
@transaction.atomic
def api_actualizar_orden_view(request, orden_id):
    try:
        data = json.loads(request.body)
        orden = None
        
        # Buscamos en todas las tablas
        for Modelo in [OrdenMCM, OrdenCHO, OrdenTPM, OrdenPREP]:
            try:
                orden = Modelo.objects.get(id=orden_id)
                break 
            except Modelo.DoesNotExist:
                continue
        
        if not orden: return JsonResponse({'message': 'Orden no encontrada.'}, status=404)

        if 'estado' in data:
            nuevo_estado = data['estado']
            ahora = timezone.now()

            if orden.estado == OrdenMCM.ESTADO_ACTIVA and nuevo_estado != OrdenMCM.ESTADO_ACTIVA:
                if orden.ultima_actualizacion:
                    delta = (ahora - orden.ultima_actualizacion).total_seconds()
                    orden.duracion_segundos += int(delta)
            elif orden.estado != OrdenMCM.ESTADO_ACTIVA and nuevo_estado == OrdenMCM.ESTADO_ACTIVA:
                orden.ultima_actualizacion = ahora

            orden.estado = nuevo_estado
            orden.save()
        
        if 'comentarios' in data:
            orden.comentarios = data['comentarios']
            orden.save()

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'message': str(e)}, status=500)
def api_get_moldes(request):

    # Obtenemos todos los moldes

    moldes = Moldes.objects.all().values('id_molde', 'numero_molde')

   

    data = []

    for m in moldes:

        data.append({

            # Mapea los datos de tu DB a lo que espera el JS

            'molde': m['numero_molde'],   # El nombre visual (ej. 21-12345)

            'pk': m['id_molde'],          # El ID único de base de datos

                       

        })

   

    return JsonResponse(data, safe=False)

def exportar_ordenes_excel(request):
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="Reporte_Ordenes_General.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ordenes General"

    headers = [
        'Tipo (Mntn)', 'ID BD', 'Número Orden', 'Status', 'Molde', 
        'Defecto SAP', 'Defecto Real', 'Estado', 'Fecha Creación', 
        'Técnicos', 'Mesas', 'Cavidades', 'Circuitos', 'Comentarios'
    ]
    ws.append(headers)

    # Consultar Todo
    qs_mcm = OrdenMCM.objects.select_related('molde').prefetch_related('tecnicos', 'mesas', 'cavidades', 'circuitos').all()
    qs_cho = OrdenCHO.objects.select_related('molde').prefetch_related('tecnicos', 'mesas', 'cavidades', 'circuitos').all()
    qs_tpm = OrdenTPM.objects.select_related('molde').prefetch_related('tecnicos', 'mesas', 'cavidades', 'circuitos').all()
    qs_prep = OrdenPREP.objects.select_related('molde').prefetch_related('tecnicos', 'mesas', 'cavidades', 'circuitos').all()

    todas = list(chain(qs_mcm, qs_cho, qs_tpm, qs_prep))
    todas.sort(key=attrgetter('fecha_creacion'), reverse=True)

    for orden in todas:
        if orden.molde:
            try: nombre_molde = orden.molde.numero_molde
            except: nombre_molde = "Ref Error"
        else: nombre_molde = "N/A"

        str_tecnicos = ", ".join([t.nombre for t in orden.tecnicos.all()])
        str_mesas = ", ".join([m.nombre for m in orden.mesas.all()])
        str_cavidades = ", ".join([c.nombre for c in orden.cavidades.all()])
        str_circuitos = ", ".join([c.nombre for c in orden.circuitos.all()])
        fecha_local = timezone.localtime(orden.fecha_creacion)
        fecha_str = fecha_local.strftime('%Y-%m-%d %H:%M')

        ws.append([
            orden.tipo_mntn,            
            orden.id,
            orden.numero_orden,
            orden.status,               
            nombre_molde,
            getattr(orden, 'defecto_sap', '-'),
            getattr(orden, 'defecto_real', '-'),
            orden.estado,
            fecha_str,
            str_tecnicos,
            str_mesas,
            str_cavidades,
            str_circuitos,
            orden.comentarios
        ])

    wb.save(response)
    return response

def importar_sap_view(request):
    if request.method == 'POST' and request.FILES.get('archivo_sap'):
        excel_file = request.FILES['archivo_sap']
        
        # Validación simple de extensión
        if not excel_file.name.endswith('.xlsx'):
            messages.error(request, 'Error: El archivo debe ser un Excel (.xlsx)')
            return render(request, 'Moldeo/importar_sap.html')

        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            
            # Buscamos "Sheet1" o usamos la primera hoja activa
            if 'Sheet1' in wb.sheetnames:
                ws = wb['Sheet1']
            else:
                ws = wb.active

            # Obtener encabezados de la fila 1 para saber en qué columna está cada dato
            headers = {}
            for cell in ws[1]: # Iterar la primera fila
                if cell.value:
                    headers[str(cell.value).strip()] = cell.column - 1 # Guardamos el índice (0, 1, 2...)

            # Verificar que existan las columnas necesarias
            required_cols = ['Order', 'Description', 'Work center', 'Equipment']
            if not all(col in headers for col in required_cols):
                messages.error(request, f'Error: Faltan columnas requeridas. Se busca: {required_cols}')
                return render(request, 'Moldeo/importar_sap.html')

            # Leer los datos (desde la fila 2)
            count = 0
            registros_nuevos = []
            
            # Iteramos las filas
            for row in ws.iter_rows(min_row=2, values_only=True):
                order_val = row[headers['Order']]
                
                # Si no hay número de orden, saltamos la fila
                if not order_val:
                    continue

                # Usamos update_or_create para actualizar si ya existe o crear si es nuevo
                OrdenSAP.objects.update_or_create(
                    order=str(order_val),
                    defaults={
                        'description': row[headers['Description']],
                        'work_center': row[headers['Work center']],
                        'equipment': str(row[headers['Equipment']]) if row[headers['Equipment']] else ''
                    }
                )
                count += 1

            messages.success(request, f'Éxito: Se procesaron {count} órdenes de SAP correctamente.')
            return redirect('Moldeo:panel_principal') # O a donde prefieras regresar

        except Exception as e:
            messages.error(request, f'Error al procesar el archivo: {e}')

    return render(request, 'Moldeo/importar_sap.html')
def lista_sap_view(request):
    # Capturamos lo que el usuario escribe en el buscador
    busqueda = request.GET.get('q', '')
    
   # PASO 1: Identificar qué órdenes YA están registradas en el sistema.
    # Obtenemos una lista simple de los números de orden de MCM (y otras si aplica)
    # values_list('numero_orden', flat=True) nos devuelve algo como ['1001', '1002', '1005']
    ordenes_registradas = OrdenMCM.objects.values_list('numero_orden', flat=True)
    
    # Si también usas números SAP en CHO, TPM, etc, puedes sumarlos:
    # ids_cho = OrdenCHO.objects.values_list('numero_orden', flat=True)
    # ordenes_registradas = list(chain(ids_mcm, ids_cho)) # Necesitarías importar chain

    # PASO 2: Consultar OrdenSAP EXCLUYENDO (.exclude) las que ya están registradas
    # Esto le dice a la DB: "Dame todas las SAP, excepto las que su 'order' esté en la lista 'ordenes_registradas'"
    ordenes = OrdenSAP.objects.exclude(order__in=ordenes_registradas)

    # PASO 3: Aplicar el buscador del usuario sobre la lista ya filtrada
    if busqueda:
        ordenes = ordenes.filter(
            Q(order__icontains=busqueda) |
            Q(description__icontains=busqueda) |
            Q(equipment__icontains=busqueda) |
            Q(work_center__icontains=busqueda)
        )
    else:
        # Si no busca nada, mostramos las primeras 50
        ordenes = ordenes[:100]

    context = {
        'ordenes': ordenes,
        'busqueda': busqueda
    }
    return render(request, 'Moldeo/lista_sap.html', context)
def imprimir_formato_view(request, orden_id, tipo):
    # Buscamos la orden según el tipo
    orden = None
    if tipo == 'MCM':
        orden = OrdenMCM.objects.get(id=orden_id)
    elif tipo == 'TPM':
        orden = OrdenTPM.objects.get(id=orden_id)
    # ... agregar otros tipos si es necesario ...

    context = {
        'orden': orden,
        # Pasamos la fecha actual para la impresión si se requiere
        'fecha_impresion': timezone.now()
    }
    return render(request, 'Moldeo/imprimir_formato.html', context)
@require_http_methods(["POST"])
def api_gestionar_tecnicos(request, orden_id):
    try:
        data = json.loads(request.body)
        accion = data.get('accion') # 'agregar' o 'baja'
        
        # Buscamos la orden (MCM por defecto, adapta si usas otros modelos)
        orden = OrdenMCM.objects.get(id=orden_id) 

        if accion == 'agregar':
            nombre_tecnico = data.get('nombre')
            # Creamos el técnico asociado a esta orden
            ItemTecnico.objects.create(content_object=orden, nombre=nombre_tecnico, activo=True)
            mensaje = f"{nombre_tecnico} agregado."

        elif accion == 'baja':
            item_id = data.get('item_id')
            tecnico_item = ItemTecnico.objects.get(id=item_id)
            
            # Lo marcamos como inactivo y ponemos hora de salida
            tecnico_item.activo = False
            tecnico_item.fecha_fin = timezone.now()
            tecnico_item.save()
            mensaje = "Técnico dado de baja."

        return JsonResponse({'success': True, 'message': mensaje})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)