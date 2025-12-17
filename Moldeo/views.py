from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import openpyxl
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Prefetch
from django.db import transaction, models
from .models import (
    Moldmakers, OrdenMCM, OrdenCHO, OrdenTPM, OrdenPREP, 
    Moldes, OrdenSAP, Defectos, AsignacionUniversal,Lideres # Updated imports
)
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django.views.decorators.http import require_http_methods 
from django.utils import timezone
import json
from itertools import chain, zip_longest
from operator import attrgetter
def es_lider(user):
    if not user.is_authenticated: 
        return False
    return user.is_superuser or user.groups.filter(name='Lideres').exists()

# --- VISTA DEL PANEL PRINCIPAL (Dashboard) ---
def panel_view(request):
    return render(request, 'Moldeo/panel_principal.html')

# --- VISTAS DE REGISTRO ---

def Registrar_Orden_view(request):
    lista_tecnicos = Moldmakers.objects.all().order_by('nombre')
    es_lider_user = request.user.groups.filter(name='Lideres').exists() or request.user.is_superuser
    
    # Datos de URL
    orden_sap = request.GET.get('orden_sap', '') or request.GET.get('numero_orden', '')
    defecto = request.GET.get('defecto', '') or request.GET.get('defecto_sap', '')
    molde_str = request.GET.get('molde', '') # Nombre (Ej: M123)
    status_url = request.GET.get('status', '100')

    # BUSCAR ID DEL MOLDE (Crucial)
    pre_molde_pk = ''
    if molde_str:
        try:
            m = Moldes.objects.filter(numero_molde=molde_str).first()
            if m: pre_molde_pk = m.id_molde
        except: pass

    ctx = {
        'pre_orden': orden_sap,
        'pre_defecto': defecto,
        'pre_molde_nombre': molde_str,
        'pre_molde_pk': pre_molde_pk, # <--- Esto llena el input hidden
        'status_actual': status_url,
        'moldmakers': lista_tecnicos,
        'es_lider_logueado': es_lider_user,
        'lideres_all': Lideres.objects.all().order_by('nombre'),
        'lista_defectos': Defectos.objects.all().order_by('nombre_defecto')
    }
    return render(request, 'Moldeo/registrar_orden.html', ctx)

def Orden_en_curso_view(request):
    lista_tecnicos = Moldmakers.objects.all().order_by('nombre')
    es_lider = request.user.is_superuser or request.user.groups.filter(name='Lideres').exists()
    lista_defectos = Defectos.objects.all().order_by('nombre_defecto')
    # DEBUG: Imprimir en la terminal de Python para verificar
    print(f"DEBUG PANEL: Usuario {request.user.username} - SuperUser: {request.user.is_superuser} - Es Lider: {es_lider}")
    context = { 
        'lista_defectos': lista_defectos,
        'moldmakers': lista_tecnicos,
        'es_lider_logueado': es_lider
    }
    return render(request, 'Moldeo/Ordenes_en_curso.html', context)

def btn_status_ordenmcm_view(request):
    context = {
        'pre_orden': request.GET.get('numero_orden', ''),
        'pre_defecto': request.GET.get('defecto_sap', ''),
        'pre_molde': request.GET.get('molde', '')
    }
    return render(request, 'Moldeo/btn_status_mcm.html', context)

