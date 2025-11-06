from django.shortcuts import render,redirect
from django.contrib import messages
import pandas as pd
from .models import STATUS_PRODUCCION, STATUS_DISPONIBLE, STATUS_MANTENIMIENTO,STATUS_PREPARACION
from django.db.models import Q
from django.http import JsonResponse
from .models import Eoats, Preventivos, Refacciones,Movimientos,RegistroPlanCargado ,FotoEoat ,STATUS_CHOICES
from django.db import transaction # Importamos transaction para asegurar la operación
import re # Importamos re para limpieza de strings
import io # Para manejar archivos en memoria de forma más flexible

def desarrollo_view(request):
    return render(request, 'EOATS/desarrollo.html')
def lista_eoats_view(request):
    # 1. Obtenemos el término de búsqueda desde la URL.
    #    request.GET.get('q', '') busca un parámetro 'q'. Si no lo encuentra, usa una cadena vacía.
    query = request.GET.get('q', '')
    
    # 2. Empezamos con todos los EOATs, pero si hay un término de búsqueda, filtramos.
    if not query:
        # Si no hay búsqueda, simplemente muestra todos los EOATs
        lista_de_eoats = Eoats.objects.all()
    else:
        
      # 2. Dividimos la búsqueda en una lista de términos individuales.
        #    Ej: "E-05 Rack" -> ['E-05', 'Rack']
        terminos = list(filter(None, query.split()))

        # 3. Creamos un objeto Q vacío para ir añadiendo condiciones.
        #    Este será nuestro contenedor principal para la consulta.
        query_final = Q()

        # 4. Iteramos sobre cada término que el usuario escribió.
        for termino in terminos:
            termino_a_buscar = termino
            if termino.upper().startswith('M'):
                # Si es así, lo transformamos.
                # Tomamos todo el string EXCEPTO el primer carácter (la 'm')
                # y le anteponemos "21-".
                termino_a_buscar = '21-' + termino[1:]
            # Por cada término, creamos una condición OR que busca
            # ese término en cualquiera de los campos.
            # Usamos __icontains para la búsqueda parcial.
            condicion_por_termino =(
                    Q(numero_eoat__icontains=termino_a_buscar ) | 
                    Q(locacion__icontains=termino_a_buscar )
                )
                # 5. Añadimos esta condición a nuestra consulta principal usando un OR (|=).
                #    Esto asegura que los resultados coincidan con CUALQUIERA de los términos.
            query_final |= condicion_por_termino

        # 6. Finalmente, filtramos el modelo con la consulta compleja que construimos.
        lista_de_eoats = Eoats.objects.filter(query_final)

    # 7. Pasamos el resultado a la plantilla.
    context = {
        'lista_de_eoats': lista_de_eoats,
        'opciones_de_estado': STATUS_CHOICES,
        'query': query,
    }
    return render(request, 'EOATS/lista_eoats.html', context)


def bitacora_view(request):


    if request.method=='POST':
        numero_eoat= request.POST.get('maint-eoat')
        comment=request.POST.get('maint-notes')
        types=request.POST.get('maint-type')
        
        nuevo_status = ''
        if types == 'Preventivo' or 'Correctivo' or 'Preparacion':
            nuevo_status = STATUS_DISPONIBLE
        else :
            nuevo_status = STATUS_PREPARACION 
        # 3. Buscamos el EOAT por su NÚMERO
        try:
            eoat_a_actualizar = Eoats.objects.get(numero_eoat=numero_eoat)
           
            # 5. ¡Actualizamos el EOAT!
            eoat_a_actualizar.status = nuevo_status
            eoat_a_actualizar.save() # Esto actualiza la columna 'status'

            
            #

            # 6. Creamos el registro de bitácora
            Preventivos.objects.create(
                eoat=numero_eoat,
                comentarios = comment,
                tipo = types
                
            )
        
        except Eoats.DoesNotExist:
            # (Manejo de error si el ID del item es incorrecto)
            print(f"Error: No se encontró el EOAT con número {numero_eoat}")
            # (Aquí podrías agregar un mensaje de error para el usuario)
        
        # 7. Redirigimos (usando el 'name' de la URL)
        return redirect('bitacora')
    # Obtenemos los preventivos y los ordenamos por fecha más reciente
    
    query = request.GET.get('q', '')
    
    # 2. Empezamos con todos los EOATs, pero si hay un término de búsqueda, filtramos.
    if query:
        # Usamos Q objects para poder buscar en múltiples campos con un 'OR'
        # __icontains significa que la búsqueda no distingue mayúsculas/minúsculas
        preventivos = Preventivos.objects.filter(
            Q(eoat__icontains=query)    |
            Q(locacion__icontains=query)
        )
    else:
        # Si no hay búsqueda, simplemente muestra todos los EOATs
        preventivos = Preventivos.objects.all().order_by('-fecha_preventivo')[:20]
    
    # 3. Pasamos tanto la lista filtrada como el término de búsqueda a la plantilla.
    context = {
        'historial_preventivos': preventivos,
        'query': query, # Le pasamos el 'query' para usarlo en el 'value' del input
    }
    
    
    return render(request, 'EOATS/bitacora.html', context)


