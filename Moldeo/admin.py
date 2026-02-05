from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from .models import (
    Lideres, Moldmakers, Maquinas, Moldes, NumerosParte, Defectos,
    OrdenMCM, OrdenCHO, OrdenTPM, OrdenPREP, OrdenSAP, AsignacionUniversal,SubZonaTPM,ActividadTPM,ZonaTPM,EstatusOrden,ActividadPREP
)

# --- INLINE PARA ASIGNACIONES (TECNICOS) ---
# Esto permite ver las asignaciones dentro de la pantalla de detalle de cada orden
class AsignacionInline(GenericTabularInline):
    model = AsignacionUniversal
    extra = 0 # No mostrar filas vacías extra
    readonly_fields = ('fecha_inicio', 'fecha_fin', 'activo')
    can_delete = False
    fields = ('nombre_tecnico', 'mesa', 'cavidad', 'circuito', 'defecto', 'activo', 'fecha_inicio', 'fecha_fin')

# --- CATÁLOGOS BÁSICOS ---
@admin.register(Lideres)
class LideresAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'id_empleado')
    search_fields = ('nombre', 'id_empleado')
    list_filter = ('activo',)

@admin.register(Moldmakers)
class MoldmakersAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'num_empleado','password')
    search_fields = ('nombre', 'num_empleado')
    list_filter = ('activo',)

@admin.register(Maquinas)
class MaquinasAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    search_fields = ('nombre',)
    list_filter = ('activo',)

@admin.register(Moldes)
class MoldesAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'molde_sap', 'maquina', 'proyecto', 'activo')
    search_fields = ('nombre', 'molde_sap', 'proyecto')
    list_filter = ('maquina', 'activo', 'proyecto')
    autocomplete_fields = ['maquina'] # Útil si tienes muchas máquinas

@admin.register(NumerosParte)
class NumerosParteAdmin(admin.ModelAdmin):
    list_display = ('numero_parte', 'molde')
    search_fields = ('numero_parte', 'molde__nombre')
    autocomplete_fields = ['molde']

@admin.register(Defectos)
class DefectosAdmin(admin.ModelAdmin):
    list_display = ('nombre_defecto', 'categoria_ingles', 'codigo_estatus', 'activo')
    search_fields = ('nombre_defecto', 'categoria_ingles')
    list_filter = ('activo', 'codigo_estatus')

# --- CONFIGURACIÓN BASE PARA ÓRDENES ---
class OrdenBaseAdmin(admin.ModelAdmin):
    list_display = ('numero_orden', 'estado', 'fecha_creacion', 'lider', 'maquina', 'molde')
    list_filter = ('estado', 'fecha_creacion','asignaciones', 'lider')
    search_fields = ('numero_orden', 'maquina', 'lider__username', 'molde__nombre')
    autocomplete_fields = ['lider', 'molde']
    inlines = [AsignacionInline] # Aquí insertamos la tabla de técnicos

# --- REGISTRO DE ÓRDENES ESPECÍFICAS ---
@admin.register(OrdenMCM)
class OrdenMCMAdmin(OrdenBaseAdmin):
    pass

@admin.register(OrdenCHO)
class OrdenCHOAdmin(OrdenBaseAdmin):
     list_display = ('numero_orden', 'estado', 'fecha_creacion', 'lider', 'maquina', 'molde','parte_saliente', 'parte_entrante')
    

@admin.register(OrdenTPM)
class OrdenTPMAdmin(OrdenBaseAdmin):
    pass

@admin.register(OrdenPREP)
class OrdenPREPAdmin(OrdenBaseAdmin):
    pass

# --- ORDEN SAP ---
@admin.register(OrdenSAP)
class OrdenSAPAdmin(admin.ModelAdmin):
    list_display = ('order', 'work_center', 'system_status', 'fecha_inicio') # Agregado system_status
    search_fields = ('order', 'work_center', 'system_status')
    list_filter = ('fecha_inicio', 'work_center')

# --- ASIGNACIÓN UNIVERSAL (Vista general) ---
@admin.register(AsignacionUniversal)
class AsignacionUniversalAdmin(admin.ModelAdmin):
    list_display = ('nombre_tecnico', 'content_object', 'activo', 'fecha_inicio')
    list_filter = ('activo', 'fecha_inicio', 'content_type')
    search_fields = ('nombre_tecnico', 'mesa', 'defecto')
@admin.register(EstatusOrden)
class EstatusOrdenAdmin(admin.ModelAdmin):
    list_display = ('status', 'descripcion')
    search_fields = ('status', 'descripcion')
    ordering = ('status',)

# --- TPM: ACTIVIDADES ---
@admin.register(ActividadTPM)
class ActividadTPMAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    search_fields = ('nombre',)
    list_filter = ('activo',)
    ordering = ('nombre',)

# --- TPM: ZONAS ---
class SubZonaInline(admin.TabularInline):
    """Permite agregar SubZonas directamente dentro de la pantalla de Zona"""
    model = SubZonaTPM
    extra = 1

@admin.register(ZonaTPM)
class ZonaTPMAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'total_subzonas')
    search_fields = ('nombre',)
    list_filter = ('activo',)
    inlines = [SubZonaInline] # Muestra las subzonas aquí

    def total_subzonas(self, obj):
        return obj.subzonas.count()
    total_subzonas.short_description = 'Subzonas'

# --- TPM: SUBZONAS (Por si quieres verlas todas juntas) ---
@admin.register(SubZonaTPM)
class SubZonaTPMAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'zona', 'requiere_detalles', 'activo')
    search_fields = ('nombre', 'zona__nombre')
    list_filter = ('zona', 'requiere_detalles', 'activo')
    list_editable = ('requiere_detalles', 'activo') # Para editar rápido desde la lista
    ordering = ('zona', 'nombre')
@admin.register(ActividadPREP)
class ActividadPREPAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    search_fields = ('nombre',)
    list_filter = ('activo',)
    ordering = ('nombre',)