@require_http_methods(["GET", "POST"])
def mcm_view(request):
    # 1. Configuración inicial (Valores por defecto)
    status_actual = request.POST.get('statusmcm') or request.GET.get('status', '')
    tipo_mntn = 'MCM'
    pre_orden = request.POST.get('numero_orden') or request.GET.get('numero_orden', '')
    pre_defecto = request.POST.get('defecto_sap') or request.GET.get('defecto_sap', '')
    
    # Intentamos obtener el nombre y el ID de diferentes fuentes (GET o POST)
    pre_molde_nombre = request.GET.get('molde', '') 
    pre_molde_pk = request.POST.get('molde', '') # Prioridad al POST (Hidden Input)

    # Lógica de Recuperación: Si tenemos ID pero no Nombre (pasó en un POST fallido), recuperamos el Nombre
    if pre_molde_pk and not pre_molde_nombre:
        try:
            m_obj = Moldes.objects.get(pk=pre_molde_pk)
            pre_molde_nombre = m_obj.numero_molde
        except:
            pass
    
    # Lógica Inversa: Si tenemos Nombre pero no ID (pasó en un GET inicial), recuperamos el ID
    if not pre_molde_pk and pre_molde_nombre:
        try:
            m = Moldes.objects.filter(numero_molde=pre_molde_nombre).first()
            if m: pre_molde_pk = m.id_molde
        except: pass

    # 2. LÓGICA DE GUARDADO (POST)
    if request.method == 'POST':
        numero_orden = request.POST.get('numero_orden')
        defecto_sap = request.POST.get('defecto_sap')
        molde_form_id = request.POST.get('molde') # Este es el ID oculto
        asignaciones_json_str = request.POST.get('asignaciones_json', '[]')

        motivo_ret = request.POST.get('motivo_retorno', '')
        obs_ret = request.POST.get('observaciones_retorno', '')
        
        molde_instancia = None
        
        # Validación de ID numérico para evitar el error "invalid literal for int() with base 10: 'None'"
        if molde_form_id and str(molde_form_id).isdigit():
            try:
                molde_instancia = Moldes.objects.get(pk=molde_form_id)
            except Moldes.DoesNotExist:
                molde_instancia = None

        # Validación final antes de guardar
        if not (numero_orden and defecto_sap and molde_instancia):
            # Si falla aquí, el código continuará abajo y renderizará la página de nuevo
            # PERO ahora 'pre_molde_pk' y 'pre_molde_nombre' ya fueron reconstruidos al inicio de la función
            messages.error(request, 'Error: Faltan campos obligatorios o el Molde no es válido.')
        else:
            try:
                with transaction.atomic():
                    lider_inicial = None
                    if es_lider(request.user):
                        lider_inicial = request.user

                    nueva_orden = OrdenMCM.objects.create(
                        numero_orden=numero_orden,
                        defecto_sap=defecto_sap,
                        molde=molde_instancia,
                        status=status_actual,
                        tipo_mntn=tipo_mntn,
                        estado='Activa',
                        lider=lider_inicial,
                        ultima_actualizacion=timezone.now(),
                        motivo_retorno=motivo_ret,
                        observaciones_retorno=obs_ret
                    )

                    import json
                    asignaciones_data = json.loads(asignaciones_json_str)

                    for item in asignaciones_data:
                        nombre = item.get('nombre')
                        if nombre:
                            detalles_str = json.dumps(item.get('detalles', []))
                            AsignacionUniversal.objects.create(
                                content_object=nueva_orden,
                                nombre_tecnico=nombre,
                                mesa=item.get('mesa', '-'),
                                detalles_json=detalles_str,
                                defecto="Ver detalles",
                                activo=True
                            )

                messages.success(request, f'Orden MCM {numero_orden} registrada con éxito.')
                return redirect('Moldeo:ordenes_en_curso')
            
            except Exception as e:
                messages.error(request, f'Error interno al guardar: {e}')
                print(f"Error Save: {e}")

    # 3. RENDERIZADO (GET o Error en POST)
    context = {
        'status_actual': status_actual,
        'tipo_mntn': tipo_mntn,
        'pre_orden': pre_orden,
        'pre_defecto': pre_defecto,
        # Estas dos variables ahora siempre tendrán datos, incluso tras un error
        'pre_molde_nombre': pre_molde_nombre, 
        'pre_molde_pk': pre_molde_pk,
        'lista_defectos': Defectos.objects.all().order_by('nombre_defecto'),
        'moldmakers': Moldmakers.objects.all().order_by('nombre'),
        'lideres_all': Lideres.objects.all().order_by('nombre'),
        'es_lider_logueado': es_lider(request.user)
    }
    
    return render(request, 'Moldeo/prueba.html', context)