def refacciones_view(request):
       
    query = request.GET.get('q', '')
    
    # 2. Empezamos con todos los EOATs, pero si hay un término de búsqueda, filtramos.
    if query:
        # Usamos Q objects para poder buscar en múltiples campos con un 'OR'
        # __icontains significa que la búsqueda no distingue mayúsculas/minúsculas
        refacciones = Refacciones.objects.filter(
            Q(numero_sap__icontains=query)    |
            Q(numero_proveedor__icontains=query)    |
            Q(descripcion__icontains=query)
        )
    else:
        # Si no hay búsqueda, simplemente muestra todos los EOATs
        refacciones = Refacciones.objects.all().order_by('-numero_sap')
    
    # 3. Pasamos tanto la lista filtrada como el término de búsqueda a la plantilla.
    context = {
        'lista_de_refacciones': refacciones,
    
        'query': query, # Le pasamos el 'query' para usarlo en el 'value' del input
    }
    
    return render(request, 'EOATS/refacciones.html', context)
def movimientos_view(request):
    
    
    # --- Lógica para PROCESAR EL FORMULARIO (POST) ---
    if request.method == 'POST':
        
        # 1. Obtenemos datos de los 'name' del formulario HTML
        tipo_mov = request.POST.get('mov-type')      # 'entrada' o 'salida'
        item_numero = request.POST.get('log-item')   # ej: "EOAT-001"
        
        # --- CAMBIO: Como pediste, ignoramos usuario y comentarios ---
        usuario_actual = None
        comentarios_str = None

        # 2. TRADUCIMOS 'mov-type' al 'status' del modelo
        # (Lógica simplificada al no tener comentarios)
        nuevo_status = ''
        if tipo_mov == 'salida':
            nuevo_status = STATUS_PRODUCCION
        elif tipo_mov == 'entrada':
            nuevo_status = STATUS_PREPARACION # Asumimos 'Disponible' por defecto

        # 3. Buscamos el EOAT por su NÚMERO
        try:
            eoat_a_actualizar = Eoats.objects.get(numero_eoat=item_numero)
            
            # 4. Guardamos el estado anterior para la bitácora
            estado_anterior = eoat_a_actualizar.status
            
            # 5. ¡Actualizamos el EOAT!
            eoat_a_actualizar.status = nuevo_status
            eoat_a_actualizar.save() # Esto actualiza la columna 'status'

            # 6. Creamos el registro de bitácora
            Movimientos.objects.create(
                eoat=eoat_a_actualizar,
                usuario=usuario_actual,       # Se guarda como None
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_status,
                comentarios=comentarios_str   # Se guarda como None
            )
        
        except Eoats.DoesNotExist:
            # (Manejo de error si el ID del item es incorrecto)
            print(f"Error: No se encontró el EOAT con número {item_numero}")
            # (Aquí podrías agregar un mensaje de error para el usuario)
        
        # 7. Redirigimos (usando el 'name' de la URL)
        return redirect('movimientos')

    # --- Lógica para MOSTRAR LA PÁGINA (GET) ---
    # Esto se ejecuta cuando el usuario solo carga la página
    
    # 1. Obtenemos los últimos 20 movimientos para la tabla
    lista_movimientos = Movimientos.objects.all().order_by('-fecha')[:20]
    
    # 2. Preparamos el contexto para el template
    context = {
        'movimientos': lista_movimientos,
    }
    
    # 3. Renderizamos la página y le pasamos los datos
    return render(request, 'EOATS/movimientos_log.html', context)
