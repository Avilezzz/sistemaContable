from datetime import date
from sqlalchemy.orm import Session
from src.modelos.entidades import Producto, MovimientoInventario

def crear_producto(db: Session, codigo: str, nombre: str):
    """
    Crea un producto neutro. 
    Ya no se define un método de valuación aquí.
    """
    # Se guarda con un valor por defecto interno, pero el reporte ignorará esto.
    p = Producto(codigo=codigo, nombre=nombre, metodo="NEUTRO")
    db.add(p)
    db.commit()
    return p

def registrar_compra(db: Session, codigo_prod: str, fecha: date, cantidad: int, costo_unit: float):
    """Registra una entrada al inventario"""
    prod = db.query(Producto).filter(Producto.codigo == codigo_prod).first()
    if not prod: return False, "Producto no existe"

    total = cantidad * costo_unit
    
    nuevo_mov = MovimientoInventario(
        producto_id=prod.id,
        fecha=fecha,
        tipo='COMPRA',
        cantidad=cantidad,
        costo_unitario=costo_unit,
        costo_total=total,
        saldo_cantidad=cantidad  # Mantenemos el saldo por lote para que el reporte FIFO sea posible
    )
    
    db.add(nuevo_mov)
    db.commit()
    return True, "Compra registrada exitosamente."

def registrar_venta(db: Session, codigo_prod: str, fecha: date, cantidad: int):
    """
    Registra una salida. 
    Usamos la lógica de lotes para actualizar la disponibilidad en la BD, 
    permitiendo que los reportes recalculen el costo según el método elegido.
    """
    prod = db.query(Producto).filter(Producto.codigo == codigo_prod).first()
    if not prod: return False, "Producto no existe"

    # 1. Validación de Stock Total
    # Sumamos el saldo disponible en todos los lotes de compra
    stock_actual = db.query(MovimientoInventario).filter(
        MovimientoInventario.producto_id == prod.id,
        MovimientoInventario.tipo == 'COMPRA'
    ).with_entities(MovimientoInventario.saldo_cantidad).all()
    
    total_disponible = sum(s[0] for s in stock_actual)
    
    if cantidad > total_disponible:
        return False, f"Stock insuficiente. Disponible: {total_disponible}"

    # 2. Consumo de lotes (Lógica base para la BD)
    # Buscamos lotes con saldo, del más antiguo al más nuevo
    cantidad_pendiente = cantidad
    costo_total_salida = 0.0
    
    lotes = db.query(MovimientoInventario)\
              .filter(MovimientoInventario.producto_id == prod.id)\
              .filter(MovimientoInventario.tipo == 'COMPRA')\
              .filter(MovimientoInventario.saldo_cantidad > 0)\
              .order_by(MovimientoInventario.fecha.asc(), MovimientoInventario.id.asc())\
              .all()

    for lote in lotes:
        if cantidad_pendiente == 0: break
        
        tomar = min(cantidad_pendiente, lote.saldo_cantidad)
        costo_total_salida += tomar * lote.costo_unitario
        
        lote.saldo_cantidad -= tomar
        cantidad_pendiente -= tomar

    # 3. Registrar el movimiento de Venta
    # El costo_unitario guardado es un promedio de la operación para el Libro Diario
    costo_unitario_operacion = costo_total_salida / cantidad

    venta = MovimientoInventario(
        producto_id=prod.id,
        fecha=fecha,
        tipo='VENTA',
        cantidad=cantidad,
        costo_unitario=costo_unitario_operacion,
        costo_total=costo_total_salida,
        saldo_cantidad=0
    )
    
    db.add(venta)
    db.commit()
    
    return True, "Venta registrada."