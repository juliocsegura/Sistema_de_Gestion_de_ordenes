# This is an auto-generated Django model module.

# You'll have to do the following manually to clean this up:

#   * Rearrange models' order

#   * Make sure each model has one field with primary_key=True

#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior

#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table

# Feel free to rename the models, but don't rename db_table values or field names.

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
STATUS_PRODUCCION = 'produccion'
STATUS_MANTENIMIENTO = 'mantenimiento'
STATUS_DISPONIBLE = 'disponible'
STATUS_PREPARACION = 'preparacion'
STATUS_CHOICES = [
    (STATUS_PRODUCCION, 'En Producción'),
    (STATUS_MANTENIMIENTO, 'En Mantenimiento'),
    (STATUS_DISPONIBLE, 'Disponible'),
    (STATUS_PREPARACION, 'Falta Preparacion'),
]



class Eoats(models.Model):

    id_eoat = models.AutoField(primary_key=True)

    numero_eoat = models.CharField(max_length=100, unique=True, blank=True, null=True)

    locacion = models.CharField(db_column='Locacion', max_length=100, blank=True, null=True)  # Field name made lowercase. This field type is a guess.
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PREPARACION,
        null=True,
        blank=True
      )
    class Meta:

        managed = False

        db_table = 'eoats'
  
    def get_status_css_class(self):
        if self.status == STATUS_PRODUCCION:
            return 'bg-blue-100 text-blue-800'
        elif self.status == STATUS_MANTENIMIENTO:
            return 'bg-yellow-100 text-yellow-800'
        elif self.status == STATUS_DISPONIBLE:
            return 'bg-green-100 text-green-800'
        elif self.status== STATUS_PREPARACION:
            return 'bg-red-100 text-red-800'
        return 'bg-gray-100 text-gray-800'

class FotoEoat(models.Model):
    # El EOAT al que pertenece esta foto
    eoat_fotos = models.ForeignKey(Eoats, 
        on_delete=models.CASCADE, 
        related_name= 'fotos'  # ¡Este nombre es clave!
    )
    
    # El campo para subir la imagen
    imagen = models.ImageField(upload_to='Eoats/')
    descripcion = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Foto de {self.eoat_fotos.numero_eoat}"



class Preventivos(models.Model):

    id_preventivo = models.AutoField(primary_key=True)

    semana = models.IntegerField(blank=True, null=True)

    eoat = models.TextField(blank=True, null=True)

    locacion = models.TextField(blank=True, null=True)

    tipo = models.TextField(blank=True, null=True )

    fecha_preventivo = models.DateTimeField(auto_now_add=True,blank=True, null=True)

    comentarios = models.TextField(blank=True, null=True)

    numero_orden = models.CharField(max_length=100,blank=True, null=True)

    antes = models.TextField(blank=True, null=True)

    despues = models.TextField(blank=True, null=True)



    class Meta:

        managed = False
        ordering = ['-fecha_preventivo']

        db_table = 'preventivos'





class Refacciones(models.Model):

    id_refaccion = models.AutoField(primary_key=True)

    numero_sap = models.CharField(db_column='numero_SAP', max_length=100,blank=True, null=True)  # Field name made lowercase.

    numero_proveedor = models.CharField(max_length=100, blank=True, null=True)

    descripcion = models.TextField(blank=True, null=True)

    proveedor = models.CharField(blank=True, null=True)

    min = models.IntegerField(blank=True, null=True)

    max = models.IntegerField(blank=True, null=True)

    locacion = models.CharField(max_length=100,blank=True, null=True)

    disponible = models.IntegerField(blank=True, null=True)

    cu = models.FloatField( blank=True, null=True)

    moneda = models.CharField(max_length=100,blank=True, null=True)



    class Meta:

        managed = False

        db_table = 'refacciones'

class Movimientos(models.Model):
   eoat = models.ForeignKey(Eoats, on_delete=models.CASCADE, related_name='movimientos')
   usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
   estado_anterior = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
   estado_nuevo = models.CharField(max_length=20, choices=STATUS_CHOICES)
   comentarios = models.TextField(blank=True, null=True)
   fecha = models.DateTimeField(auto_now_add=True)

   class Meta:
       
        ordering = ['-fecha']

   def __str__(self):
        return f"{self.eoat.numero_eoat}: {self.estado_anterior} -> {self.estado_nuevo}"
  
class RegistroPlanCargado(models.Model):
    """
    Almacena los datos PROCESADOS del archivo Excel/CSV cargado.
    Incluye el molde transformado y el status de mantenimiento.
    """
    id = models.AutoField(primary_key=True)
    maquina = models.CharField(max_length=100, blank=True, null=True)
    
    # Almacenará el molde transformado (ej. 21-12345)
    molde = models.CharField(max_length=100, blank=True, null=True) 
    
    fecha = models.DateField(blank=True, null=True)
    
    # Campo de Status añadido
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PREPARACION,
        
    )
    
    fecha_carga = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Carga")

    class Meta:
        verbose_name = "Registro de Plan Cargado"
        verbose_name_plural = "Registros de Planes Cargados"
        ordering = ['maquina', 'molde']

    def get_status_css_class(self):
        """ Copiamos la lógica de Eoats para mostrar colores en la plantilla """
        if self.status == STATUS_PRODUCCION:
            return 'bg-blue-100 text-blue-800'
        elif self.status == STATUS_MANTENIMIENTO:
            return 'bg-yellow-100 text-yellow-800'
        elif self.status == STATUS_DISPONIBLE:
            return 'bg-green-100 text-green-800'
        elif self.status == STATUS_PREPARACION:
            return 'bg-red-100 text-red-800'
        return 'bg-gray-100 text-gray-800'

    def __str__(self):
        return f"Registro: {self.molde} ({self.status}) en {self.maquina} para {self.fecha}"
@receiver(post_save, sender=Eoats)
def limpiar_plan_al_terminar(sender, instance, **kwargs):
    """
    Esta función se ejecuta automáticamente DESPUÉS de que se guarda un EOAT.
    Si el estado del EOAT guardado es 'DISPONIBLE', busca en la tabla
    de registros del plan y borra la entrada correspondiente.
    """
    
    # Comprobamos si el estado del EOAT que se guardó es DISPONIBLE
    if instance.status == STATUS_DISPONIBLE:
        try:
            # Buscamos el registro en el plan que coincida con el número de EOAT
            registro_a_borrar = RegistroPlanCargado.objects.filter(molde=instance.numero_eoat)
            
            if registro_a_borrar.exists():
                # Borramos el registro del plan
                registro_a_borrar.delete()
                print(f"Señal: EOAT {instance.numero_eoat} pasó a DISPONIBLE. Registro del plan eliminado.")
                
        except RegistroPlanCargado.DoesNotExist:
            # No se encontró, no hacemos nada
            pass
        except Exception as e:
            # Imprime cualquier otro error en la consola del servidor
            print(f"Error en la señal limpiar_plan_al_terminar: {e}")
