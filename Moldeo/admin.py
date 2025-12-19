from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
import json

from .models import (
    Actividades, Defectos, Estatus, Lideres, Maquinas, Moldmakers, Moldes,
    NumerosDeParte, Retorno, RetornoInfo, Semana, Zonas, Bitacora,
    OrdenMCM, OrdenCHO, OrdenTPM, OrdenPREP, OrdenSAP, AsignacionUniversal
)

# ---------------------------------
# Tablas de referencia / maestros
# ---------------------------------
@admin.register(Actividades)
class ActividadesAdmin(admin.ModelAdmin):
    list_display = ('id_actividad', 'nombre_actividad')

@admin.register(Defectos)
class DefectosAdmin(admin.ModelAdmin):
    list_display = ('id_defecto', 'nombre_defecto', 'main_activity')
    search_fields = ('nombre_defecto',)

@admin.register(Estatus)
class EstatusAdmin(admin.ModelAdmin):
    list_display = ('id_estatus', 'numero_estatus')

@admin.register(Lideres)
class LideresAdmin(admin.ModelAdmin):
    list_display = ('id_lider', 'nombre')


@admin.register(Moldmakers)
class MoldmakersAdmin(admin.ModelAdmin):
    list_display = ('id_mold_m', 'nombre')




@admin.register(Retorno)
class RetornoAdmin(admin.ModelAdmin):
    list_display = ('id_retorno', 'retorno_opcion')

@admin.register(RetornoInfo)
class RetornoInfoAdmin(admin.ModelAdmin):
    list_display = ('id_retorno_info', 'info_retorno')

@admin.register(Semana)
class SemanaAdmin(admin.ModelAdmin):
    list_display = ('id_semana', 'semana_natural', 'semana_fiscal')

@admin.register(Zonas)
class ZonasAdmin(admin.ModelAdmin):
    list_display = ('id_zona', 'zona', 'wc', 'mn')

@admin.register(OrdenSAP)
class OrdenSAPAdmin(admin.ModelAdmin):
    list_display = ('order', 'description', 'work_center', 'equipment', 'fecha_inicio')
    search_fields = ('order', 'description', 'equipment', 'work_center')
    list_filter = ('fecha_inicio', 'work_center')
    ordering = ('-fecha_inicio',)

# ---------------------------------
# Tabla principal de bitácora
# ---------------------------------
@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = (
        'fecha', 'orden', 'maquina', 'molde', 'parte_actual', 'parte_entrante',
        'defecto1', 'estatus'
    )
    list_filter = ('fecha', 'maquina', 'molde', 'lider1', 'lider2', 'estatus')
    search_fields = ('orden', 'molde__numero_molde')

# ---------------------------------
# Configuración para las Órdenes Nuevas
# ---------------------------------

class AsignacionUniversalInline(GenericTabularInline):
    model = AsignacionUniversal
    extra = 0
    can_delete = True
    fields = ('nombre_tecnico', 'mesa', 'defecto', 'detalles_json', 'activo', 'fecha_inicio', 'fecha_fin')
    readonly_fields = ('fecha_inicio', 'fecha_fin')

class OrdenAdminBase(admin.ModelAdmin):
    list_display = ('numero_orden', 'ver_molde', 'status', 'estado', 'fecha_creacion', 'ver_tecnicos_resumen')
    list_filter = ('fecha_creacion', 'estado', 'status', 'tipo_mntn')
    search_fields = ('numero_orden', 'molde__numero_molde')
    inlines = [AsignacionUniversalInline] 

    def ver_molde(self, obj):
        return obj.molde.numero_molde if obj.molde else "N/A"
    ver_molde.short_description = "Molde"

    def ver_tecnicos_resumen(self, obj):
        asignaciones = obj.asignaciones.filter(activo=True)
        nombres = [a.nombre_tecnico for a in asignaciones]
        return ", ".join(nombres) if nombres else "Sin asignar"
    ver_tecnicos_resumen.short_description = "Técnicos Activos"

