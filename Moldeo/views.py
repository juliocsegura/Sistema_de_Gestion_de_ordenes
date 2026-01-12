from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
import openpyxl
import pandas as pd
from datetime import datetime, time
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, Prefetch
from django.db import transaction, models
from .models import (Moldmakers, OrdenMCM, OrdenCHO, OrdenTPM, OrdenPREP, Maquinas, NumerosParte, Moldes, OrdenSAP, Defectos, AsignacionUniversal,Lideres)
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
    maquina = request.POST.get('maquina','') or request.GET.get('maquina', '')
    # BUSCAR ID DEL MOLDE (Crucial)
    pre_molde_pk = ''
    if molde_str:
        try:
            m = Moldes.objects.filter(nombre=molde_str).first()
            if m: pre_molde_pk = m.id_molde
        except: pass

    ctx = {
        'pre_orden': orden_sap,
        'pre_defecto': defecto,
        'pre_maquina': maquina,
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
        'lideres_all': Lideres.objects.all().order_by('nombre'),
    }
    return render(request, 'Moldeo/Ordenes_en_curso.html', context)

def btn_status_ordenmcm_view(request):
    context = {
        'pre_orden': request.GET.get('numero_orden', ''),
        'pre_defecto': request.GET.get('defecto_sap', ''),
        'pre_molde': request.GET.get('molde', ''),
        
        'pre_maquina': request.GET.get('maquina', '')
    }
    return render(request, 'Moldeo/btn_status_mcm.html', context)
def btn_status_ordentpm_view(request):
    context = {
        'pre_orden': request.GET.get('numero_orden', ''),
        'pre_defecto': request.GET.get('defecto_sap', ''),
        'pre_molde': request.GET.get('molde', ''),
        
        'pre_maquina': request.GET.get('maquina', '')
    }
    return render(request, 'Moldeo/btn_status_tpm.html', context)

