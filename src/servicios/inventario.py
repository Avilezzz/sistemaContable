from datetime import date
from sqlalchemy.orm import Session
from src.modelos.entidades import Producto, MovimientoInventario
from src.servicios.contabilidad import registrar_asiento



# === Cuentas contables (DEMO) ===
CTA_INVENTARIO = "1.1.03.01"     # Inventario productos terminados (ajusta si tu plan tiene otro)
CTA_CAJA = "1.1.01.01"           # Caja
CTA_BANCOS = "1.1.01.02"         # Bancos (opcional)
CTA_CLIENTES = "1.1.02.01"       # Clientes (CxC)
CTA_PROVEEDORES = "2.1.01.01"    # Proveedores (CxP)
CTA_VENTAS = "4.1.01"            # Ventas productos terminados
CTA_COSTO_VENTAS = "5.1.01"      # Para demo como “costo de ventas” (si tu plan tiene otra mejor, cámbiala)


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

def registrar_compra_con_asiento(
    db: Session,
    codigo_prod: str,
    fecha: date,
    cantidad: int,
    costo_unit: float,
    es_credito: bool = False
):
    ok, msg = registrar_compra(db, codigo_prod, fecha, cantidad, costo_unit)
    if not ok:
        return False, msg

    total = cantidad * costo_unit

    # Compra contado => Haber Caja. Compra crédito => Haber Proveedores.
    cuenta_haber = CTA_PROVEEDORES if es_credito else CTA_CAJA

    movimientos = [
        {"cuenta_codigo": CTA_INVENTARIO, "debe": total, "haber": 0.0},
        {"cuenta_codigo": cuenta_haber,   "debe": 0.0,  "haber": total},
    ]

    ok2, msg2 = registrar_asiento(
        db,
        fecha,
        f"Compra inventario {codigo_prod} x{cantidad} (sin IVA)",
        movimientos
    )
    if not ok2:
        return False, f"Compra OK, pero asiento falló: {msg2}"

    return True, "Compra + asiento registrados."

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
    
    return True, "Venta registrada.", costo_total_salida

def registrar_venta_con_asientos(
    db: Session,
    codigo_prod: str,
    fecha: date,
    cantidad: int,
    precio_unit_venta: float,
    es_credito: bool = False
):
    # 1) Registrar salida inventario y obtener costo real (según tu lógica)
    ok, msg, costo_total = registrar_venta(db, codigo_prod, fecha, cantidad)
    if not ok:
        return False, msg

    total_venta = cantidad * precio_unit_venta

    # 2) Asiento de INGRESO
    cuenta_debe = CTA_CLIENTES if es_credito else CTA_CAJA
    mov_ingreso = [
        {"cuenta_codigo": cuenta_debe, "debe": total_venta, "haber": 0.0},
        {"cuenta_codigo": CTA_VENTAS,  "debe": 0.0,        "haber": total_venta},
    ]
    ok1, msg1 = registrar_asiento(
        db,
        fecha,
        f"Venta {codigo_prod} x{cantidad} (sin IVA) {'CRÉDITO' if es_credito else 'CONTADO'}",
        mov_ingreso
    )
    if not ok1:
        return False, f"Venta OK, pero asiento de ingreso falló: {msg1}"

    # 3) Asiento de COSTO (COGS)
    mov_costo = [
        {"cuenta_codigo": CTA_COSTO_VENTAS, "debe": costo_total, "haber": 0.0},
        {"cuenta_codigo": CTA_INVENTARIO,   "debe": 0.0,        "haber": costo_total},
    ]
    ok2, msg2 = registrar_asiento(
        db,
        fecha,
        f"Costo de venta {codigo_prod} x{cantidad}",
        mov_costo
    )
    if not ok2:
        return False, f"Asiento ingreso OK, pero costo falló: {msg2}"

    return True, "Venta + asientos (ingreso y costo) registrados."