@require_http_methods(["GET", "POST"])
def registro_cho_view(request):
    tipo_mntn = 'CHO'
    status_actual = '110'
    pre_orden = request.GET.get('numero_orden', '')
    pre_molde_nombre = request.GET.get('molde', '')
    tecnicos_list = Moldmakers.objects.all().order_by('nombre')
    
    pre_molde_pk = ''
    if pre_molde_nombre:
        try:
            m = Moldes.objects.filter(numero_molde=pre_molde_nombre).first()
            if m: pre_molde_pk = m.id_molde
        except: pass

    if request.method == 'POST':
        numero_orden = request.POST.get('numero_orden')
        molde_form_id = request.POST.get('molde')
        
        # Arrays del formulario (Asegúrate de actualizar tu HTML de CHO para usar estos names)
        # Si el HTML de CHO aún usa los viejos names, cámbialos aquí temporalmente o actualiza el HTML
        l_tecnicos = request.POST.getlist('tecnico_nombre[]') 
        l_mesas = request.POST.getlist('mesa[]')
        # CHO suele ser más simple, pero usamos la misma estructura para consistencia

        molde_instancia = None
        lider_inicial = None
        if request.user.is_authenticated and es_lider(request.user):
            lider_inicial = request.user
        if molde_form_id:
            try:
                molde_instancia = Moldes.objects.get(pk=molde_form_id)
            except Moldes.DoesNotExist:
                molde_instancia = None

        if not (numero_orden and molde_instancia):
            messages.error(request, 'Error: Faltan campos obligatorios.')
        else:
            try:
                with transaction.atomic():
                    nueva_orden = OrdenCHO.objects.create(
                        numero_orden=numero_orden,
                        molde=molde_instancia,
                        tipo_mntn=tipo_mntn,
                        lider=lider_inicial,
                        status=status_actual,
                        estado='Activa',
                        ultima_actualizacion=timezone.now()
                    )

                    # Guardar Asignaciones
                    # Zip simple si solo hay técnicos y mesas
                    from itertools import zip_longest
                    datos = zip_longest(l_tecnicos, l_mesas, fillvalue='')
                    
                    for tec, mesa in datos:
                        if tec and tec.strip():
                            AsignacionUniversal.objects.create(
                                content_object=nueva_orden,
                                nombre_tecnico=tec.strip(),
                                mesa=mesa.strip() if mesa else '',
                                activo=True
                            )

                messages.success(request, f'Orden CHO {numero_orden} registrada.')
                return redirect('Moldeo:ordenes_en_curso')
            except Exception as e:
                messages.error(request, f'Error: {e}')

    context = {
        'tipo_mntn': tipo_mntn,
        'status_actual': status_actual,
        'pre_orden': pre_orden,
        'pre_molde_nombre': pre_molde_nombre,
        'pre_molde_pk': pre_molde_pk,
        'moldmakers': tecnicos_list
    }
    return render(request, 'Moldeo/registro_cho.html', context)

@require_http_methods(["GET", "POST"])
def registro_tpm_view(request):
    tipo_mntn = 'TPM'
    pre_orden = request.GET.get('numero_orden', '')
    pre_molde_nombre = request.GET.get('molde', '')
    tecnicos_list = Moldmakers.objects.all().order_by('nombre')
    
    pre_molde_pk = ''
    if pre_molde_nombre:
        try:
            m = Moldes.objects.filter(numero_molde=pre_molde_nombre).first()
            if m: pre_molde_pk = m.id_molde
        except: pass

    if request.method == 'POST':
        numero_orden = request.POST.get('numero_orden')
        molde_form_id = request.POST.get('molde')
        
        # Adapta esto según los inputs de tu HTML de TPM
        l_tecnicos = request.POST.getlist('tecnico_nombre[]') 
        l_mesas = request.POST.getlist('mesa[]')

        molde_instancia = None
        if molde_form_id:
            try:
                molde_instancia = Moldes.objects.get(pk=molde_form_id)
            except Moldes.DoesNotExist:
                molde_instancia = None

        if not (numero_orden and molde_instancia):
            messages.error(request, 'Error: Faltan campos.')
        else:
            try:
                with transaction.atomic():
                    nueva_orden = OrdenTPM.objects.create(
                        numero_orden=numero_orden,
                        molde=molde_instancia,
                        tipo_mntn=tipo_mntn,
                        estado='Activa',
                        ultima_actualizacion=timezone.now()
                    )

                    from itertools import zip_longest
                    datos = zip_longest(l_tecnicos, l_mesas, fillvalue='')
                    
                    for tec, mesa in datos:
                        if tec and tec.strip():
                            AsignacionUniversal.objects.create(
                                content_object=nueva_orden,
                                nombre_tecnico=tec.strip(),
                                mesa=mesa.strip() if mesa else '',
                                activo=True
                            )

                messages.success(request, f'Orden TPM {numero_orden} registrada.')
                return redirect('Moldeo:ordenes_en_curso')
            except Exception as e:
                messages.error(request, f'Error: {e}')

    context = {
        'tipo_mntn': tipo_mntn,
        'pre_orden': pre_orden,
        'pre_molde_nombre': pre_molde_nombre,
        'pre_molde_pk': pre_molde_pk,
        'moldmakers': tecnicos_list
    }
    return render(request, 'Moldeo/registro_tpm.html', context)

