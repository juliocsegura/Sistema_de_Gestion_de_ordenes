# EOATS/management/commands/clean_data.py

from django.core.management.base import BaseCommand
from django.db import connection # Importamos la conexión directa a la BD

class Command(BaseCommand):
    help = 'Replaces "nan" string with NULL in Refacciones numerical fields using raw SQL.'

    def handle(self, *args, **kwargs):
        # El nombre de la tabla en la base de datos es 'nombreapp_nombremodelo'
        table_name = 'refacciones'
        
        # IMPORTANTE: Revisa que estos sean los nombres exactos de las columnas en tu BD
        # Si tus campos en models.py se llaman 'stock_actual' y 'costo', estos son los nombres correctos.
        columns_to_clean = ['cu', 'min', 'max''numero_SAP','numero_proveedor','descripcion','proveedor','locacion',
                            'disponible','moneda'] 
        self.stdout.write(f"Starting raw SQL data cleaning for table '{table_name}'...")

        try:
            # Creamos un 'cursor'. Es como un puntero para ejecutar comandos en la BD
            with connection.cursor() as cursor:
                total_rows_affected = 0
                for column in columns_to_clean:
                    # Esta es la consulta SQL. Le decimos:
                    # "Actualiza la tabla, pon la columna a NULL donde sea igual al texto 'nan'"
                    sql_query = f"UPDATE {table_name} SET {column} = NULL WHERE {column} = 'nan','None';"
                    
                    self.stdout.write(f"Executing: {sql_query}")
                    cursor.execute(sql_query)
                    
                    # cursor.rowcount nos dice cuántas filas se modificaron
                    rows_affected = cursor.rowcount
                    total_rows_affected += rows_affected
                    self.stdout.write(self.style.SUCCESS(f" -> Cleaned {rows_affected} records in column '{column}'."))

            if total_rows_affected == 0:
                self.stdout.write(self.style.WARNING("No records with 'nan' found to clean."))
            else:
                self.stdout.write(self.style.SUCCESS(f"\nFinished cleaning. Total rows affected: {total_rows_affected}."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
            self.stdout.write(self.style.WARNING("Please check if the table and column names are correct."))