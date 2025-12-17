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

@admin.register(Maquinas)
class MaquinasAdmin(admin.ModelAdmin):
    list_display = ('id_maquinas', 'wc', 'mn', 'wc2')

@admin.register(Moldmakers)
class MoldmakersAdmin(admin.ModelAdmin):
    list_display = ('id_mold_m', 'nombre')

@admin.register(Moldes)
class MoldesAdmin(admin.ModelAdmin):
    list_display = ('id_molde', 'numero_molde')
    search_fields = ('numero_molde',)

@admin.register(NumerosDeParte)
class NumerosDeParteAdmin(admin.ModelAdmin):
    list_display = ('id_np', 'id_molde', 'numero_parte', 'terminacion', 'inicio', 'number_part', 'junto')

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
    list_display = ('numero_orden', 'ver_molde', 'status', 'ver_tecnicos_resumen', 'motivo_retorno', 'ver_detalles_json')
    search_fields = ('numero_orden', 'molde__numero_molde')
    
    # --- AQUÍ ESTÁ LA LÓGICA DE ETIQUETAS DINÁMICAS ---
    def ver_detalles_json(self, obj):
        asignaciones = obj.asignaciones.all()
        html = ""
        for a in asignaciones:
            try:
                detalles = json.loads(a.detalles_json) if a.detalles_json else []
                info_tecnico = f"<strong>{a.nombre_tecnico} (Mesa {a.mesa}):</strong><br>"
                info_detalles = ""
                
                for d in detalles:
                    defecto_nombre = d.get('defecto', '').upper()
                    valor_cav = d.get('cav', '-')
                    valor_circ = d.get('circ', '-')
                    
                    # Determinar etiquetas según el defecto
                    label_cav = "Cav"
                    label_circ = "Circ"
                    
                    if "HOT RUNNER" in defecto_nombre or "COLADA CALIENTE" in defecto_nombre:
                        label_cav = "Drop"
                        label_circ = "Zona"
                    elif "FALLA DE SENSORES" in defecto_nombre or "SENSOR" in defecto_nombre:
                        label_cav = "PG"
                        label_circ = "EO"
                    
                    # Construir la línea
                    info_detalles += f"- {d.get('defecto')} ({label_cav}: {valor_cav}, {label_circ}: {valor_circ})<br>"
                
                html += f"<div style='margin-bottom:5px; border-bottom:1px solid #eee; padding-bottom:2px;'>{info_tecnico}{info_detalles}</div>"
            except:
                html += f"{a.nombre_tecnico}: Error de formato<br>"
        
        return format_html(html)
    
    ver_detalles_json.short_description = "Detalles (Técnicos)"

@admin.register(OrdenCHO)
class OrdenCHOAdmin(OrdenAdminBase):
    pass

@admin.register(OrdenTPM)
class OrdenTPMAdmin(OrdenAdminBase):
    pass

@admin.register(OrdenPREP)
class OrdenPREPAdmin(OrdenAdminBase):
    pass