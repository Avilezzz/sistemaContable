import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from src.modelos.entidades import Cuenta, Asiento, DetalleAsiento
import os
from datetime import date

def importar_plan_cuentas_desde_excel(ruta_archivo: str, db: Session):
    """
    Lee un archivo Excel con MÚLTIPLES HOJAS y carga las cuentas en la base de datos.
    Une todas las hojas en una sola lista antes de procesar.
    """
    if not os.path.exists(ruta_archivo):
        return False, f"El archivo '{ruta_archivo}' no existe."

    try:
        # 1. LEER TODAS LAS HOJAS
        # sheet_name=None hace que pandas lea todas las pestañas y devuelva un diccionario
        xls_dict = pd.read_excel(ruta_archivo, sheet_name=None, dtype={'CÓDIGO': str})
        
        # 2. UNIR TODAS LAS HOJAS
        # pd.concat toma todas las hojas leídas y crea una sola tabla gigante
        df = pd.concat(xls_dict.values(), ignore_index=True)
        
        # Limpiar nombres de columnas (quitar espacios y poner mayúsculas)
        df.columns = [str(c).upper().strip() for c in df.columns]
        
        # Validar que existan las columnas obligatorias
        cols_requeridas = ['CÓDIGO', 'NOMBRE', 'TIPO', 'NATURALEZA']
        if not all(col in df.columns for col in cols_requeridas):
            return False, f"Todas las hojas del Excel deben tener las columnas: {cols_requeridas}"

        cuentas_importadas = 0
        
        for _, row in df.iterrows():
            # Saltamos filas vacías si las hay (común al unir hojas)
            if pd.isna(row['CÓDIGO']) or pd.isna(row['NOMBRE']):
                continue

            codigo = str(row['CÓDIGO']).strip()
            
            # Verificar si la cuenta ya existe para no duplicar
            cuenta_existente = db.query(Cuenta).filter(Cuenta.codigo == codigo).first()
            
            if not cuenta_existente:
                nueva_cuenta = Cuenta(
                    codigo=codigo,
                    nombre=str(row['NOMBRE']).strip(),
                    tipo=str(row['TIPO']).strip(),
                    naturaleza=str(row['NATURALEZA']).strip()
                )
                db.add(nueva_cuenta)
                cuentas_importadas += 1
        
        db.commit()
        return True, f"Proceso completado. Se importaron {cuentas_importadas} cuentas de todas las hojas."

    except Exception as e:
        db.rollback()
        return False, f"Error crítico al importar: {str(e)}"

def registrar_asiento(db: Session, fecha: date, descripcion: str, movimientos: list):
    """
    Registra un asiento contable validando partida doble.
    movimientos: lista de diccionarios [{'cuenta_codigo': str, 'debe': float, 'haber': float}]
    """
    # 1. Validación de Partida Doble
    total_debe = sum(m['debe'] for m in movimientos)
    total_haber = sum(m['haber'] for m in movimientos)
    
    # Usamos round para evitar errores de punto flotante
    if round(total_debe, 2) != round(total_haber, 2):
        return False, f"Descuadrado: Debe (${total_debe}) != Haber (${total_haber})"

    try:
        # 2. Crear Cabecera del Asiento
        nuevo_asiento = Asiento(fecha=fecha, descripcion=descripcion)
        db.add(nuevo_asiento)
        db.flush() # Para obtener el ID del asiento antes de commit

        # 3. Crear Detalles
        for mov in movimientos:
            # Buscar la cuenta por código
            cuenta = db.query(Cuenta).filter(Cuenta.codigo == mov['cuenta_codigo']).first()
            if not cuenta:
                db.rollback()
                return False, f"La cuenta código '{mov['cuenta_codigo']}' no existe."

            detalle = DetalleAsiento(
                asiento_id=nuevo_asiento.id,
                cuenta_id=cuenta.id,
                debe=mov['debe'],
                haber=mov['haber']
            )
            db.add(detalle)

        db.commit()
        return True, f"Asiento registrado correctamente. ID: {nuevo_asiento.id}"

    except Exception as e:
        db.rollback()
        return False, f"Error al guardar: {str(e)}"