def plan_view(request):
    """
    Muestra la página con la tabla de los datos cargados desde el Excel.
    """
    # 1. Consultamos la nueva tabla de registros crudos
    registros = RegistroPlanCargado.objects.all()
    
    context = {
        # 2. Pasamos los registros a la plantilla HTML
        'registros_cargados': registros
    }
    # 3. Renderizamos la plantilla que también contiene el formulario de carga
    return render(request, 'EOATS/planes.html', context)


def upload_plan_view(request):
    """
    Maneja la carga del archivo Excel/CSV.
    Transforma el MOLDE (M -> 21-)
    Asigna el STATUS (MANTENIMIENTO)
    Guarda los datos procesados en la tabla 'RegistroPlanCargado'.
    Y ADEMÁS, actualiza el 'status' en la tabla maestra 'Eoats'.
    """
    # Solo debe funcionar con POST
    if request.method != 'POST':
        return redirect('plan_view') 

    # 1. Obtenemos el archivo
    file = request.FILES.get('plan_file') 

    if not file:
        messages.error(request, 'No se seleccionó ningún archivo.')
        return redirect('plan_view') 

    # 2. Verificamos la extensión
    if not file.name.endswith(('.xlsx', '.xls', '.csv')):
        messages.error(request, 'Formato de archivo no válido. Usar .xlsx, .xls o .csv')
        return redirect('plan_view')

    try:
        # --- LÓGICA DE LECTURA ROBUSTA ---
        df = None
        if file.name.endswith('.csv'):
            file_data = file.read().decode('utf-8')
            try:
                df = pd.read_csv(io.StringIO(file_data), sep=',', on_bad_lines='skip')
            except Exception:
                df = pd.read_csv(io.StringIO(file_data), sep=';', on_bad_lines='skip')
            
            if len(df.columns) <= 1:
                messages.error(request, 'El CSV solo contiene una columna. Asegúrese de que los datos estén separados por **comas (,)** o **punto y comas (;)** en su archivo.')
                return redirect('plan_view')
        else:
            df = pd.read_excel(file, engine='openpyxl') 

        # --- LÓGICA DE PROCESAMIENTO ROBUSTA ---
        
        # Limpiar y mapear encabezados
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        COL_MAQUINA = 'MAQUINA'
        COL_MOLDE = 'MOLDE'
        COL_FECHA = 'FECHA'

        required_cols = [COL_MAQUINA, COL_MOLDE, COL_FECHA]
        if not all(col in df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in df.columns]
            messages.error(request, f'El archivo debe contener las columnas exactas: {", ".join(required_cols)}. Faltan: {", ".join(missing_cols)}.')
            return redirect('plan_view')

        # Procesar fechas y limpiar strings
        df[COL_FECHA] = pd.to_datetime(df[COL_FECHA], errors='coerce', dayfirst=True) 
        df[COL_MAQUINA] = df[COL_MAQUINA].fillna('').astype(str).str.strip()
        df[COL_MOLDE] = df[COL_MOLDE].fillna('').astype(str).str.strip()


        # --- LÓGICA DE ACTUALIZACIÓN (PROCESAR Y GUARDAR) ---
        with transaction.atomic():
            
            # Borrar el log anterior
            RegistroPlanCargado.objects.all().delete()
            
            nuevos_registros_auditoria = []
            filas_guardadas = 0
            filas_ignoradas_no_molde = 0
            
            # Contadores para la actualización de Eoats
            filas_eoat_actualizadas = 0
            filas_ignoradas_no_eoat = 0


            for index, row in df.iterrows():
                maquina = row[COL_MAQUINA]
                molde_crudo = row[COL_MOLDE]
                fecha_pandas = row[COL_FECHA]
                
                # Validación de Molde no vacío
                if not molde_crudo:
                    filas_ignoradas_no_molde += 1
                    continue 

                # *** LÓGICA DE TRANSFORMACIÓN ***
                # 1. Transformar Molde (M -> 21-)
                molde_final = re.sub(r'^[Mm]', '21-', molde_crudo, 1)
                
                # 2. Asignar Status
                status_asignado = STATUS_MANTENIMIENTO


                # *** NUEVA LÓGICA PARA ACTUALIZAR EOATS ***
                try:
                    # 3. Buscar el EOAT maestro
                    eoat_maestro = Eoats.objects.get(numero_eoat=molde_final)
                    
                    # 4. Actualizar su status
                    eoat_maestro.status = STATUS_MANTENIMIENTO
                    eoat_maestro.save(update_fields=['status']) # Eficiente: solo actualiza el status
                    
                    filas_eoat_actualizadas += 1

                except Eoats.DoesNotExist:
                    # El EOAT existe en el Excel pero no en la BD maestra
                    filas_ignoradas_no_eoat += 1
                    # No hacemos nada, solo lo guardamos en el RegistroPlanCargado
                    pass
                # *** FIN DE LA NUEVA LÓGICA ***


                # Manejo de fechas
                fecha_db = None
                if pd.notna(fecha_pandas):
                    fecha_db = fecha_pandas.date() 
                
                # PASO A: Registrar en la tabla (siempre se registra)
                nuevos_registros_auditoria.append(
                    RegistroPlanCargado(
                        maquina=maquina,
                        molde=molde_final, # Guardamos el molde transformado
                        fecha=fecha_db,
                        status=status_asignado # Guardamos el status
                    )
                )
                filas_guardadas += 1
            
            # Guardar los registros
            if nuevos_registros_auditoria:
                RegistroPlanCargado.objects.bulk_create(nuevos_registros_auditoria)

        # Mensaje de éxito simple
        total_filas = len(df)
        if filas_guardadas > 0:
            messages.success(request, f'¡Carga exitosa! Se procesaron {total_filas} filas. Se guardaron {filas_guardadas} registros en el plan.')
            # Mensaje específico para Eoats
            if filas_eoat_actualizadas > 0:
                messages.info(request, f'Se actualizó el estado a "MANTENIMIENTO" en {filas_eoat_actualizadas} EOATs de la tabla maestra.')
            if filas_ignoradas_no_molde > 0:
                messages.warning(request, f'Se ignoraron {filas_ignoradas_no_molde} filas por tener el MOLDE vacío.')
            # Mensaje específico si no se encontró el EOAT
            if filas_ignoradas_no_eoat > 0:
                messages.error(request, f'Se ignoraron {filas_ignoradas_no_eoat} registros (solo en la actualización de estado) porque el MOLDE no fue encontrado en la tabla maestra de Eoats.')
        else:
            messages.error(request, 'El archivo se leyó, pero no se encontró ningún registro válido para guardar.')


    except Exception as e:
        messages.error(request, f'Error al procesar el archivo. Detalle: {e}')
        print(f"ERROR EN LA VISTA UPLOAD_PLAN_VIEW: {e}")

    # Redirigimos de vuelta a la vista del plan
    return redirect('plan_view')

def get_eoat_fotos(request, eoat_id):
    """
    Esta vista devuelve una lista de URLs de las fotos
    para un EOAT específico.
    """
    try:
        eoat = Eoats.objects.get(pk=eoat_id)
        
        # Usamos el related_name 'fotos' que definimos en el modelo FotoEoat
        fotos = eoat.fotos.all()  
        
        # Creamos una lista de las URLs de las imágenes
        urls_fotos = [foto.imagen.url for foto in fotos]
        
        print("URLs de fotos encontradas:", urls_fotos)
        return JsonResponse({'status': 'ok', 'fotos': urls_fotos})
    except Eoats.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'EOAT no encontrado'}, status=404)