@admin.register(OrdenMCM)
class OrdenMCMAdmin(OrdenAdminBase):
    # 1. LISTADO DE COLUMNAS
    list_display = (
        'numero_orden', 
        'ver_molde', 
        'status', 
        'ver_tecnicos_resumen', 
        'ver_ref_retorno',   # <--- AQUÍ ESTÁ LA REFERENCIA VISUAL MEJORADA
        'motivo_retorno',    
        'ver_detalles_json'
    )
    
    # 2. BUSCADOR (Podrás buscar por la nueva orden O por la vieja)
    search_fields = (
        'numero_orden', 
        'molde__numero_molde', 
        'orden_retorno_ref', # <--- Búsqueda activada para la referencia
        'motivo_retorno'
    )
    
    # 3. FILTROS LATERALES
    list_filter = (
        'fecha_creacion', 
        'estado', 
        'status', 
        'motivo_retorno'
    )

    # 4. ORGANIZACIÓN DEL FORMULARIO
    fieldsets = (
        ('Información General', {
            'fields': ('numero_orden', 'molde', 'defecto_sap', 'status', 'tipo_mntn', 'estado', 'lider')
        }),
        ('Información de Retorno (Si aplica)', {
            'classes': ('collapse',), 
            'fields': ('orden_retorno_ref', 'motivo_retorno', 'observaciones_retorno')
        }),
        ('Tiempos', {
            'fields': ('fecha_creacion', 'fecha_cierre', 'ultima_actualizacion', 'duracion_segundos')
        }),
    )
    
    # --- MÉTODO PARA RESALTAR LA REFERENCIA ---
    def ver_ref_retorno(self, obj):
        if obj.orden_retorno_ref:
            # Se muestra en naranja negrita si existe referencia
            return format_html(
                '<span style="color: #d97706; font-weight: bold;">{}</span>', 
                obj.orden_retorno_ref
            )
        return "-" # Guion si es una orden normal
    
    ver_ref_retorno.short_description = "Ref. Orden Anterior"
    ver_ref_retorno.admin_order_field = 'orden_retorno_ref' # Permite ordenar la columna

    # --- MÉTODO DE DETALLES TÉCNICOS (Igual que antes) ---
    def ver_detalles_json(self, obj):
        asignaciones = obj.asignaciones.all()
        html = ""
        for a in asignaciones:
            try:
                nombre_mostrar = a.nombre_tecnico
                if "(L:" in nombre_mostrar:
                    nombre_mostrar = nombre_mostrar.replace("(L:", "<span style='color:#d97706; font-weight:bold;'>(Líder:") + "</span>"

                detalles = json.loads(a.detalles_json) if a.detalles_json else []
                info_tecnico = f"<strong>{nombre_mostrar} (Mesa {a.mesa}):</strong><br>"
                info_detalles = ""
                
                for d in detalles:
                    defecto_nombre = d.get('defecto', '').upper()
                    valor_cav = d.get('cav', '-')
                    valor_circ = d.get('circ', '-')
                    
                    label_cav = "Cav"
                    label_circ = "Circ"
                    
                    if "HOT RUNNER" in defecto_nombre or "COLADA CALIENTE" in defecto_nombre:
                        label_cav = "Drop"
                        label_circ = "Zona"
                    elif "FALLA DE SENSORES" in defecto_nombre or "SENSOR" in defecto_nombre:
                        label_cav = "PG"
                        label_circ = "EO"
                    
                    info_detalles += f"- {d.get('defecto')} (<span style='color:#2563eb;'>{label_cav}: {valor_cav}</span>, <span style='color:#2563eb;'>{label_circ}: {valor_circ}</span>)<br>"
                
                html += f"<div style='margin-bottom:8px; border-left:3px solid #ccc; padding-left:5px;'>{info_tecnico}{info_detalles}</div>"
            except:
                html += f"{a.nombre_tecnico}: Error JSON<br>"
        
        return format_html(html)
    
    ver_detalles_json.short_description = "Detalles Técnicos"

@admin.register(OrdenCHO)
class OrdenCHOAdmin(OrdenAdminBase):
    pass

@admin.register(OrdenTPM)
class OrdenTPMAdmin(OrdenAdminBase):
    pass

@admin.register(OrdenPREP)
class OrdenPREPAdmin(OrdenAdminBase):
    pass