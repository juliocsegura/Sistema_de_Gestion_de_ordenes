from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

# Create your models here.
class Actividades(models.Model):
    id_actividad = models.AutoField(primary_key=True, blank=True, null=False)
    nombre_actividad = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Actividades'


class Defectos(models.Model):
    id_defecto = models.AutoField(primary_key=True, blank=True, null=False)
    nombre_defecto = models.TextField(blank=True, null=True)
    main_activity = models.TextField(db_column='Main_activity', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Defectos'


class Estatus(models.Model):
    id_estatus = models.AutoField(primary_key=True, blank=True, null=False)
    numero_estatus = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Estatus'


class Lideres(models.Model):
    id_lider = models.AutoField(primary_key=True, blank=True, null=False)
    nombre = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Lideres'


class Maquinas(models.Model):
    id_maquinas = models.AutoField(db_column='id_Maquinas', primary_key=True, blank=True, null=False)  # Field name made lowercase.
    wc = models.TextField(db_column='WC', blank=True, null=True)  # Field name made lowercase.
    mn = models.TextField(db_column='MN', blank=True, null=True)  # Field name made lowercase.
    wc2 = models.TextField(db_column='WC2', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Maquinas'


class Moldmakers(models.Model):
    id_mold_m = models.AutoField(db_column='id_Mold_m', primary_key=True, blank=True, null=False)  # Field name made lowercase.
    nombre = models.TextField(db_column='Nombre', blank=True, null=True)  # Field name made lowercase.
    
    class Meta:
        managed = False
        db_table = 'MoldMakers'


class Moldes(models.Model):
    id_molde = models.AutoField(db_column='id_Molde', primary_key=True, blank=True, null=False)  # Field name made lowercase.
    numero_molde = models.TextField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Moldes'


class NumerosDeParte(models.Model):
    id_np = models.AutoField(primary_key=True, blank=True, null=False)
    id_molde = models.CharField(max_length=50, blank=True, null=True)  # Field name made lowercase.  # This field type is a guess.
    numero_parte = models.TextField(blank=True, null=True)
    terminacion = models.TextField(blank=True, null=True)
    inicio = models.TextField(blank=True, null=True)
    number_part = models.TextField(blank=True, null=True)
    junto = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Numeros_de_parte'


class Retorno(models.Model):
    id_retorno = models.AutoField(primary_key=True, blank=True, null=False)
    retorno_opcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Retorno'


class RetornoInfo(models.Model):
    id_retorno_info = models.AutoField(db_column='id_Retorno_info', primary_key=True, blank=True, null=False)  # Field name made lowercase.
    info_retorno = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Retorno_info'


class Semana(models.Model):
    id_semana = models.AutoField(primary_key=True, blank=True, null=False)
    semana_natural = models.TextField(blank=True, null=True)
    semana_fiscal = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Semana'


class Zonas(models.Model):
    id_zona = models.AutoField(db_column='id_Zona', primary_key=True, blank=True, null=False)  # Field name made lowercase.
    zona = models.TextField(db_column='Zona', blank=True, null=True)  # Field name made lowercase.
    wc = models.TextField(db_column='WC', blank=True, null=True)  # Field name made lowercase.
    mn = models.TextField(db_column='MN', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Zonas'



class Bitacora(models.Model):
    fecha = models.DateField()
    orden = models.CharField(max_length=50)
    maquina = models.CharField(max_length=50)
    molde = models.CharField(max_length=50)
    parte_actual = models.CharField(max_length=50)
    parte_entrante = models.CharField(max_length=50)
    defecto1 = models.CharField(max_length=100)
    cavidad1 = models.CharField(max_length=50)
    defecto2 = models.CharField(max_length=100)
    cavidad2 = models.CharField(max_length=50)
    defecto3 = models.CharField(max_length=100)
    cavidad3 = models.CharField(max_length=50)
    tecnico1 = models.CharField(max_length=50)
    tecnico2 = models.CharField(max_length=50)
    tecnico3 = models.CharField(max_length=50)
    tecnico4 = models.CharField(max_length=50)
    tecnico5 = models.CharField(max_length=50)
    tecnico6 = models.CharField(max_length=50)
    tecnico7 = models.CharField(max_length=50)
    tecnico8 = models.CharField(max_length=50)
    tecnico9 = models.CharField(max_length=50)
    lider1 = models.CharField(max_length=50)
    lider2 = models.CharField(max_length=50)
    fecha_paro = models.DateTimeField(blank=True, null=True)
    fecha_entrega = models.DateTimeField(blank=True, null=True)
    duracion = models.FloatField(blank=True, null=True)
    hora_entrega = models.TimeField(blank=True, null=True)
    retorno = models.CharField(max_length=50)
    estatus = models.CharField(max_length=50)
    info_retorno = models.CharField(max_length=100)
    defecto_retorno = models.CharField(max_length=100)
    lider_retorno = models.CharField(max_length=50)
    tecnico_retorno = models.CharField(max_length=50)
    estatus2 = models.CharField(max_length=50)
    actividad = models.CharField(max_length=50)
    prioridad = models.CharField(max_length=50)
    comentarios = models.TextField()

    class Meta:
        managed = False
        db_table = 'bitacora_bitacora'

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType

# --- 1. MODELO BASE ABSTRACTO ---
# Campos comunes para TODAS las órdenes (MCM, CHO, TPM, etc.)
class OrdenBase(models.Model):
    ESTADO_ACTIVA = 'Activa'
    ESTADO_PAUSADA = 'Pausada'
    ESTADO_FINALIZADA = 'Finalizada'
    ESTADO_CHOICES = [
        (ESTADO_ACTIVA, 'Activa'),
        (ESTADO_PAUSADA, 'Pausada'),
        (ESTADO_FINALIZADA, 'Finalizada'),
    ]
    fecha_creacion = models.DateTimeField(auto_now_add=True) 
    numero_orden = models.CharField(max_length=50, unique=True)
    molde = models.CharField(max_length=50)
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_ACTIVA
    )
    comentarios = models.TextField(blank=True, default='')
    # --- RELACIONES GENÉRICAS INVERSAS ---
    # Esto nos permite hacer "mi_orden.tecnicos.all()"
    tecnicos = GenericRelation('ItemTecnico', related_query_name='orden')
    mesas = GenericRelation('ItemMesa', related_query_name='orden')
    cavidades = GenericRelation('ItemCavidad', related_query_name='orden')

    class Meta:
        abstract = True # No crea una tabla "OrdenBase" en la BD

    def __str__(self):
        return f"Orden {self.numero_orden}"
# --- 2. MODELOS DE ÓRDENES ESPECÍFICAS ---
class OrdenMCM(OrdenBase):
    defecto_sap = models.CharField(max_length=100)
    defecto_real = models.TextField()
    
    def __str__(self):
        return f"Orden MCM {self.numero_orden} - {self.molde}"

class OrdenCHO(OrdenBase):
    tipo_cuchilla = models.CharField(max_length=50, blank=True)
    # ... otros campos ...

class OrdenTPM(OrdenBase):
    equipo = models.CharField(max_length=100, blank=True)
    # ... otros campos ...

class OrdenPREP(OrdenBase):
    material = models.CharField(max_length=100, blank=True)
    # ... otros campos ...


# --- 3. MODELOS GENÉRICOS RELACIONADOS ---
class ItemTecnico(models.Model):
    nombre = models.CharField(max_length=100) 
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.nombre} (Orden: {self.content_object})"

class ItemMesa(models.Model):
    nombre = models.CharField(max_length=50) 
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.nombre} (Orden: {self.content_object})"

class ItemCavidad(models.Model):
    nombre = models.CharField(max_length=50)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"{self.nombre} (Orden: {self.content_object})"