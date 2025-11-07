from django.contrib import admin
from .models import Eoats, Preventivos, Refacciones,RegistroPlanCargado,FotoEoat

# Register your models here.
@admin.register(Eoats)
class EoatsAdmin(admin.ModelAdmin):
    list_display = ('id_eoat','numero_eoat', 'locacion')
    search_fields = ('id_eoat','numero_eoat', 'locacion')

@admin.register(Preventivos)
class PreventivosAdmin(admin.ModelAdmin):
    # Podemos mostrar campos del modelo relacionado (Eoats)
    list_display = ( 'locacion','eoat', 'semana', 'fecha_preventivo', 'numero_orden')
    list_filter = ('semana', 'fecha_preventivo')

    # Función para obtener la ubicación del EOAT relacionado
    def get_eoat_locacion(self, obj):
        return obj.id_eoat.locacion
    get_eoat_locacion.short_description = 'Ubicación del EOAT' # Nombre de la columna

@admin.register(Refacciones)
class RefaccionesAdmin(admin.ModelAdmin):
    list_display = ('numero_sap', 'descripcion', 'disponible', 'min', 'max', 'cu', 'moneda', 'locacion')
    search_fields = ('mumero_sap', 'descripcion', 'locacion')
    list_filter = ('proveedor', 'moneda')

@admin.register(RegistroPlanCargado)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'maquina', 'molde')

@admin.register(FotoEoat)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('eoat_fotos', 'imagen', 'descripcion')
    