@require_http_methods(["GET", "POST"])
def mcm_view(request):
    # 1. RECUPERAR PARÁMETROS INICIALES (GET o POST)
    status_actual = request.POST.get('statusmcm') or request.GET.get('status', '')
    pre_orden = request.POST.get('numero_orden') or request.GET.get('numero_orden', '')
    pre_defecto = request.POST.get('defecto_sap') or request.GET.get('defecto_sap', '')
    pre_maquina = request.POST.get('maquina') or request.GET.get('maquina', '')
    
    # Manejo inteligente del Molde (Nombre vs ID)
    pre_molde_nombre = request.GET.get('molde', '') 
    pre_molde_pk = request.POST.get('molde', '')

    molde_obj = None

    # Caso A: Tenemos ID (POST), buscamos el objeto
    if pre_molde_pk:
        try:
            molde_obj = Moldes.objects.get(pk=pre_molde_pk)
            pre_molde_nombre = molde_obj.nombre
            if not pre_maquina and molde_obj.maquina: # Autocompletar máquina si falta
                pre_maquina = molde_obj.maquina.nombre
        except: pass
    
    # Caso B: Tenemos Nombre (GET), buscamos ID y Máquina
    elif pre_molde_nombre:
        try:
            molde_obj = Moldes.objects.filter(nombre=pre_molde_nombre).first()
            if molde_obj: 
                pre_molde_pk = molde_obj.pk
                if not pre_maquina and molde_obj.maquina:
                    pre_maquina = molde_obj.maquina.nombre
        except: pass

    # 2. LÓGICA DE GUARDADO (POST)
    if request.method == 'POST':
        # Recuperamos datos del formulario
        numero_orden = request.POST.get('numero_orden')
        defecto_sap = request.POST.get('defecto_sap')
        molde_id = request.POST.get('molde')
        asignaciones_json = request.POST.get('asignaciones_json', '[]')
        
        # Recuperar máquina (del input o del objeto molde)
        maquina_final = request.POST.get('maquina')
        if not maquina_final and molde_obj:
             maquina_final = molde_obj.maquina.nombre if molde_obj.maquina else ''

        # Recuperar datos de retorno
        motivo_ret = request.POST.get('motivo_retorno', '')
        obs_ret = request.POST.get('observaciones_retorno', '')
        orden_ref = request.POST.get('orden_retorno_ref', '')

        # Validaciones
        if not numero_orden:
            messages.error(request, 'Error: Falta el Número de Orden.')
        elif not molde_obj:
            messages.error(request, 'Error: El Molde no es válido o no existe.')
        else:
            try:
                with transaction.atomic():
                    # Crear la Orden
                    nueva_orden = OrdenMCM.objects.create(
                        numero_orden=numero_orden,
                        defecto_sap=defecto_sap,
                        molde=molde_obj,
                        status=status_actual,
                        tipo_mntn='MCM',
                        maquina=maquina_final, # Usamos la máquina recuperada
                        estado='Activa',
                        ultima_actualizacion=timezone.now(),
                        motivo_retorno=motivo_ret,
                        orden_retorno_ref=orden_ref,
                        observaciones_retorno=obs_ret
                    )

                    # Procesar Técnicos (JSON)
                    asignaciones_data = json.loads(asignaciones_json)
                    
                    for item in asignaciones_data:
                        nombre = item.get('nombre')
                        lider_tec = item.get('lider', '')
                        mesa = item.get('mesa', '-')
                        
                        if nombre:
                            # Formato nombre: "Juan Perez (L: Carlos)"
                            nombre_guardar = f"{nombre} (L: {lider_tec})" if lider_tec else nombre
                            detalles_str = json.dumps(item.get('detalles', []))

                            AsignacionUniversal.objects.create(
                                content_object=nueva_orden,
                                nombre_tecnico=nombre_guardar,
                                mesa=mesa,
                                detalles_json=detalles_str,
                                defecto="Ver detalles",
                                activo=True
                            )

                messages.success(request, f'Orden MCM {numero_orden} registrada correctamente.')
                return redirect('Moldeo:ordenes_en_curso')

            except Exception as e:
                messages.error(request, f'Error crítico al guardar: {str(e)}')
                print(f"DEBUG ERROR SAVE: {e}")

    # 3. RENDERIZADO (GET o Fallo POST)
    context = {
        'status_actual': status_actual,
        'tipo_mntn': 'MCM',
        'pre_orden': pre_orden,
        'pre_defecto': pre_defecto,
        'pre_maquina': pre_maquina, # Pasamos la máquina recuperada
        'pre_molde_nombre': pre_molde_nombre, 
        'pre_molde_pk': pre_molde_pk,
        'lista_defectos': Defectos.objects.filter(activo=True).order_by('nombre_defecto'),
        'moldmakers': Moldmakers.objects.filter(activo=True).order_by('nombre'),
        'lideres_all': Lideres.objects.filter(activo=True).order_by('nombre'),
    }
    return render(request, 'Moldeo/prueba.html', context)