# --- VISTAS DE API ---

@require_http_methods(["GET"])
def api_ordenes_recientes_view(request):
    p_asignaciones = Prefetch('asignaciones', queryset=AsignacionUniversal.objects.all())

    qs_mcm = OrdenMCM.objects.exclude(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()
    qs_cho = OrdenCHO.objects.exclude(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()
    qs_tpm = OrdenTPM.objects.exclude(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()
    qs_prep = OrdenPREP.objects.exclude(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()

    todas = list(chain(qs_mcm, qs_cho, qs_tpm, qs_prep))
    todas.sort(key=attrgetter('fecha_creacion'), reverse=True)
    
    data = []
    for orden in todas:
        asignaciones = list(orden.asignaciones.all())
        
        tecnicos_data = []
        nombres_visibles = [] 
        defectos_visibles = set()
        
        for item in asignaciones:
            # 1. Intentar leer JSON complejo
            try:
                detalles_obj = json.loads(item.detalles_json) if item.detalles_json else []
            except:
                detalles_obj = []

            # 2. Compatibilidad con datos viejos (planos)
            if not detalles_obj and (item.defecto or item.cavidad):
                detalles_obj = [{
                    'defecto': item.defecto or '', 
                    'cav': item.cavidad or '-', 
                    'circ': item.circuito or '-'
                }]

            # 3. --- CORRECCIÓN CLAVE: Extraer resumen para la tarjeta principal ---
            # Tomamos la cavidad/circuito del PRIMER detalle para mostrarlo en el dashboard
            resumen_cav = '-'
            resumen_circ = '-'
            if detalles_obj:
                resumen_cav = detalles_obj[0].get('cav', '-')
                resumen_circ = detalles_obj[0].get('circ', '-')

            # 4. Construir objeto del técnico
            tecnicos_data.append({
                'id': item.id, 
                'nombre': item.nombre_tecnico,
                'mesa': item.mesa or '-',
                'activo': item.activo,
                'fecha_fin': item.fecha_fin.strftime('%H:%M') if item.fecha_fin else None,
                
                'detalles': detalles_obj, # Lista completa para el Modal
                
                # Agregamos estos campos para evitar el KeyError
                'cavidad': resumen_cav,   
                'circuito': resumen_circ
            })
            
            # Recolectar nombres y defectos para el resumen visual
            if item.activo:
                nombres_visibles.append(item.nombre_tecnico)
                for det in detalles_obj:
                    if det.get('defecto'):
                        defectos_visibles.add(det.get('defecto'))
        
        # Ordenar: Activos primero
        tecnicos_data.sort(key=lambda x: x['activo'], reverse=True)

        tecnico_str = ", ".join(nombres_visibles) if nombres_visibles else "Sin técnico activo"
        nombre_lider = orden.lider.username if orden.lider else "Sin Líder Asignado"
        tiene_lider = bool(orden.lider)

        # Encontrar datos del primer técnico activo para mostrar en la tarjeta
        primero_activo = next((t for t in tecnicos_data if t['activo']), None)
        
        nombre_molde = "N/A"
        if orden.molde:
            try: nombre_molde = orden.molde.numero_molde
            except: nombre_molde = "Ref Error"

        data.append({
            'id': orden.id,
            'numero_orden': orden.numero_orden,
            'status': getattr(orden, 'status', '-'),
            'tipo': orden.tipo_mntn,
            'fecha_creacion': timezone.localtime(orden.fecha_creacion).strftime('%d/%m/%Y %H:%M'),
            'molde': nombre_molde,
            'defecto_sap': getattr(orden, 'defecto_sap', '-'),
            'defectos_lista': list(defectos_visibles), 
            'estado': orden.estado, 
            'comentarios': orden.comentarios, 
            'tecnico': tecnico_str,
            'tecnicos_lista': tecnicos_data,
            
            'lider': nombre_lider,
            'tiene_lider': tiene_lider,

            # Aquí es donde fallaba antes: ahora 'cavidad' y 'circuito' existen en 'primero_activo'
            'mesa': primero_activo['mesa'] if primero_activo else '-',
            'cavidad': primero_activo['cavidad'] if primero_activo else '-', 
            'circuito': primero_activo['circuito'] if primero_activo else '-',
            
            'duracion_segundos': getattr(orden, 'duracion_segundos', 0),
            'ultima_actualizacion_iso': orden.ultima_actualizacion.isoformat() if hasattr(orden, 'ultima_actualizacion') and orden.ultima_actualizacion else None,
        })
    
    return JsonResponse({'ordenes': data})

@require_http_methods(["GET","POST"])
def historial_finalizadas_view(request):
    def format_duration(seconds):
        if not seconds: return "00:00:00"
        
        # Agregamos int() para quitar decimales antes de calcular
        seconds = int(seconds) 
        
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
    # Prefetch único
    p_asignaciones = Prefetch('asignaciones', queryset=AsignacionUniversal.objects.all())
    
    qs_mcm = OrdenMCM.objects.filter(estado='Finalizada').select_related('molde').prefetch_related(p_asignaciones).all()
    qs_cho = OrdenCHO.objects.filter(estado='Finalizada').select_related('molde').prefetch_related(p_asignaciones).all()
    qs_tpm = OrdenTPM.objects.filter(estado='Finalizada').select_related('molde').prefetch_related(p_asignaciones).all()
    qs_prep = OrdenPREP.objects.filter(estado='Finalizada').select_related('molde').prefetch_related(p_asignaciones).all()

    todas = list(chain(qs_mcm, qs_cho, qs_tpm, qs_prep))
    todas.sort(key=lambda o: getattr(o, 'fecha_cierre', o.ultima_actualizacion) or o.fecha_creacion, reverse=True)
    
    datos = []
    for orden in todas:
        asignaciones = list(orden.asignaciones.all())
        fecha_inicio = orden.fecha_creacion
        fecha_fin = getattr(orden, 'fecha_cierre', orden.ultima_actualizacion)
        lista_detallada = []
        nombres_simples = []
        defectos_reales = set()
        # 1. Tiempo Acumulado (El que cuenta el cronómetro, descontando pausas)
        tiempo_activo_segundos = getattr(orden, 'duracion_segundos', 0)

        # 2. Tiempo Real (Resta simple: Fin - Inicio)
        tiempo_real_segundos = 0
        if fecha_inicio and fecha_fin:
            diferencia = fecha_fin - fecha_inicio
            tiempo_real_segundos = diferencia.total_seconds()
        for item in asignaciones:
            lista_detallada.append({
                'nombre': item.nombre_tecnico,
                'mesa': item.mesa or '-',       
                'cavidad': item.cavidad or '-',
                'circuito': item.circuito or '-',
                'defecto': item.defecto or '-',
                'inicio': item.fecha_inicio.strftime('%d/%m %H:%M') if item.fecha_inicio else '-',
                'fin': item.fecha_fin.strftime('%d/%m %H:%M') if item.fecha_fin else 'Activo'
            })
            if item.nombre_tecnico: nombres_simples.append(item.nombre_tecnico)
            if item.defecto: defectos_reales.add(item.defecto)
        
        tecnico_tabla = ", ".join(list(set(nombres_simples))) # Nombres únicos
        tiempo_activo_segundos = getattr(orden, 'duracion_segundos', 0)
        datos.append({
            'id': orden.id,
            'tipo': orden.tipo_mntn,
            'numero_orden': orden.numero_orden,
            'molde': orden.molde.numero_molde if orden.molde else 'N/A',
            'defecto': getattr(orden, 'defecto_sap', '-'),
            'defecto_real': ", ".join(defectos_reales),
            'tecnico': tecnico_tabla,
            'lista_tecnicos': lista_detallada,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'tiempo_activo_fmt': format_duration(tiempo_activo_segundos), # Cronómetro
            'tiempo_real_fmt': format_duration(tiempo_real_segundos),     # Inicio a Fin
            'comentarios': orden.comentarios
        })

    return render(request, 'Moldeo/ordenes_finalizadas.html', {'ordenes': datos})

@require_http_methods(["POST"])
@transaction.atomic
def api_actualizar_orden_view(request, orden_id):
    try:
        data = json.loads(request.body)
        tipo = data.get('tipo') 
        modelo_map = {'MCM': OrdenMCM, 'CHO': OrdenCHO, 'TPM': OrdenTPM, 'PREP': OrdenPREP}
        Modelo = modelo_map.get(tipo)
        
        if not Modelo: return JsonResponse({'message': 'Tipo inválido'}, status=400)

        # Usamos select_for_update para bloquear la fila mientras editamos
        orden = Modelo.objects.select_for_update().get(id=orden_id)

        # --- LÓGICA DE PAUSA / REANUDAR (Campo: ESTADO) ---
        # Solo entramos aquí si el JS nos manda 'estado' (Activa/Pausada/Finalizada)
        if 'estado' in data:
            nuevo_estado_flujo = data['estado']
            ahora = timezone.now()
            
            # 1. DE ACTIVA -> PAUSADA (Detener reloj)
            if orden.estado == 'Activa' and nuevo_estado_flujo == 'Pausada':
                if orden.ultima_actualizacion:
                    segundos = (ahora - orden.ultima_actualizacion).total_seconds()
                    orden.duracion_segundos = (orden.duracion_segundos or 0) + int(segundos)
                orden.ultima_actualizacion = None 

            # 2. DE PAUSADA -> ACTIVA (Arrancar reloj)
            elif orden.estado == 'Pausada' and nuevo_estado_flujo == 'Activa':
                orden.ultima_actualizacion = ahora

            # 3. FINALIZAR
            elif nuevo_estado_flujo == 'Finalizada':
                if orden.estado == 'Activa' and orden.ultima_actualizacion:
                    segundos = (ahora - orden.ultima_actualizacion).total_seconds()
                    orden.duracion_segundos = (orden.duracion_segundos or 0) + int(segundos)
                
                orden.ultima_actualizacion = None
                if not orden.fecha_cierre: orden.fecha_cierre = ahora
                
                # Cerrar técnicos
                ct = ContentType.objects.get_for_model(orden)
                AsignacionUniversal.objects.filter(content_type=ct, object_id=orden.id, activo=True).update(activo=False, fecha_fin=ahora)

            # GUARDAR SOLO EL ESTADO (Activa/Pausada)
            orden.estado = nuevo_estado_flujo
            orden.save()

        # --- GUARDAR COMENTARIOS ---
        if 'comentarios' in data:
            orden.comentarios = data['comentarios']
            orden.save()

        return JsonResponse({'success': True})

    except Exception as e:
        print(f"ERROR API: {e}")
        return JsonResponse({'message': str(e)}, status=500)

def api_get_moldes(request):
    moldes = Moldes.objects.all().values('id_molde', 'numero_molde')
    data = [{'molde': m['numero_molde'], 'pk': m['id_molde']} for m in moldes]
    return JsonResponse(data, safe=False)

def exportar_ordenes_excel(request):
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="Reporte_Ordenes_General.xlsx"'

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ordenes General"

    headers = ['Tipo', 'ID', 'Orden', 'Status', 'Molde', 'Defecto SAP', 'Asignaciones (Técnico/Defecto)', 'Estado', 'Fecha', 'Comentarios']
    ws.append(headers)

    p_asignaciones = Prefetch('asignaciones', queryset=AsignacionUniversal.objects.all())
    
    qs_mcm = OrdenMCM.objects.select_related('molde').prefetch_related(p_asignaciones).all()
    qs_cho = OrdenCHO.objects.select_related('molde').prefetch_related(p_asignaciones).all()
    qs_tpm = OrdenTPM.objects.select_related('molde').prefetch_related(p_asignaciones).all()
    qs_prep = OrdenPREP.objects.select_related('molde').prefetch_related(p_asignaciones).all()

    todas = list(chain(qs_mcm, qs_cho, qs_tpm, qs_prep))
    todas.sort(key=attrgetter('fecha_creacion'), reverse=True)

    for orden in todas:
        if orden.molde:
            try: nombre_molde = orden.molde.numero_molde
            except: nombre_molde = "Ref Error"
        else: nombre_molde = "N/A"

        # Formatear asignaciones en una celda
        asignaciones_str = ""
        for item in orden.asignaciones.all():
            def_str = f" ({item.defecto})" if item.defecto else ""
            asignaciones_str += f"[{item.nombre_tecnico}{def_str} - {item.mesa or ''}], "

        ws.append([
            orden.tipo_mntn,            
            orden.id,
            orden.numero_orden,
            orden.status,              
            nombre_molde,
            getattr(orden, 'defecto_sap', '-'),
            asignaciones_str,
            orden.estado,
            timezone.localtime(orden.fecha_creacion).strftime('%Y-%m-%d %H:%M'),
            orden.comentarios
        ])

    wb.save(response)
    return response

@require_http_methods(["POST"])
def api_gestionar_tecnicos(request, orden_id):
    try:
        data = json.loads(request.body)
        accion = data.get('accion') 
        tipo = data.get('tipo')
        
        modelo_map = {'MCM': OrdenMCM, 'CHO': OrdenCHO, 'TPM': OrdenTPM, 'PREP': OrdenPREP}
        Modelo = modelo_map.get(tipo)
        if not Modelo: return JsonResponse({'error': 'Tipo inválido'}, status=400)
        
        try:
            orden = Modelo.objects.get(id=orden_id)
        except Modelo.DoesNotExist:
            return JsonResponse({'error': 'Orden no encontrada'}, status=404)

        if accion == 'agregar':
            nombre = data.get('nombre')
            mesa = data.get('mesa')
            
            # --- CORRECCIÓN: RECIBIR LISTA DE DETALLES ---
            detalles_lista = data.get('detalles', []) 
            
            # Si por alguna razón llega vacío, creamos uno genérico
            if not detalles_lista:
                detalles_lista = [{
                    'defecto': data.get('defecto', 'General'),
                    'cav': data.get('cavidad', '-'),
                    'circ': data.get('circuito', '-')
                }]

            # Serializamos a Texto para guardar en la BD
            detalles_json_str = json.dumps(detalles_lista)

            AsignacionUniversal.objects.create(
                content_object=orden,
                nombre_tecnico=nombre,
                mesa=mesa,
                detalles_json=detalles_json_str, # <--- Guardamos el JSON
                defecto="Ver detalles",          # Texto dummy para compatibilidad
                activo=True
            )

        elif accion == 'baja':
            item_id = data.get('item_id')
            asignacion = AsignacionUniversal.objects.get(id=item_id)
            asignacion.activo = False
            asignacion.fecha_fin = timezone.now()
            asignacion.save()

        elif accion == 'relevo':
            # ... (Tu lógica de relevo existente) ...
            id_saliente = data.get('item_id_saliente')
            nombre_entrante = data.get('nombre_entrante')
            
            saliente = AsignacionUniversal.objects.get(id=id_saliente)
            saliente.activo = False
            saliente.fecha_fin = timezone.now()
            saliente.save()

            # El nuevo hereda los detalles del anterior
            AsignacionUniversal.objects.create(
                content_object=orden,
                nombre_tecnico=nombre_entrante,
                mesa=saliente.mesa,
                detalles_json=saliente.detalles_json, # <--- Heredar JSON
                defecto=saliente.defecto,
                activo=True
            )

        return JsonResponse({'success': True})

    except Exception as e:
        print(f"ERROR API: {e}") # Ver error en terminal
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
def importar_sap_view(request):
    if request.method == 'POST' and request.FILES.get('archivo_sap'):
        excel_file = request.FILES['archivo_sap']
        
        if not excel_file.name.endswith('.xlsx'):
            messages.error(request, 'Error: El archivo debe ser un Excel (.xlsx)')
            return render(request, 'Moldeo/importar_sap.html')

        try:
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            ws = wb['Sheet1'] if 'Sheet1' in wb.sheetnames else wb.active

            # Mapear encabezados
            headers = {}
            for cell in ws[1]:
                if cell.value:
                    headers[str(cell.value).strip()] = cell.column - 1

            # Verificar columnas obligatorias
            required_cols = ['Order', 'Description', 'Work center']
            if not all(col in headers for col in required_cols):
                messages.error(request, f'Faltan columnas. Se requiere: {required_cols}')
                return render(request, 'Moldeo/importar_sap.html')

            # Buscar índice de la fecha (Puede llamarse "Bas. start date" o "Basic start date")
            idx_fecha = headers.get('Bas. start date') or headers.get('Basic start date')

            count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                order_val = row[headers['Order']]
                if not order_val: continue

                # Procesar Fecha
                fecha_val = None
                if idx_fecha is not None:
                    raw_date = row[idx_fecha]
                    # openpyxl suele devolver datetime, si es string intentamos no guardar basura
                    if raw_date and hasattr(raw_date, 'date'): 
                        fecha_val = raw_date.date()
                    elif isinstance(raw_date, str):
                        # Aquí podrías agregar lógica para parsear texto si fuera necesario
                        pass 

                OrdenSAP.objects.update_or_create(
                    order=str(order_val),
                    defaults={
                        'description': row[headers['Description']],
                        'work_center': row[headers['Work center']],
                        'equipment': str(row[headers.get('Equipment', -1)]) if headers.get('Equipment') else '',
                        'fecha_inicio': fecha_val # <--- GUARDAMOS LA FECHA
                    }
                )
                count += 1

            messages.success(request, f'Éxito: Se procesaron {count} órdenes correctamente.')
            return redirect('Moldeo:panel_principal')

        except Exception as e:
            messages.error(request, f'Error al procesar: {e}')

    return render(request, 'Moldeo/importar_sap.html')
def lista_sap_view(request):
    # Capturamos lo que el usuario escribe en el buscador
    busqueda = request.GET.get('q', '')
    fecha_filtro = request.GET.get('fecha', '')
    # PASO 1: Recolectar órdenes registradas de TODAS las tablas
    # Usamos values_list(..., flat=True) para obtener solo una lista de strings ['1001', '1002']
    ids_mcm = OrdenMCM.objects.values_list('numero_orden', flat=True)
    ids_cho = OrdenCHO.objects.values_list('numero_orden', flat=True)
    ids_tpm = OrdenTPM.objects.values_list('numero_orden', flat=True)
    ids_prep = OrdenPREP.objects.values_list('numero_orden', flat=True)

    # Unimos todas las listas en una sola usando chain
    ordenes_registradas = list(chain(ids_mcm, ids_cho, ids_tpm, ids_prep))

    # PASO 2: Consultar OrdenSAP EXCLUYENDO (.exclude) todas las registradas
    ordenes = OrdenSAP.objects.exclude(order__in=ordenes_registradas)
    filtros_activos = False
    # PASO 3: Aplicar el buscador del usuario sobre la lista ya filtrada
    if busqueda:
        ordenes = ordenes.filter(
            Q(order__icontains=busqueda) |
            Q(description__icontains=busqueda) |
            Q(equipment__icontains=busqueda) |
            Q(work_center__icontains=busqueda)|
            Q(fecha_inicio__icontains=busqueda)
        )
    if fecha_filtro:
        ordenes = ordenes.filter(fecha_inicio=fecha_filtro)
        filtros_activos = True

    # 4. Limitar resultados si no hay filtros (Para no trabar la página)
    if not filtros_activos:
        ordenes = ordenes.order_by('-fecha_inicio') # Mostrar las 100 más recientes por defecto
    else:
        ordenes = ordenes.order_by('-fecha_inicio')

    context = {
        'ordenes': ordenes,
        'busqueda': busqueda,
        'fecha': fecha_filtro # <--- Enviamos la fecha para mantenerla en el input
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
def api_buscar_orden_info(request):
    numero = request.GET.get('numero')
    if not numero:
        return JsonResponse({'success': False, 'message': 'Falta número'})
    
    # Buscamos la orden
    orden = OrdenMCM.objects.filter(numero_orden=numero).last()
    
    if orden:
        # Recuperar asignaciones (Técnicos/Detalles)
        lista_asignaciones = []
        for asig in orden.asignaciones.all():
            detalles = []
            if asig.detalles_json:
                import json
                try:
                    detalles = json.loads(asig.detalles_json)
                except:
                    pass
            
            lista_asignaciones.append({
                'nombre': asig.nombre_tecnico,
                'mesa': asig.mesa,
                'detalles': detalles
            })

        return JsonResponse({
            'success': True,
            'molde': str(orden.molde),
            'defecto': orden.defecto_sap,
            'comentarios': orden.comentarios or '',
            'motivo_retorno': orden.motivo_retorno or '',
            'observaciones_retorno': orden.observaciones_retorno or '',
            'asignaciones': lista_asignaciones # <--- ENVIAMOS TODO EL DETALLE
        })
    else:
        return JsonResponse({'success': False, 'message': 'Orden no encontrada'})