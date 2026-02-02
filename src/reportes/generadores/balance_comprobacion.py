"""
Generador de Balance de Comprobación de Sumas y Saldos.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from src.modelos.entidades import Cuenta,Asiento
from src.servicios.empresa import obtener_empresa
from src.reportes.encabezado import crear_encabezado_empresa

def generar_balance_comprobacion(db: Session, nombre_archivo="balance_comprobacion.pdf"):
    """
    Genera el Balance de Comprobación de Sumas y Saldos.
    Verifica que (Sumas Debe == Sumas Haber) y (Saldo Deudor == Saldo Acreedor).
    """
    # 1. OBTENER EMPRESA Y PERÍODO
    empresa = obtener_empresa(db)
    asientos = db.query(Asiento).order_by(Asiento.fecha).all()
    
    fecha_inicio = asientos[0].fecha if asientos else None
    fecha_fin = asientos[-1].fecha if asientos else None

    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # 2. AGREGAR ENCABEZADO PROFESIONAL
    if empresa:
        elements.extend(
            crear_encabezado_empresa(
                empresa,
                "BALANCE DE COMPROBACIÓN",
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                moneda="USD"
            )
        )
    else:
        elements.append(Paragraph("BALANCE DE COMPROBACIÓN", styles['Title']))
        elements.append(Spacer(1, 12))
    
    # 2. Encabezados de Tabla
    data = [[
        'CÓDIGO', 'CUENTA',
        'SUMAS\nDEBE', 'SUMAS\nHABER',
        'SALDO\nDEUDOR', 'SALDO\nACREEDOR'
    ]]
    
    # 3. Variables para Totales Globales
    total_sum_debe = 0.0
    total_sum_haber = 0.0
    total_sal_deudor = 0.0
    total_sal_acreedor = 0.0
    
    # 4. Procesar Cuentas
    cuentas = db.query(Cuenta).order_by(Cuenta.codigo).all()
    hay_datos = False
    
    for cuenta in cuentas:
        if not cuenta.detalles:
            continue
        
        hay_datos = True
        
        # Calcular sumas
        sum_debe = sum(d.debe for d in cuenta.detalles)
        sum_haber = sum(d.haber for d in cuenta.detalles)
        
        # Calcular saldos
        sal_deudor = 0.0
        sal_acreedor = 0.0
        
        if sum_debe > sum_haber:
            sal_deudor = sum_debe - sum_haber
        elif sum_haber > sum_debe:
            sal_acreedor = sum_haber - sum_debe
        
        # Acumular totales generales
        total_sum_debe += sum_debe
        total_sum_haber += sum_haber
        total_sal_deudor += sal_deudor
        total_sal_acreedor += sal_acreedor
        
        # Agregar fila
        data.append([
            cuenta.codigo,
            Paragraph(cuenta.nombre, styles['Normal']),
            f"{sum_debe:,.2f}",
            f"{sum_haber:,.2f}",
            f"{sal_deudor:,.2f}",
            f"{sal_acreedor:,.2f}"
        ])
    
    # 5. Fila de Totales Finales
    data.append([
        "TOTALES", "",
        f"{total_sum_debe:,.2f}",
        f"{total_sum_haber:,.2f}",
        f"{total_sal_deudor:,.2f}",
        f"{total_sal_acreedor:,.2f}"
    ])
    
    if not hay_datos:
        print("No hay datos para generar el balance.")
        return False
    
    # 6. Estilos
    t = Table(data, colWidths=[50, 140, 65, 65, 65, 65])
    estilo = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),  # Números a la derecha
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        # Negrita en encabezados
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        # Fila de totales resaltada
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, -1), (-1, -1), 8),
    ])
    t.setStyle(estilo)
    elements.append(t)
    
    # 7. Mensaje de validación en el PDF
    cuadra_sumas = round(total_sum_debe, 2) == round(total_sum_haber, 2)
    cuadra_saldos = round(total_sal_deudor, 2) == round(total_sal_acreedor, 2)
    
    elements.append(Spacer(1, 20))
    
    if cuadra_sumas and cuadra_saldos:
        msg = "✓ VALIDACIÓN: EL BALANCE CUADRA CORRECTAMENTE."
        color_msg = colors.green
    else:
        msg = "✗ ALERTA: EL BALANCE ESTÁ DESCUADRADO. REVISAR ASIENTOS."
        color_msg = colors.red
    
    p_valid = Paragraph(
        f"{msg}",
        style=ParagraphStyle('Valid', parent=styles['Normal'], textColor=color_msg)
    )
    elements.append(p_valid)
    
    try:
        doc.build(elements)
        print(f"✅ Balance de Comprobación generado: {nombre_archivo}")
        return True
    except Exception as e:
        print(f"❌ Error PDF Balance: {e}")
        return False