@require_http_methods(["GET", "POST"])
def registro_cho_view(request):
    # 1. Configuración Inicial y Recuperación de Datos
    status_actual = '110' # Valor por defecto para CHO
    tipo_mntn = 'CHO'
    
    pre_orden = request.POST.get('numero_orden') or request.GET.get('numero_orden', '')
    pre_defecto = request.POST.get('defecto_sap') or request.GET.get('defecto_sap', '')
    pre_maquina = request.POST.get('maquina') or request.GET.get('maquina', '')
    
    # Manejo inteligente del Molde (Nombre vs ID)
    pre_molde_nombre = request.GET.get('molde', '') 
    pre_molde_pk = request.POST.get('molde', '')
    
    molde_obj = None
    partes_data = [] # Lista para el dropdown

    # Búsqueda inteligente del Molde
    if pre_molde_pk:
        try:
            molde_obj = Moldes.objects.get(pk=pre_molde_pk)
            pre_molde_nombre = molde_obj.nombre
        except: pass
    elif pre_molde_nombre:
        try:
            molde_obj = Moldes.objects.filter(nombre=pre_molde_nombre).first()
            if molde_obj: pre_molde_pk = molde_obj.pk
        except: pass

    # Obtener Números de Parte si tenemos molde
    if molde_obj:
        qs_partes = NumerosParte.objects.filter(molde=molde_obj).values_list('numero_parte', flat=True)
        partes_data = [{'nombre': p} for p in qs_partes]
    
    partes_json = json.dumps(partes_data)

    # 2. PROCESAMIENTO POST
    if request.method == 'POST':
        numero_orden = request.POST.get('numero_orden')
        defecto_sap = request.POST.get('defecto_sap')
        # Datos específicos de CHO
        parte_saliente = request.POST.get('parte_saliente', '')
        parte_entrante = request.POST.get('parte_entrante', '')
        
        # Recuperar máquina (del input o del objeto)
        maquina_input = request.POST.get('maquina', '')
        if not maquina_input and molde_obj and molde_obj.maquina:
            maquina_input = molde_obj.maquina.nombre

        # Recuperar Asignaciones (JSON stringify desde el front o arrays antiguos)
        # Asumiremos que actualizas el HTML para usar el mismo JSON que MCM, 
        # pero mantenemos compatibilidad básica si usas arrays simples.
        asignaciones_json = request.POST.get('asignaciones_json', '')
        
        if not (numero_orden and molde_obj):
            messages.error(request, 'Error: Faltan campos obligatorios (Orden o Molde).')
        else:
            try:
                with transaction.atomic():
                    # Crear Orden CHO
                    nueva_orden = OrdenCHO.objects.create(
                        numero_orden=numero_orden,
                        defecto_sap=defecto_sap,
                        molde=molde_obj,
                        tipo_mntn=tipo_mntn,
                        status=status_actual,
                        estado='Activa',
                        maquina=maquina_input,
                        parte_saliente=parte_saliente, # <--- Nuevo
                        parte_entrante=parte_entrante, # <--- Nuevo
                        ultima_actualizacion=timezone.now()
                    )

                    # Guardar Técnicos
                    if asignaciones_json:
                        # Si viene el JSON complejo (con mesa, lider, etc.)
                        data = json.loads(asignaciones_json)
                        for item in data:
                            nombre = item.get('nombre')
                            lider_tec = item.get('lider', '')
                            mesa = item.get('mesa', '-')
                            
                            if nombre:
                                nombre_final = f"{nombre} (L: {lider_tec})" if lider_tec else nombre
                                # En CHO a veces no hay "detalles" de defectos, guardamos vacío o lo que venga
                                detalles_str = json.dumps(item.get('detalles', []))
                                
                                AsignacionUniversal.objects.create(
                                    content_object=nueva_orden,
                                    nombre_tecnico=nombre_final,
                                    mesa=mesa,
                                    detalles_json=detalles_str,
                                    activo=True
                                )
                    else:
                        # Fallback: Arrays simples (si tu HTML es antiguo)
                        l_tecnicos = request.POST.getlist('tecnico_nombre[]')
                        l_mesas = request.POST.getlist('mesa[]')
                        from itertools import zip_longest
                        for tec, mes in zip_longest(l_tecnicos, l_mesas, fillvalue=''):
                            if tec and tec.strip():
                                AsignacionUniversal.objects.create(
                                    content_object=nueva_orden,
                                    nombre_tecnico=tec.strip(),
                                    mesa=mes.strip(),
                                    activo=True
                                )

                messages.success(request, f'Orden CHO {numero_orden} registrada.')
                return redirect('Moldeo:ordenes_en_curso')

            except Exception as e:
                messages.error(request, f'Error al guardar: {e}')
                print(f"Error CHO: {e}")

    # 3. RENDERIZADO
    context = {
        'tipo_mntn': tipo_mntn,
        'status_actual': status_actual,
        'pre_orden': pre_orden,
        'pre_molde_nombre': pre_molde_nombre,
        'pre_molde_pk': pre_molde_pk,
        'pre_defecto': pre_defecto,
        'pre_maquina': molde_obj.maquina.nombre if molde_obj and molde_obj.maquina else '',
        'moldmakers': Moldmakers.objects.all().order_by('nombre'),
        'lideres_all': Lideres.objects.filter(activo=True).order_by('nombre'),
        'partes_json': partes_json # Enviamos el JSON para los combos
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
        nombres_defectos = set()
        tecnicos_data = []
        nombres_visibles = [] 
        defectos_visibles = set()
        for asignacion in orden.asignaciones.filter(activo=True):
            if asignacion.detalles_json:
                try:
                    detalles = json.loads(asignacion.detalles_json)
                    for item in detalles:
                        if 'defecto' in item:
                            nombres_defectos.add(item['defecto'])
                except:
                    pass
        
        # Si encontraron defectos, los unimos con comas. Si no, ponemos el de SAP por defecto.
        if nombres_defectos:
          texto_defectos = ", ".join(list(nombres_defectos))
        else:
            # Fallback: Si nadie ha registrado nada aún, mostramos el defecto original
          texto_defectos = getattr(orden, 'defecto_sap', 'Sin defecto')
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
                'lider': str(item.lider) if hasattr(item, 'lider') and item.lider else (str(orden.lider) if orden.lider else None),
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
        

        # Encontrar datos del primer técnico activo para mostrar en la tarjeta
        primero_activo = next((t for t in tecnicos_data if t['activo']), None)
        
        nombre_molde = "N/A"
        if orden.molde:
            try: nombre_molde = orden.molde.nombre
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
            'lista_defectos': texto_defectos,
            'orden_retorno_ref': orden.orden_retorno_ref,
            'motivo_retorno': orden.motivo_retorno,
            'observaciones_retorno': orden.observaciones_retorno,
            'maquina': orden.maquina if orden.maquina else None,
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
        seconds = int(seconds) 
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    # 1. --- LOGICA NUEVA: MAPA DE RETORNOS ---
    # Buscamos en TODAS las tablas (activas y finalizadas) quién está referenciando a una orden vieja
    # Queremos pares: (Referencia_Vieja, Orden_Nueva_Que_La_Creo)
    
    referencias = {} # Diccionario: Clave=OrdenVieja -> Valor=OrdenNueva
    
    # Buscamos en MCM
    refs_mcm = OrdenMCM.objects.exclude(orden_retorno_ref__isnull=True).exclude(orden_retorno_ref__exact='').values_list('orden_retorno_ref', 'numero_orden')
    # Buscamos en CHO, TPM, PREP...
    refs_cho = OrdenCHO.objects.exclude(orden_retorno_ref__isnull=True).exclude(orden_retorno_ref__exact='').values_list('orden_retorno_ref', 'numero_orden')
    refs_tpm = OrdenTPM.objects.exclude(orden_retorno_ref__isnull=True).exclude(orden_retorno_ref__exact='').values_list('orden_retorno_ref', 'numero_orden')
    refs_prep = OrdenPREP.objects.exclude(orden_retorno_ref__isnull=True).exclude(orden_retorno_ref__exact='').values_list('orden_retorno_ref', 'numero_orden')

    # Llenamos el diccionario maestro
    # Si la orden '1050' generó la '1055', el diccionario será: {'1050': '1055'}
    for ref, nueva in list(chain(refs_mcm, refs_cho, refs_tpm, refs_prep)):
        referencias[str(ref)] = str(nueva)

    # ------------------------------------------

    p_asignaciones = Prefetch('asignaciones', queryset=AsignacionUniversal.objects.all())
    
    qs_mcm = OrdenMCM.objects.filter(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()
    qs_cho = OrdenCHO.objects.filter(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()
    qs_tpm = OrdenTPM.objects.filter(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()
    qs_prep = OrdenPREP.objects.filter(estado='Finalizada').select_related('molde', 'lider').prefetch_related(p_asignaciones).all()

    todas = list(chain(qs_mcm, qs_cho, qs_tpm, qs_prep))
    todas.sort(key=lambda o: getattr(o, 'fecha_cierre', o.ultima_actualizacion) or o.fecha_creacion, reverse=True)
    
    datos = []
    for orden in todas:
        asignaciones = list(orden.asignaciones.all())
        fecha_inicio = orden.fecha_creacion
        fecha_fin = getattr(orden, 'fecha_cierre', orden.ultima_actualizacion)
        
        lista_detallada = []
        nombres_simples = []
        
        tiempo_activo_segundos = getattr(orden, 'duracion_segundos', 0)
        tiempo_real_segundos = 0
        if fecha_inicio and fecha_fin:
            tiempo_real_segundos = (fecha_fin - fecha_inicio).total_seconds()
            
        for item in asignaciones:
            detalles_str = ""
            if item.detalles_json:
                try:
                    import json
                    d_obj = json.loads(item.detalles_json)
                    nombres_defectos = [d.get('defecto') for d in d_obj if d.get('defecto')]
                    if nombres_defectos: detalles_str = ", ".join(nombres_defectos)
                except: pass
            if not detalles_str: detalles_str = item.defecto or '-'

            lista_detallada.append({
                'nombre': item.nombre_tecnico,
                'mesa': item.mesa or '-',       
                'cavidad': item.cavidad or '-',
                'circuito': item.circuito or '-',
                'defecto': detalles_str,
                'inicio': item.fecha_inicio.strftime('%H:%M') if item.fecha_inicio else '-',
                'fin': item.fecha_fin.strftime('%H:%M') if item.fecha_fin else 'Activo'
            })
            if item.nombre_tecnico: nombres_simples.append(item.nombre_tecnico)

        tecnico_tabla = ", ".join(list(set(nombres_simples)))
        
        # --- BUSCAMOS SI ESTA ORDEN GENERÓ UN RETORNO ---
        # Preguntamos: ¿El número de esta orden aparece como referencia en alguna otra?
        retorno_generado = referencias.get(str(orden.numero_orden), None)
        # ------------------------------------------------

        datos.append({
            'id': orden.id,
            'tipo': orden.tipo_mntn,
            'numero_orden': orden.numero_orden,
            'molde': orden.molde.nombre if orden.molde else 'N/A',
            'defecto': getattr(orden, 'defecto_sap', '-'),
            'lider': str(orden.lider) if orden.lider else 'Sin Asignar',
            'tecnico': tecnico_tabla,
            'lista_tecnicos': lista_detallada,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'tiempo_activo_fmt': format_duration(tiempo_activo_segundos),
            'tiempo_real_fmt': format_duration(tiempo_real_segundos),    
            'comentarios': orden.comentarios,

            # Datos propios (Si ella fue retorno)
            'orden_retorno_ref': getattr(orden, 'orden_retorno_ref', None),
            'motivo_retorno': getattr(orden, 'motivo_retorno', ''),
            'observaciones_retorno': getattr(orden, 'observaciones_retorno', ''),

            # --- NUEVO DATO: SI ELLA PROVOCÓ UN RETORNO ---
            'genero_retorno': retorno_generado  # Contendrá el número de la nueva orden (ej: "1055") o None
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
def encontrar_encabezados(df_preview, keywords):
    """Busca la fila donde aparecen las palabras clave y retorna su índice."""
    for idx, row in df_preview.iterrows():
        fila_str = [str(val).strip() for val in row.values]
        if all(any(k.lower() in s.lower() for s in fila_str) for k in keywords):
            return idx
    return None

def carga_masiva_view(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('archivo_excel') or request.FILES.get('archivo_sap')
        modelo_destino = request.POST.get('modelo_destino')

        if not excel_file:
            messages.error(request, "Por favor selecciona un archivo.")
            return render(request, 'Moldeo/subir_excel.html')

        try:
            registros_creados = 0
            
            # ==========================================
            # CASO A: ACTUALIZACIÓN SAP
            # ==========================================
            if modelo_destino == 'sap':
                # ... (Lógica SAP sin cambios, funciona bien) ...
                if not excel_file.name.endswith('.xlsx'):
                    messages.error(request, 'Para SAP el archivo debe ser .xlsx')
                    return render(request, 'Moldeo/subir_excel.html')

                wb = openpyxl.load_workbook(excel_file, data_only=True)
                ws = wb['Sheet1'] if 'Sheet1' in wb.sheetnames else wb.active
                
                header_row = 1
                headers = {}
                for r in range(1, 6):
                    row_vals = [str(cell.value).strip() for cell in ws[r] if cell.value]
                    if 'Order' in row_vals:
                        header_row = r
                        for cell in ws[r]:
                            if cell.value: headers[str(cell.value).strip()] = cell.column - 1
                        break
                
                if 'Order' not in headers:
                    messages.error(request, "Error SAP: No se encontró la columna 'Order'.")
                    return redirect('Moldeo:carga_masiva')

                idx_fecha = headers.get('Bas. start date') or headers.get('Basic start date')
                idx_hora = headers.get('Start time')
                idx_equipo = headers.get('Equipment')

                for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
                    try:
                        order_val = row[headers['Order']]
                        if not order_val: continue
                        
                        fecha_val = None
                        if idx_fecha is not None and row[idx_fecha]:
                            raw = row[idx_fecha]
                            if hasattr(raw, 'date'): fecha_val = raw.date()
                            elif isinstance(raw, datetime): fecha_val = raw.date()

                        hora_val = None
                        if idx_hora is not None and row[idx_hora]:
                            raw = row[idx_hora]
                            if isinstance(raw, (datetime, time)):
                                hora_val = raw.time() if isinstance(raw, datetime) else raw
                            elif isinstance(raw, str):
                                try: hora_val = datetime.strptime(raw.strip(), "%H:%M:%S").time()
                                except: pass

                        equip = str(row[idx_equipo]).strip() if idx_equipo is not None and row[idx_equipo] else ''

                        OrdenSAP.objects.update_or_create(
                            order=str(order_val),
                            defaults={
                                'description': row[headers.get('Description', -1)] if 'Description' in headers else '',
                                'work_center': row[headers.get('Work center', -1)] if 'Work center' in headers else '',
                                'equipment': equip,
                                'fecha_inicio': fecha_val,
                                'hora_inicio': hora_val
                            }
                        )
                        registros_creados += 1
                    except: continue

                messages.success(request, f'SAP Actualizado: {registros_creados} órdenes.')
                return redirect('Moldeo:panel_principal')

            # ==========================================
            # CASO B: CATÁLOGOS (Pandas)
            # ==========================================
            else:
                df = None
                
                # Leer archivo
                if excel_file.name.endswith('.csv'):
                    try: df = pd.read_csv(excel_file, encoding='utf-8')
                    except: df = pd.read_csv(excel_file, encoding='latin-1')
                else:
                    xls = pd.ExcelFile(excel_file)
                    keywords = ['MOLDE', 'MAQUINA'] if modelo_destino == 'moldes' else ['DEFECTOS'] if modelo_destino == 'defectos' else ['nombre']
                    
                    for sheet in xls.sheet_names:
                        preview = pd.read_excel(excel_file, sheet_name=sheet, nrows=10, header=None)
                        idx = encontrar_encabezados(preview, keywords)
                        if idx is not None:
                            df = pd.read_excel(excel_file, sheet_name=sheet, header=idx)
                            break
                    
                    if df is None: df = pd.read_excel(excel_file)

                # Limpieza de nombres de columnas
                df.columns = df.columns.astype(str).str.strip()
                col_names = df.columns.tolist()

                # --- PROCESO MOLDES (CORREGIDO) ---
                if modelo_destino == 'moldes':
                    # 1. Identificar columnas (Maestro vs Detalle)
                    # Columna A (Maestra): "MOLDE" (Mayúsculas)
                    col_maestro = 'MOLDE' if 'MOLDE' in col_names else next((c for c in col_names if c.upper()=='MOLDE'), None)
                    col_maquina = 'MAQUINA' if 'MAQUINA' in col_names else next((c for c in col_names if c.upper()=='MAQUINA'), None)
                    
                    # Columna E (Detalle): "Molde" (Normal)
                    # OJO: Pandas renombra duplicados. Si hay "MOLDE" y "Molde", el segundo suele ser "Molde.1"
                    col_detalle = 'Molde' 
                    if 'Molde' not in col_names and 'Molde.1' in col_names: col_detalle = 'Molde.1'
                    elif 'Molde' not in col_names and col_maestro: 
                        # Si no encuentra 'Molde', busca cualquier columna que contenga 'Molde' y no sea la maestra
                        col_detalle = next((c for c in col_names if 'Molde' in c and c != col_maestro), None)

                    col_parte = 'Numeros de Parte' if 'Numeros de Parte' in col_names else next((c for c in col_names if 'Parte' in c), None)

                    if not col_maestro:
                        messages.error(request, f"Error: No se encontró la columna maestra 'MOLDE'.")
                        return redirect('Moldeo:carga_masiva')

                    # ------------------------------------------------
                    # PASO 1: MAESTRO DE MOLDES (Solo ~363 registros)
                    # ------------------------------------------------
                    moldes_ok = 0
                    # Filtramos filas donde la columna MAESTRA no sea nula/NaN
                    df_master = df.dropna(subset=[col_maestro])
                    
                    for _, row in df_master.iterrows():
                        nm = str(row[col_maestro]).strip()
                        # Validación estricta: Ignorar 'nan', 'EOAT', vacíos
                        if not nm or nm.lower() == 'nan' or nm == 'EOAT': continue
                        
                        # Máquina
                        instancia_maq = None
                        if col_maquina and str(row[col_maquina]).lower() != 'nan':
                            maq_nombre = str(row[col_maquina]).strip()
                            if maq_nombre:
                                instancia_maq, _ = Maquinas.objects.get_or_create(nombre=maq_nombre)
                        
                        # Proyecto
                        proy = None
                        if 'PROYECTO' in row and str(row['PROYECTO']).lower() != 'nan':
                            proy = str(row['PROYECTO']).strip()

                        # Crear/Actualizar solo si el nombre es válido
                        Moldes.objects.update_or_create(
                            nombre=nm,
                            defaults={'maquina': instancia_maq, 'proyecto': proy, 'activo': True}
                        )
                        moldes_ok += 1

                    # ------------------------------------------------
                    # PASO 2: DETALLES Y PARTES (Solo vinculación)
                    # ------------------------------------------------
                    partes_ok = 0
                    if col_detalle and col_parte:
                        # Filtramos filas donde haya un número de parte
                        df_det = df.dropna(subset=[col_parte])

                        for _, row in df_det.iterrows():
                            ref_molde = str(row[col_detalle]).strip()
                            num_parte = str(row[col_parte]).strip()

                            if not ref_molde or ref_molde.lower() == 'nan': continue
                            if not num_parte or num_parte.lower() == 'nan': continue

                            # IMPORTANTE: Usamos 'filter().first()' en lugar de 'get_or_create'
                            # Solo agregamos partes a moldes que YA EXISTEN (creados en Paso 1).
                            # Esto evita crear "M1046808" duplicados o vacíos si no estaban en la lista maestra.
                            molde_obj = Moldes.objects.filter(nombre=ref_molde).first()

                            if molde_obj:
                                # Actualizar datos extra del molde existente
                                if 'Molde SAP' in row and str(row['Molde SAP']).lower() != 'nan':
                                    molde_obj.molde_sap = str(row['Molde SAP']).strip()
                                
                                if 'Cavidades' in row:
                                    try:
                                        c = int(row['Cavidades'])
                                        if c > 0: molde_obj.cavidades = c
                                    except: pass
                                
                                molde_obj.save()

                                # Crear Parte
                                NumerosParte.objects.get_or_create(
                                    numero_parte=num_parte,
                                    molde=molde_obj
                                )
                                partes_ok += 1
                            else:
                                # Opcional: Imprimir moldes huerfanos (existen en detalle pero no en maestro)
                                # print(f"Ignorado detalle huérfano: {ref_molde}")
                                pass

                    messages.success(request, f"Proceso OK: {moldes_ok} moldes maestros creados/actualizados. {partes_ok} números de parte vinculados.")

                # --- OTROS ---
                elif modelo_destino == 'defectos':
                    df.columns = df.columns.str.lower()
                    if 'defectos' in df.columns:
                        for _, row in df.iterrows():
                            nom = str(row['defectos']).strip()
                            if nom and nom.lower() != 'nan':
                                Defectos.objects.get_or_create(nombre_defecto=nom, defaults={'activo': True})
                                registros_creados += 1
                        messages.success(request, f"{registros_creados} defectos cargados.")

                elif modelo_destino == 'maquinas':
                    df.columns = df.columns.str.lower()
                    col = next((c for c in df.columns if 'maquina' in c), None)
                    if col:
                        for _, row in df.iterrows():
                            nm = str(row[col]).strip()
                            if nm and nm.lower() != 'nan':
                                Maquinas.objects.get_or_create(nombre=nm)
                                registros_creados += 1
                        messages.success(request, f"{registros_creados} máquinas cargadas.")

                elif modelo_destino in ['tecnicos', 'lideres']:
                    df.columns = df.columns.str.lower()
                    col = 'nombre' if 'nombre' in df.columns else df.columns[0]
                    Modelo = Moldmakers if modelo_destino == 'tecnicos' else Lideres
                    for _, row in df.iterrows():
                        nm = str(row[col]).strip()
                        if nm and nm.lower() != 'nan':
                            Modelo.objects.get_or_create(nombre=nm)
                            registros_creados += 1
                    messages.success(request, f"{registros_creados} personas cargadas.")

            return redirect('Moldeo:carga_masiva')

        except Exception as e:
            messages.error(request, f"Error crítico: {str(e)}")
            return render(request, 'Moldeo/subir_excel.html')

    return render(request, 'Moldeo/subir_excel.html')
   
def lista_sap_view(request):
    # --- 1. Filtros y Búsqueda (Tu lógica estándar) ---
    busqueda = request.GET.get('q', '')
    fecha_filtro = request.GET.get('fecha', '')
 
    ids_registrados = list(chain(
        OrdenMCM.objects.values_list('numero_orden', flat=True),
        OrdenCHO.objects.values_list('numero_orden', flat=True),
        OrdenTPM.objects.values_list('numero_orden', flat=True),
        OrdenPREP.objects.values_list('numero_orden', flat=True)
    ))
    
    ordenes = OrdenSAP.objects.exclude(order__in=ids_registrados)

    if busqueda:
        ordenes = ordenes.filter(
            Q(order__icontains=busqueda) |
            Q(work_center__icontains=busqueda) | # Busca por Molde
            Q(description__icontains=busqueda)
        )
    
    if fecha_filtro:
        ordenes = ordenes.filter(fecha_inicio=fecha_filtro)

  
    ordenes = ordenes.order_by('-fecha_inicio')

   
    moldes_con_maquina = Moldes.objects.select_related('maquina').filter(maquina__isnull=False)

    diccionario_maquinas = {}
    for m in moldes_con_maquina:
        nombre_molde = str(m.nombre).strip()
      
        nombre_maquina = m.maquina.nombre
        diccionario_maquinas[nombre_molde] = nombre_maquina

    # C. Pegamos la etiqueta a cada orden
    lista_final = []
    for orden in ordenes:
        # ¿Qué molde pide esta orden?
        molde_solicitado = str(orden.work_center).strip() if orden.work_center else ""
        
        # Buscamos en el diccionario
        maquina_encontrada = diccionario_maquinas.get(molde_solicitado)
        
        # Guardamos el dato en una variable temporal dentro del objeto
        if maquina_encontrada:
            orden.maquina_relacionada = maquina_encontrada
        else:
            orden.maquina_relacionada = None # No tiene máquina asignada
            
        lista_final.append(orden)

    context = {
        'ordenes': lista_final,
        'busqueda': busqueda,
        'fecha': fecha_filtro
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
    
    orden = OrdenMCM.objects.filter(numero_orden=numero).last()
    
    if orden:
        lista_asignaciones = []
        for asig in orden.asignaciones.all():
            detalles = []
            if asig.detalles_json:
                import json
                try:
                    detalles = json.loads(asig.detalles_json)
                except: pass
            
            # LÓGICA DE SEPARACIÓN (Parsing)
            raw_name = asig.nombre_tecnico
            nombre_real = raw_name
            lider_real = ""
            
            # Si el nombre tiene el formato "Nombre (L: Lider)"
            if "(L:" in raw_name:
                try:
                    parts = raw_name.split("(L:")
                    nombre_real = parts[0].strip() # "Juan Perez"
                    lider_real = parts[1].replace(")", "").strip() # "Pedro"
                except:
                    pass

            lista_asignaciones.append({
                'nombre': nombre_real,
                'lider': lider_real, # Enviamos el líder limpio al JS
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
            'asignaciones': lista_asignaciones
        })
    else:
        return JsonResponse({'success': False, 'message': 'Orden no encontrada'})
    
@require_http_methods(["GET"])
def api_filtrar_ordenes_mcm(request):
    """
    Retorna una lista simple de órdenes FINALIZADAS para el autocompletado.
    """
    q = request.GET.get('q', '')
    
  
    if not q: 
        return JsonResponse([], safe=False)
    
    qs = OrdenMCM.objects.filter(
        numero_orden__icontains=q,
        estado='Finalizada' 
    ).order_by('-fecha_creacion')[:10]
    
    data = []
    for o in qs:
        nombre_molde = o.molde.nombre if o.molde else 'N/A'
        data.append({
            'numero': o.numero_orden,
            'molde': nombre_molde,
            'defecto': o.defecto_sap
        })
        
    return JsonResponse(data, safe=False)