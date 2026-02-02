"""
Funciones auxiliares compartidas entre generadores de reportes.
"""
from sqlalchemy.orm import Session
from src.modelos.entidades import Cuenta


def obtener_saldo_cuenta(db: Session, codigo_cuenta: str):
    """
    Calcula el saldo final de una cuenta o grupo de cuentas.
    Respeta correctamente la naturaleza de cada cuenta.
    
    Args:
        db: Sesión de base de datos
        codigo_cuenta: Código de cuenta (ej: "1" para todos los activos)
    
    Returns:
        float: Saldo total calculado según naturaleza
    """
    cuentas = db.query(Cuenta).filter(Cuenta.codigo.like(f"{codigo_cuenta}%")).all()
    saldo_total = 0.0
    
    for cuenta in cuentas:
        if not cuenta.detalles:
            continue
        
        debe = sum(d.debe for d in cuenta.detalles)
        haber = sum(d.haber for d in cuenta.detalles)
        
        # Respetar la naturaleza de la cuenta
        if cuenta.naturaleza.upper() == 'DEUDORA':
            # Para cuentas deudoras: DEBE aumenta, HABER disminuye
            saldo_total += (debe - haber)
        else:  # ACREEDORA
            # Para cuentas acreedoras: HABER aumenta, DEBE disminuye
            saldo_total += (haber - debe)
    
    return saldo_total


def obtener_cuentas_con_saldo_detallado(db: Session, prefijo: str, styles):
    """
    Obtiene las cuentas con saldo de un grupo específico.
    
    Args:
        db: Sesión de base de datos
        prefijo: Prefijo del código de cuenta (ej: "1", "2", "3")
        styles: Estilos de reportlab para formateo
    
    Returns:
        tuple: (lista_filas, total_grupo)
    """
    from reportlab.platypus import Paragraph
    
    cuentas = db.query(Cuenta).filter(
        Cuenta.codigo.like(f"{prefijo}%")
    ).order_by(Cuenta.codigo).all()
    
    lista_resultado = []
    total_grupo = 0.0
    
    for c in cuentas:
        if not c.detalles:
            continue
        
        debe = sum(d.debe for d in c.detalles)
        haber = sum(d.haber for d in c.detalles)
        
        # Calcular saldo según naturaleza
        if c.naturaleza.upper() == 'DEUDORA':
            saldo = debe - haber
        else:  # ACREEDORA
            saldo = haber - debe
        
        # Solo incluir si tiene saldo significativo
        if abs(saldo) > 0.01:
            # Indentación visual según nivel de cuenta
            nivel = c.codigo.count('.')
            indent = "  " * nivel
            nombre_indentado = f"{indent}{c.nombre}"
            
            lista_resultado.append([
                c.codigo,
                Paragraph(nombre_indentado, styles['Normal']),
                f"{saldo:,.2f}"
            ])
            total_grupo += saldo
    
    return lista_resultado, total_grupo
