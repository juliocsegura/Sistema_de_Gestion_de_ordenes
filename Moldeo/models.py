from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from itertools import chain 
from django.contrib.auth.models import User

class Lideres(models.Model):
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True) # Para mostrar/ocultar en dropdowns
    id_empleado = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Líder"
        verbose_name_plural = "Líderes"

class Moldmakers(models.Model): # Técnicos
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)
    num_empleado = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Técnico (Moldmaker)"
        verbose_name_plural = "Técnicos (Moldmakers)"

# --- 1. CATÁLOGO DE MÁQUINAS ---
class Maquinas(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Máquina"
        verbose_name_plural = "Máquinas"


# --- 2. CATÁLOGO DE MOLDES ---
class Moldes(models.Model):
    # Ejemplo CSV: M1046113
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Número de Molde")
    
    # Ejemplo CSV: 21-1046113-00000
    molde_sap = models.CharField(max_length=100, blank=True, null=True, verbose_name="Molde SAP")
    
    # Ejemplo CSV: OTROS, 2P, 4P
    proyecto = models.CharField(max_length=100, blank=True, null=True)
    
    # Ejemplo CSV: 4, 8, 16
    cavidades = models.IntegerField(default=0, blank=True, null=True)
    
    # Relación: Un molde se asigna a una Máquina (puede ser null si no está asignado)
    maquina = models.ForeignKey(
        Maquinas, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='moldes'
    )
    
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.molde_sap})"

    class Meta:
        verbose_name = "Molde"
        verbose_name_plural = "Moldes"


# --- 3. NÚMEROS DE PARTE (Relación Uno a Muchos con Molde) ---
class NumerosParte(models.Model):
    # Ejemplo CSV: 2203460-1
    numero_parte = models.CharField(max_length=100)
    
    # Relación: Este número de parte pertenece a ESTE molde.
    # related_name='numeros_parte' permite acceder desde el molde: molde.numeros_parte.all()
    molde = models.ForeignKey(
        Moldes, 
        on_delete=models.CASCADE, 
        related_name='numeros_parte'
    )

    def __str__(self):
        return self.numero_parte

    class Meta:
        verbose_name = "Número de Parte"
        verbose_name_plural = "Números de Parte"


# --- 4. CATÁLOGO DE DEFECTOS ---
class Defectos(models.Model):
    # Ejemplo CSV: ARRASTRE
    nombre_defecto = models.CharField(max_length=200, unique=True)
    
    # Ejemplo CSV: Drag Mark (Main Activity)
    categoria_ingles = models.CharField(max_length=200, blank=True, null=True, verbose_name="Categoría (Inglés)")
    
    # Ejemplo CSV: 110 (ESTATUS)
    codigo_estatus = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código Estatus")
    
    # Ejemplo CSV: CAMBIO DE CONFIGURACION (ACTIVIDAD)
    actividad_asociada = models.TextField(blank=True, null=True, verbose_name="Actividad Asociada")

    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre_defecto

    class Meta:
        verbose_name = "Defecto"
        verbose_name_plural = "Defectos"

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
    motivo_retorno = models.CharField(max_length=100, blank=True, null=True)
    observaciones_retorno = models.TextField(blank=True, null=True)
    orden_retorno_ref = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Número de la orden anterior que causó el retorno"
    )
    defecto_sap = models.CharField(max_length=100)
    maquina = models.CharField(max_length=50, blank=True, null=True)
    class Meta:
        abstract = True # No crea una tabla "OrdenBase" en la BD

    def __str__(self):
        return f"Orden {self.numero_orden,self.tipo_mntn}"
# --- 2. MODELOS DE ÓRDENES ESPECÍFICAS ---
class OrdenMCM(OrdenBase):
    
    defecto_real = models.TextField()
    molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_mcm',db_constraint=False)
    status=models.CharField(max_length=5,blank=True, null=True)
   
    def __str__(self):
        return f"Orden MCM {self.numero_orden}"

class OrdenCHO(OrdenBase):
  status=models.CharField(max_length=5,blank=True, null=True) 
  molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_cho',db_constraint=False)
  parte_saliente = models.CharField(max_length=100, blank=True, null=True)
  parte_entrante = models.CharField(max_length=100, blank=True, null=True)
  tipo_tarjeta = models.CharField(max_length=10, default='verde', choices=[('verde', 'Verde'), ('roja', 'Roja')])
 
class OrdenTPM(OrdenBase):
    status=models.CharField(max_length=5,blank=True, null=True)
    molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_tpm',db_constraint=False)
    tipo_tarjeta = models.CharField(max_length=10, default='verde', choices=[('verde', 'Verde'), ('roja', 'Roja')])
    def __str__(self):
            return f"Orden TPM {self.numero_orden}"
class OrdenPREP(OrdenBase):
    status=models.CharField(max_length=5,blank=True, null=True)
    molde =models.ForeignKey(Moldes, on_delete=models.SET_NULL,null=True,blank=True,related_name='ordenes_prep',db_constraint=False)
    tipo_tarjeta = models.CharField(max_length=10, default='verde', choices=[('verde', 'Verde'), ('roja', 'Roja')])
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
    hora_inicio = models.TimeField(null=True, blank=True)

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
