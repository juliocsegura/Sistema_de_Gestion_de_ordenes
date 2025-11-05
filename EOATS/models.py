# This is an auto-generated Django model module.

# You'll have to do the following manually to clean this up:

#   * Rearrange models' order

#   * Make sure each model has one field with primary_key=True

#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior

#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table

# Feel free to rename the models, but don't rename db_table values or field names.

from django.db import models
from django.contrib.auth.models import User
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
  