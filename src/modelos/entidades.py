# src/modelos/entidades.py
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from src.base_datos.db import Base

class Cuenta(Base):
    __tablename__ = "cuentas"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)       # Activo, Pasivo, Patrimonio, etc.
    naturaleza = Column(String, nullable=False) # Deudora, Acreedora
    
    # Relación para ver los movimientos de esta cuenta
    detalles = relationship("DetalleAsiento", back_populates="cuenta")

    def __repr__(self):
        return f"<Cuenta {self.codigo} - {self.nombre}>"

class Asiento(Base):
    __tablename__ = "asientos"

    id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False)
    descripcion = Column(String, nullable=False)
    
    # Relación: Un asiento tiene muchos detalles (líneas)
    detalles = relationship("DetalleAsiento", back_populates="asiento", cascade="all, delete-orphan")

class DetalleAsiento(Base):
    __tablename__ = "detalles_asiento"

    id = Column(Integer, primary_key=True, index=True)
    asiento_id = Column(Integer, ForeignKey("asientos.id"), nullable=False)
    cuenta_id = Column(Integer, ForeignKey("cuentas.id"), nullable=False)
    
    debe = Column(Float, default=0.0)
    haber = Column(Float, default=0.0)

    # Relaciones inversas
    asiento = relationship("Asiento", back_populates="detalles")
    cuenta = relationship("Cuenta", back_populates="detalles")

# --- Agregar al final de src/modelos/entidades.py ---

class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True, nullable=False)
    nombre = Column(String, nullable=False)
    metodo = Column(String, default="FIFO") # FIFO o PMP (Promedio)
    
    # Relación
    movimientos = relationship("MovimientoInventario", back_populates="producto", cascade="all, delete-orphan")

class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)
    fecha = Column(Date, nullable=False)
    tipo = Column(String, nullable=False) # 'COMPRA' o 'VENTA'
    
    cantidad = Column(Integer, nullable=False)
    costo_unitario = Column(Float, nullable=False)
    costo_total = Column(Float, nullable=False)
    
    # Campos exclusivos para control FIFO
    # saldo_cantidad: Cuánto queda de ESTE lote de compra específico
    saldo_cantidad = Column(Integer, default=0) 
    
    producto = relationship("Producto", back_populates="movimientos")

# Al final de src/modelos/entidades.py, después de MovimientoInventario

class Empresa(Base):
    __tablename__ = "empresa"
    
    id = Column(Integer, primary_key=True, index=True)
    ruc = Column(String, unique=True, nullable=False)  # RUC o identificación fiscal
    nombre = Column(String, nullable=False)
    nombre_comercial = Column(String)
    direccion = Column(String)
    telefono = Column(String)
    email = Column(String)
    ciudad = Column(String, default="Babahoyo")
    pais = Column(String, default="Ecuador")
    
    def __repr__(self):
        return f"<Empresa {self.nombre}>"
