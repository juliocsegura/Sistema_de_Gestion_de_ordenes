from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from itertools import chain 
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User


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
    def __str__(self):
            # Devuelve el numero_molde. Si es nulo, devuelve una cadena vacía.
            return str(self.numero_molde) if self.numero_molde else "Sin Nombre"

    @property
    def ordenes(self):
        """
        Esta propiedad une todas las órdenes (MCM, CHO, TPM) en una sola lista.
        Uso: mi_molde.ordenes
        """
        # Obtenemos las listas de cada tabla usando los nombres únicos del Paso 1
        lista_mcm = self.ordenes_mcm.all()
        lista_cho = self.ordenes_cho.all()
        lista_tpm = self.ordenes_tpm.all()
        
        # Las unimos en una sola lista
        return list(chain(lista_mcm, lista_cho, lista_tpm))

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
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    numero_orden = models.CharField(max_length=50, unique=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default=ESTADO_ACTIVA
    )
    tipo_mntn=models.CharField(max_length=50, null=True,blank=True)
    comentarios = models.TextField(blank=True, default='')
    # --- RELACIONES GENÉRICAS INVERSAS ---
    # Esto nos permite hacer "mi_orden.tecnicos.all()"
    asignaciones = GenericRelation('AsignacionUniversal')
    #tecnicos = GenericRelation('ItemTecnico', related_query_name='orden')
    #mesas = GenericRelation('ItemMesa', related_query_name='orden')
    #cavidades = GenericRelation('ItemCavidad', related_query_name='orden')
    #circuitos = GenericRelation('ItemCircuito', related_query_name='orden')
    #defectos = GenericRelation('ItemDefecto', related_query_name='orden')
    duracion_segundos = models.IntegerField(default=0) 
    ultima_actualizacion = models.DateTimeField(null=True, blank=True)
    lider = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='%(class)s_lideradas' # Esto evita conflictos de nombres
    )
    class Meta:
        abstract = True # No crea una tabla "OrdenBase" en la BD

    def __str__(self):
        return f"Orden {self.numero_orden,self.tipo_mntn}"
# --- 2. MODELOS DE ÓRDENES ESPECÍFICAS ---
class OrdenMCM(OrdenBase):
    defecto_sap = models.CharField(max_length=100)
    defecto_real = models.TextField()
    molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_mcm',db_constraint=False)
    status=models.CharField(max_length=5,blank=True, null=True)
    motivo_retorno = models.CharField(max_length=100, blank=True, null=True)
    observaciones_retorno = models.TextField(blank=True, null=True)
    orden_retorno_ref = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Número de la orden anterior que causó el retorno"
    )
    def __str__(self):
        return f"Orden MCM {self.numero_orden}"

class OrdenCHO(OrdenBase):
  status=models.CharField(max_length=5,blank=True, null=True) 
  molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_cho',db_constraint=False)
 
class OrdenTPM(OrdenBase):
    status=models.CharField(max_length=5,blank=True, null=True)
    molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_tpm',db_constraint=False)
    def __str__(self):
            return f"Orden TPM {self.numero_orden}"
class OrdenPREP(OrdenBase):
    status=models.CharField(max_length=5,blank=True, null=True)
    molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_prep',db_constraint=False)

class AsignacionUniversal(models.Model):
    # Conexión
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Datos
    nombre_tecnico = models.CharField(max_length=200) # OBLIGATORIO
    mesa = models.CharField(max_length=50, blank=True, null=True)     # OPCIONAL
    cavidad = models.CharField(max_length=255, blank=True, null=True)  # OPCIONAL
    circuito = models.CharField(max_length=255, blank=True, null=True) # OPCIONAL   
    activo = models.BooleanField(default=True) # True = Trabajando, False = Salió
    tipo_sistema = models.CharField(max_length=50, default='Estandar')
    defecto = models.CharField(max_length=255, blank=True, null=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    detalles_json = models.TextField(blank=True, null=True, default='[]')
    def __str__(self):
        status = "🟢" if self.activo else "🔴"
        return f"{status} {self.nombre_tecnico} en {self.content_object}"
    
    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
# --- 3. MODELOS GENÉRICOS RELACIONADOS ---
#class ItemTecnico(models.Model):
#    nombre = models.CharField(max_length=100) 
#    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#   object_id = models.PositiveIntegerField()
#    content_object = GenericForeignKey('content_type', 'object_id')
#    activo = models.BooleanField(default=True) # True = Trabajando, False = Ya salió
#    fecha_inicio = models.DateTimeField(auto_now_add=True)
#    fecha_fin = models.DateTimeField(null=True, blank=True)
#    def __str__(self):
#        return f"{self.nombre}"

#class ItemMesa(models.Model):
#    nombre = models.CharField(max_length=50) 
#    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#    object_id = models.PositiveIntegerField()
#    content_object = GenericForeignKey('content_type', 'object_id')

#    def __str__(self):
#        return f"{self.nombre}"

#class ItemCavidad(models.Model):
#    nombre = models.CharField(max_length=50)
#    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#    object_id = models.PositiveIntegerField()
#    content_object = GenericForeignKey('content_type', 'object_id')
#
#    def __str__(self):
#        return f"{self.nombre}"
    
#class ItemCircuito(models.Model):
#    nombre = models.CharField(max_length=50)
#    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#    object_id = models.PositiveIntegerField()
#    content_object = GenericForeignKey('content_type', 'object_id')

#    def __str__(self):
#        return f"{self.nombre}"
class OrdenSAP(models.Model):
    order = models.CharField(max_length=50, unique=True)      
    description = models.TextField(blank=True, null=True)    
    work_center = models.CharField(max_length=50, blank=True, null=True) 
    equipment = models.CharField(max_length=50, blank=True, null=True)  
    fecha_inicio = models.DateField(null=True, blank=True)
     

    def __str__(self):
        return self.order  
#class ItemDefecto(models.Model):
    # Relación Genérica (Para vincularlo a OrdenMCM o cualquier otra orden futura)
#    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
#    object_id = models.PositiveIntegerField()
#    content_object = GenericForeignKey('content_type', 'object_id')

    # El dato que guardamos
#    nombre = models.CharField(max_length=255)  # Aquí guardamos el nombre del defecto
#    fecha_registro = models.DateTimeField(auto_now_add=True)

 #   def __str__(self):
 #       return self.nombre
