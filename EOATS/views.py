from django.shortcuts import render,redirect
from django.contrib import messages
import pandas as pd
from .models import STATUS_PRODUCCION, STATUS_DISPONIBLE, STATUS_MANTENIMIENTO,STATUS_PREPARACION
from django.db.models import Q

# Create your views here.
from .models import Eoats, Preventivos, Refacciones,Movimientos,STATUS_CHOICES
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

    return render(request, 'EOATS/planes.html')
def upload_plan_view(request):
    
    # Si el usuario envía el formulario (POST)
    if request.method == 'POST':
        # 1. Obtenemos el archivo usando el 'name' del input
        file = request.FILES.get('plan_file') 

        if not file:
            messages.error(request, 'No se seleccionó ningún archivo.')
            return redirect('upload_plan_file') # Redirige a la misma página

        # 2. Verificamos la extensión (opcional pero recomendado)
        if not file.name.endswith(('.xlsx', '.xls', '.csv')):
            messages.error(request, 'Formato de archivo no válido. Usar .xlsx, .xls o .csv')
            return redirect('upload_plan_file')

        try:
            # 3. Usamos Pandas para leer el archivo en memoria
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)

            # 4. Procesamos los datos (¡AQUÍ ESTÁ LA MAGIA!)
            # Iteramos sobre cada fila leída del Excel
            for index, row in df.iterrows():
                # Asumimos que tu Excel tiene columnas 'ID', 'Plan', 'Fecha'
                # Y tu modelo tiene campos 'numero_eoat', 'plan', 'proximo_mantenimiento'
                
                # Buscamos si el EOAT ya existe
                eoat, created = Eoats.objects.update_or_create(
                    numero_eoat=row['ID Herramental'], # Columna del Excel
                    defaults={
                        'plan': row['Plan Asignado'], # Columna del Excel
                        'proximo_mantenimiento': row['Próxima Fecha de Mto.'], # Columna del Excel
                        # ... otros campos ...
                    }
                )

            messages.success(request, f'¡Archivo procesado! Se actualizaron {len(df)} registros.')

        except Exception as e:
            # Capturamos cualquier error durante la lectura o procesamiento
            messages.error(request, f'Error al procesar el archivo: {e}')

        # 5. Redirigimos de vuelta a la página del formulario
        return redirect('upload_plan_file') # Usa el 'name' de la URL de tu plantilla

    # Si el usuario solo carga la página (GET)
    else:
        # Simplemente mostramos la página con la tabla
        eoats = Eoats.objects.filter(plan__isnull=False) # Ejemplo
        context = {
            'eoats_con_plan': eoats
        }
        return render(request, 'planes.html', context)
