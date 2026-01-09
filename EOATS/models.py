from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

# --- DEFINICIÓN DE ESTATUS ---
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

# --- MODELO EOATS ---
class Eoats(models.Model):
    id_eoat = models.AutoField(primary_key=True)
    numero_eoat = models.CharField(max_length=100, unique=True, blank=True, null=True)
    locacion = models.CharField(db_column='Locacion', max_length=100, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PREPARACION
    )
    codigo_barras = models.ImageField(
        upload_to='codigos_eoat/',
        blank=True, 
        null=True,
        editable=False
    )

    class Meta:
        managed = True  # Ahora Django administra esta tabla
        db_table = 'eoats'

    def save(self, *args, **kwargs):
        # Generación de código de barras
        # if self.numero_eoat and self.numero_eoat.strip():
        #     buffer = BytesIO()
        #     codigo = barcode.get('code128', self.numero_eoat, writer=ImageWriter())
        #     codigo.write(buffer, options={"write_text": True})
        #     file_name = f'{self.numero_eoat}.png'
        #     # self.codigo_barras.save(file_name, File(buffer), save=False)
        super().save(*args, **kwargs)

    def get_status_css_class(self):
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
        return self.numero_eoat if self.numero_eoat else "EOAT sin número"

# --- FOTOS EOAT ---
class FotoEoat(models.Model):
    # IMPORTANTE: Usamos 'Eoats' como string para evitar NameError
    eoat_fotos = models.ForeignKey('Eoats', on_delete=models.CASCADE, related_name='fotos')
    imagen = models.ImageField(upload_to='Eoats/')
    descripcion = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Foto de {self.eoat_fotos.numero_eoat}"

# --- PREVENTIVOS ---
class Preventivos(models.Model):
    id_preventivo = models.AutoField(primary_key=True)
    semana = models.IntegerField(blank=True, null=True)
    eoat = models.TextField(blank=True, null=True)
    locacion = models.TextField(blank=True, null=True)
    tipo = models.TextField(blank=True, null=True )
    fecha_preventivo = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    comentarios = models.TextField(blank=True, null=True)
    numero_orden = models.CharField(max_length=100, blank=True, null=True)
    antes = models.TextField(blank=True, null=True)
    despues = models.TextField(blank=True, null=True)
    maquina = models.CharField(max_length=100, blank=True, null=True)
    retorno = models.CharField(max_length=100, blank=True, null=True)
    retorno_info = models.CharField(max_length=100, blank=True, null=True)
    tecnico = models.CharField(max_length=100, blank=True, null=True)
    hora_paro = models.CharField(max_length=100, blank=True, null=True)
    hora_entrega = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True
        ordering = ['-fecha_preventivo']
        db_table = 'preventivos'

# --- REFACCIONES ---
class Refacciones(models.Model):
    id_refaccion = models.AutoField(primary_key=True)
    numero_sap = models.CharField(db_column='numero_SAP', max_length=100, blank=True, null=True)
    numero_proveedor = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    proveedor = models.CharField(blank=True, null=True)
    min = models.IntegerField(blank=True, null=True)
    max = models.IntegerField(blank=True, null=True)
    locacion = models.CharField(max_length=100, blank=True, null=True)
    disponible = models.IntegerField(blank=True, null=True)
    cu = models.FloatField(blank=True, null=True)
    moneda = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = True  # Ahora Django administra esta tabla
        db_table = 'refacciones'

# --- MOVIMIENTOS ---
class Movimientos(models.Model):
    # IMPORTANTE: Usamos 'Eoats' como string
    eoat = models.ForeignKey('Eoats', on_delete=models.CASCADE, related_name='movimientos')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    estado_anterior = models.CharField(max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    estado_nuevo = models.CharField(max_length=20, choices=STATUS_CHOICES)
    comentarios = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.eoat.numero_eoat}: {self.estado_anterior} -> {self.estado_nuevo}"

# --- PLAN DE CARGA ---
class RegistroPlanCargado(models.Model):
    id = models.AutoField(primary_key=True)
    maquina = models.CharField(max_length=100, blank=True, null=True)
    molde = models.CharField(max_length=100, blank=True, null=True) 
    fecha = models.DateField(blank=True, null=True)
    tipo_plan = models.CharField(max_length=10, blank=True, null=True, default='PREP')
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
        return f"Registro: {self.molde} - {self.tipo_plan} ({self.status}) en {self.maquina} para {self.fecha}"

# --- SEÑALES (SIGNALS) ---
@receiver(post_save, sender=Eoats)
def limpiar_plan_al_terminar(sender, instance, **kwargs):
    if instance.status == STATUS_DISPONIBLE:
        try:
            registro_a_borrar = RegistroPlanCargado.objects.filter(molde=instance.numero_eoat)
            if registro_a_borrar.exists():
                registro_a_borrar.delete()
                print(f"Señal: EOAT {instance.numero_eoat} pasó a DISPONIBLE. Registro del plan eliminado.")
        except Exception as e:
            print(f"Error en la señal limpiar_plan_al_terminar: {e}")