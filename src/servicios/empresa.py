# src/servicios/empresa.py
from sqlalchemy.orm import Session
from src.modelos.entidades import Empresa

def configurar_empresa(db: Session, datos: dict):
    """
    Crea o actualiza los datos de la empresa.
    Solo puede haber UNA empresa en el sistema.
    """
    empresa_existente = db.query(Empresa).first()
    
    if empresa_existente:
        # Actualizar datos existentes
        for key, value in datos.items():
            if hasattr(empresa_existente, key):
                setattr(empresa_existente, key, value)
        mensaje = "Datos de empresa actualizados"
    else:
        # Crear nueva empresa
        empresa_existente = Empresa(**datos)
        db.add(empresa_existente)
        mensaje = "Empresa registrada exitosamente"
    
    try:
        db.commit()
        db.refresh(empresa_existente)
        return True, mensaje, empresa_existente
    except Exception as e:
        db.rollback()
        return False, f"Error: {str(e)}", None

def obtener_empresa(db: Session):
    """
    Obtiene los datos de la empresa configurada.
    Retorna None si no existe.
    """
    return db.query(Empresa).first()

def empresa_configurada(db: Session):
    """
    Verifica si ya existe una empresa configurada.
    """
    return db.query(Empresa).first() is not None
