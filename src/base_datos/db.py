# src/base_datos/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Nombre de la base de datos
DB_NAME = "datos/contabilidad.sqlite"

# Asegurar que el directorio datos existe
if not os.path.exists("datos"):
    os.makedirs("datos")

# Crear motor de conexión
engine = create_engine(f"sqlite:///{DB_NAME}", echo=False)

# Crear sesión para interactuar con la BD
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para los modelos
Base = declarative_base()

def get_db():
    """Generador de sesiones de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Crea las tablas en la base de datos"""
    Base.metadata.create_all(bind=engine)

def close_engine():
    """Cierra todas las conexiones del motor para liberar el archivo."""
    engine.dispose()