from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.contrib.contenttypes.models import ContentType
# Register your models here.
from .models import (
    Actividades, Defectos, Estatus, Lideres, Maquinas, Moldmakers, Moldes,
    NumerosDeParte, Retorno, RetornoInfo, Semana, Zonas, Bitacora,OrdenMCM, OrdenCHO, OrdenTPM,
    ItemTecnico, ItemMesa, ItemCavidad,ItemCircuito
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

# ---------------------------------
# Tabla principal de bitácora
# ---------------------------------
@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    list_display = (
        'fecha', 'orden', 'maquina', 'molde', 'parte_actual', 'parte_entrante',
        'defecto1', 'cavidad1', 'defecto2', 'cavidad2', 'defecto3', 'cavidad3',
        'tecnico1', 'tecnico2', 'tecnico3', 'tecnico4', 'tecnico5', 'tecnico6',
        'tecnico7', 'tecnico8', 'tecnico9', 'lider1', 'lider2', 'fecha_paro',
        'fecha_entrega', 'duracion', 'hora_entrega', 'retorno', 'estatus',
        'info_retorno', 'defecto_retorno', 'lider_retorno', 'tecnico_retorno',
        'estatus2', 'actividad', 'prioridad', 'comentarios'
    )
    list_filter = ('fecha', 'maquina', 'molde', 'lider1', 'lider2', 'estatus')
    search_fields = ('orden', 'molde', 'parte_actual', 'parte_entrante', 'defecto1', 'defecto2', 'defecto3')


class TecnicoInline(GenericTabularInline):
    model = ItemTecnico
    extra = 1 

class MesaInline(GenericTabularInline):
    model = ItemMesa
    extra = 1

class CavidadInline(GenericTabularInline):
    model = ItemCavidad
    extra = 1


class OrdenAdminBase(admin.ModelAdmin):
  
    inlines = [
        TecnicoInline,
        MesaInline,
        CavidadInline,
    ]
    
    list_display = ('numero_orden', 'fecha_creacion')
    
    list_filter = ('fecha_creacion',)
   
    search_fields = ('numero_orden','numero_molde')


@admin.register(OrdenMCM)
class OrdenMCMAdmin(OrdenAdminBase):
    list_display = ('numero_orden', 'fecha_creacion', 'ver_tecnicos', 'ver_mesas', 'ver_cavidades','ver_circuitos')
    search_fields = ('numero_orden', )

    
    def ver_tecnicos(self, obj):
        
        ct = ContentType.objects.get_for_model(obj)
        items = ItemTecnico.objects.filter(content_type=ct, object_id=obj.id)
        return ", ".join([str(item) for item in items]) or "-"
    
    ver_tecnicos.short_description = "Técnicos" 

   
    def ver_mesas(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        items = ItemMesa.objects.filter(content_type=ct, object_id=obj.id)
        return ", ".join([str(item) for item in items]) or "-"
    
    ver_mesas.short_description = "Mesas"

  
    def ver_cavidades(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        items = ItemCavidad.objects.filter(content_type=ct, object_id=obj.id)
        return ", ".join([str(item) for item in items]) or "-"
    
    ver_cavidades.short_description = "Cavidades"
    
    def ver_circuitos(self, obj):
        ct = ContentType.objects.get_for_model(obj)
        items = ItemCircuito.objects.filter(content_type=ct, object_id=obj.id)
        return ", ".join([str(item) for item in items]) or "-"
    
    ver_cavidades.short_description = "Circuito"   
@admin.register(OrdenCHO)
class OrdenCHOAdmin(OrdenAdminBase):
    
    list_display = ('numero_orden', 'fecha_creacion',)
    pass

@admin.register(OrdenTPM)
class OrdenTPMAdmin(OrdenAdminBase):
    pass

