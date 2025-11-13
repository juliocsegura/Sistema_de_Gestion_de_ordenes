from django.shortcuts import render , redirect
from django.contrib import messages
from django.db import transaction
from .models import OrdenMCM, ItemTecnico, ItemMesa, ItemCavidad
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods 
from django.db.models import Prefetch 
# Create your views here.
def panel_view(request):
  ordenes_recientes = OrdenMCM.objects.all().order_by('-fecha_creacion').prefetch_related(
        'tecnicos', 
        'mesas', 
        'cavidades'
  )
    
  context = {
        # Ahora tu dashboard.html recibirá las órdenes reales
        'ordenes_recientes': ordenes_recientes
    }
  return render(request,'Moldeo/panel_principal.html')

def Registrar_Orden_view(request):
  
  return render(request,'Moldeo/Registrar_orden.html')

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
        
        # Validación básica de campos obligatorios
        if not (numero_orden and defecto_sap and defecto_real and molde_form):
             messages.error(request, 'Error: Faltan campos obligatorios. Asegúrate de rellenar todos los campos estáticos.')
             # CORRECCIÓN DE RUTA: Si falla, renderizar 'registrar_orden.html'
             return render(request, 'Moldeo/registrar_orden.html')

        try:
            with transaction.atomic():
                # Crear la orden principal
                nueva_orden = OrdenMCM.objects.create(
                    numero_orden=numero_orden,
                    defecto_sap=defecto_sap,
                    defecto_real=defecto_real,
                    molde=molde_form
                )

                # Guardar items relacionados (Técnicos, Mesas, Cavidades)
                # Solo guarda si el campo no está vacío
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
            # Redirigir al dashboard (usando el nombre 'inicio' de urls.py)
            return redirect('Moldeo:panel_principal')

        except Exception as e:
            messages.error(request, f'Error al guardar la orden: {e}')
            # CORRECCIÓN DE RUTA: Si hay error, renderizar 'registrar_orden.html'
            return render(request, 'Moldeo/prueba.html')

    # --- PETICIÓN GET (Mostrar Formulario) ---
    # CORRECCIÓN DE RUTA: Renderizar 'registrar_orden.html'
    return render(request, 'Moldeo/prueba.html')


def registro_cho_view(request):
    # CORRECCIÓN DE RUTA: (Asumiendo que no has creado este template, usamos el de registro como base)
    # Cambia 'Moldeo/registro_cho.html' por el nombre de tu template si existe.
    return render (request, 'Moldeo/registro_cho.html', {'tipo_orden': 'CHO'})

def registro_tpm_view(request):
    # CORRECCIÓN DE RUTA: (Asumiendo que no has creado este template, usamos el de registro como base)
    # Cambia 'Moldeo/registro_tpm.html' por el nombre de tu template si existe.
    return render (request, 'Moldeo/registro_tpm.html', {'tipo_orden': 'TPM'})

def api_ordenes_recientes_view(request):
    """
    Esta vista devuelve los datos de las órdenes en formato JSON
    para que JavaScript pueda consumirlos.
    
    CORRECCIÓN: Esta versión es robusta y previene crashes
    si una orden no tiene items (técnicos, mesas, etc.)
    """
    
    # Usamos Prefetch para optimizar la consulta y cargar solo el primer item
    tecnicos_prefetch = Prefetch('tecnicos', queryset=ItemTecnico.objects.order_by('id'), to_attr='first_tecnico')
    mesas_prefetch = Prefetch('mesas', queryset=ItemMesa.objects.order_by('id'), to_attr='first_mesa')
    cavidades_prefetch = Prefetch('cavidades', queryset=ItemCavidad.objects.order_by('id'), to_attr='first_cavidad')
    
    ordenes = OrdenMCM.objects.all().order_by('-fecha_creacion').prefetch_related(
        tecnicos_prefetch, mesas_prefetch, cavidades_prefetch
    )[:20] # Limitamos a las últimas 20
    
    data = []
    for orden in ordenes:
        # Lógica robusta para evitar fallos si no hay items
        # 'first_tecnico' es una lista gracias a to_attr, tomamos el [0] si existe
        tecnico_obj = orden.first_tecnico[0] if orden.first_tecnico else None
        mesa_obj = orden.first_mesa[0] if orden.first_mesa else None
        cavidad_obj = orden.first_cavidad[0] if orden.first_cavidad else None
        
        data.append({
            'numero_orden': orden.numero_orden,
            'molde': orden.molde,
            'tecnico': tecnico_obj.nombre if tecnico_obj else 'N/A',
            'mesa': mesa_obj.nombre if mesa_obj else 'N/A',
            'cavidad': cavidad_obj.nombre if cavidad_obj else 'N/A',
            'fecha_creacion_iso': orden.fecha_creacion.isoformat(),
        })
    
    return JsonResponse({'ordenes': data})