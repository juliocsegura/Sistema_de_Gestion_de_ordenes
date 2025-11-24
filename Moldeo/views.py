from django.shortcuts import render , redirect
from django.contrib import messages
import openpyxl
from django.db.models import Q
from django.db import transaction, models
from .models import OrdenMCM, OrdenCHO,OrdenTPM,OrdenPREP, ItemTecnico, ItemMesa, ItemCavidad,ItemCircuito,Moldes,OrdenSAP
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
   ctx = {
        'pre_orden': request.GET.get('orden_sap', ''),
        'pre_defecto': request.GET.get('defecto', ''),
        'pre_molde': request.GET.get('molde', '')
    }
   
   return render(request, 'Moldeo/registrar_orden.html', ctx)

def Orden_en_curso_view(request):
   
    return render(request, 'Moldeo/Ordenes_en_curso.html')
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
                    molde=molde_instancia, # <--- ASIGNACIÓN CORRECTA
                    status= status_actual,
                    tipo_mntn= tipo_mntn,
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
            return redirect('Moldeo:ordenes_en_curso')
        
        except Exception as e:
            messages.error(request, f'Error al guardar la orden: {e}')
            return render(request, 'Moldeo/prueba.html') 
    context = {
        'status_actual': status_actual,
        'tipo_mntn' : tipo_mntn,
        'pre_orden': pre_orden,
        'pre_defecto': pre_defecto,
        'pre_molde_nombre': pre_molde_nombre,
        'pre_molde_pk': pre_molde_pk
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
    p_tecnicos = models.Prefetch('tecnicos', queryset=ItemTecnico.objects.order_by('id'), to_attr='first_tecnico')
    p_mesas = models.Prefetch('mesas', queryset=ItemMesa.objects.order_by('id'), to_attr='first_mesa')
    p_cavidades = models.Prefetch('cavidades', queryset=ItemCavidad.objects.order_by('id'), to_attr='first_cavidad')
    p_circuitos = models.Prefetch('circuitos', queryset=ItemCircuito.objects.order_by('id'), to_attr='first_circuito')
    
    # Consulta a TODAS las tablas
    qs_mcm = OrdenMCM.objects.select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()
    qs_cho = OrdenCHO.objects.select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()
    qs_tpm = OrdenTPM.objects.select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()
    qs_prep = OrdenPREP.objects.select_related('molde').prefetch_related(p_tecnicos, p_mesas, p_cavidades, p_circuitos).all()

    todas = list(chain(qs_mcm, qs_cho, qs_tpm, qs_prep))
    todas.sort(key=attrgetter('fecha_creacion'), reverse=True)
    ordenes = todas[:50]
    
    data = []
    for orden in ordenes:
        tecnico_obj = orden.first_tecnico[0] if orden.first_tecnico else None
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
            'tecnico': tecnico_obj.nombre if tecnico_obj else 'N/A',
            'mesa': mesa_obj.nombre if mesa_obj else 'N/A',
            'cavidad': cavidad_obj.nombre if cavidad_obj else 'N/A',
            'circuito': circuito_obj.nombre if circuito_obj else 'N/A',
            'fecha_creacion_iso': orden.fecha_creacion.isoformat(),
            'duracion_segundos': getattr(orden, 'duracion_segundos', 0),
            'ultima_actualizacion_iso': orden.ultima_actualizacion.isoformat() if hasattr(orden, 'ultima_actualizacion') and orden.ultima_actualizacion else None,
        })
    
    return JsonResponse({'ordenes': data})


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
    
    if busqueda:
        # Filtramos por Orden, Descripción o Equipo
        ordenes = OrdenSAP.objects.filter(
            Q(order__icontains=busqueda) |
            Q(description__icontains=busqueda) |
            Q(equipment__icontains=busqueda) |
            Q(work_center__icontains=busqueda)
        )[:100] # Limitamos a 100 resultados para que sea rápido
    else:
        # Si no busca nada, mostramos las primeras 50
        ordenes = OrdenSAP.objects.all()[:50]

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