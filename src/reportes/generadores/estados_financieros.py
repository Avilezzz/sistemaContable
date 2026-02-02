"""
Generador de Estados Financieros (Estado de Resultados y Balance General).
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from .utilidades import obtener_saldo_cuenta, obtener_cuentas_con_saldo_detallado


def generar_estado_resultados(db: Session, nombre_archivo="estado_resultados.pdf"):
    """
    Genera el Estado de Resultados (Pérdidas y Ganancias).
    Retorna la UTILIDAD DEL EJERCICIO (float) para usarla en el Balance General.
    
    CORRECCIONES:
    1. Los ingresos (clase 4) son ACREEDORES - su saldo se calcula como HABER - DEBE
    2. Los gastos (clase 5) y costos (clase 6) son DEUDORES - su saldo se calcula como DEBE - HABER
    3. Utilidad = Ingresos - (Gastos + Costos)
    """
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    elements.append(Paragraph("ESTADO DE RESULTADOS INTEGRAL", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # 1. INGRESOS (Clase 4 - ACREEDORA)
    total_ingresos = obtener_saldo_cuenta(db, "4")
    
    # 2. COSTOS DE VENTAS (Clase 6 - DEUDORA)
    total_costos = obtener_saldo_cuenta(db, "6")
    
    # 3. UTILIDAD BRUTA
    utilidad_bruta = total_ingresos - total_costos
    
    # 4. GASTOS OPERACIONALES (Clase 5 - DEUDORA)
    total_gastos = obtener_saldo_cuenta(db, "5")
    
    # 5. UTILIDAD NETA DEL EJERCICIO
    utilidad_ejercicio = utilidad_bruta - total_gastos
    
    # Estructura visual mejorada
    data = [
        ["CONCEPTO", "PARCIAL", "TOTAL"],
        ["", "", ""],
        ["INGRESOS OPERACIONALES", "", f"{total_ingresos:,.2f}"],
        ["(-) COSTO DE VENTAS", f"{total_costos:,.2f}", ""],
        ["", "", ""],
        ["UTILIDAD BRUTA EN VENTAS", "", f"{utilidad_bruta:,.2f}"],
        ["", "", ""],
        ["(-) GASTOS OPERACIONALES", "", ""],
        ["   Gastos Administrativos y de Ventas", f"{total_gastos:,.2f}", ""],
        ["", "", ""],
        ["UTILIDAD OPERACIONAL", "", f"{(utilidad_bruta - total_gastos):,.2f}"],
        ["", "", ""],
        ["UTILIDAD NETA DEL EJERCICIO", "", f"{utilidad_ejercicio:,.2f}"]
    ]
    
    t = Table(data, colWidths=[280, 80, 80])
    
    # Color para utilidad/pérdida
    color_resultado = colors.green if utilidad_ejercicio >= 0 else colors.red
    
    t.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        # Resaltar ingresos totales
        ('BACKGROUND', (0, 2), (-1, 2), colors.lightblue),
        ('FONTNAME', (0, 2), (-1, 2), 'Helvetica-Bold'),
        # Resaltar utilidad bruta
        ('BACKGROUND', (0, 5), (-1, 5), colors.lightyellow),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        # Resaltar utilidad operacional
        ('BACKGROUND', (0, 10), (-1, 10), colors.lightyellow),
        ('FONTNAME', (0, 10), (-1, 10), 'Helvetica-Bold'),
        # Resaltar Resultado Final
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), color_resultado),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
    ]))
    
    elements.append(t)
    
    # Agregar nota explicativa
    elements.append(Spacer(1, 20))
    nota_style = ParagraphStyle('Nota', parent=styles['Normal'], fontSize=8, textColor=colors.grey)
    nota = Paragraph(
        f"Nota: Los saldos se calculan respetando la naturaleza de cada cuenta. "
        f"Ingresos (Acreedores) = Haber - Debe. Gastos y Costos (Deudores) = Debe - Haber.",
        nota_style
    )
    elements.append(nota)
    
    try:
        doc.build(elements)
        print(f"✅ Estado de Resultados generado. Utilidad: ${utilidad_ejercicio:,.2f}")
        return utilidad_ejercicio  # RETORNAMOS EL VALOR PARA EL BALANCE
    except Exception as e:
        print(f"❌ Error PDF Estado Resultados: {e}")
        return 0.0


def generar_balance_general(db: Session, utilidad_ejercicio: float, nombre_archivo="balance_general.pdf"):
    """
    Genera el Balance General (Estado de Situación Financiera).
    
    CORRECCIONES:
    1. Respeta la naturaleza de las cuentas al calcular saldos
    2. Mejora la presentación con subtotales
    3. Incluye validación de la ecuación contable
    4. Formato más profesional y legible
    """
    # Usamos landscape (horizontal) para que quepan bien las dos columnas
    doc = SimpleDocTemplate(nombre_archivo, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("ESTADO DE SITUACIÓN FINANCIERA (BALANCE GENERAL)", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # --- OBTENER DATOS ---
    # ACTIVOS (Clase 1 - DEUDORA)
    lista_activos, total_activo = obtener_cuentas_con_saldo_detallado(db, "1", styles)
    
    # PASIVOS (Clase 2 - ACREEDORA)
    lista_pasivos, total_pasivo = obtener_cuentas_con_saldo_detallado(db, "2", styles)
    
    # PATRIMONIO (Clase 3 - ACREEDORA)
    lista_patrimonio_base, total_patrimonio_base = obtener_cuentas_con_saldo_detallado(db, "3", styles)
    
    # PATRIMONIO TOTAL = Patrimonio Base + Utilidad del Ejercicio
    total_patrimonio_final = total_patrimonio_base + utilidad_ejercicio
    
    # --- CONSTRUCCIÓN DEL LADO IZQUIERDO (ACTIVOS) ---
    izquierda = [
        ["", Paragraph("ACTIVOS", styles['Heading3']), ""]
    ] + lista_activos + [
        ["", "", ""],
        ["", Paragraph("TOTAL ACTIVOS", styles['Heading3']), f"{total_activo:,.2f}"]
    ]
    
    # --- CONSTRUCCIÓN DEL LADO DERECHO (PASIVOS + PATRIMONIO) ---
    derecha = [
        ["", Paragraph("PASIVOS", styles['Heading3']), ""]
    ] + lista_pasivos + [
        ["", "", ""],
        ["", Paragraph("TOTAL PASIVOS", styles['Normal']), f"{total_pasivo:,.2f}"],
        ["", "", ""],
        ["", Paragraph("PATRIMONIO", styles['Heading3']), ""]
    ] + lista_patrimonio_base + [
        ["", Paragraph("Resultado del Ejercicio", styles['Normal']), f"{utilidad_ejercicio:,.2f}"],
        ["", "", ""],
        ["", Paragraph("TOTAL PATRIMONIO", styles['Normal']), f"{total_patrimonio_final:,.2f}"],
        ["", "", ""],
        ["", Paragraph("TOTAL PASIVO + PATRIMONIO", styles['Heading3']), f"{(total_pasivo + total_patrimonio_final):,.2f}"]
    ]
    
    # --- EMPAREJAR LAS LISTAS ---
    data = [[
        "CÓD", "ACTIVOS", "VALOR",
        "CÓD", "PASIVOS Y PATRIMONIO", "VALOR"
    ]]
    
    max_rows = max(len(izquierda), len(derecha))
    
    for i in range(max_rows):
        fila = []
        
        # Lado izquierdo
        if i < len(izquierda):
            fila.extend(izquierda[i])
        else:
            fila.extend(["", "", ""])
        
        # Lado derecho
        if i < len(derecha):
            fila.extend(derecha[i])
        else:
            fila.extend(["", "", ""])
        
        data.append(fila)
    
    # --- CREAR Y ESTILIZAR TABLA ---
    t = Table(data, colWidths=[45, 200, 75, 45, 200, 75])
    estilo = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        # Alineación general
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),  # Valores activos
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'),  # Valores pasivo+patrimonio
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        # Línea vertical separadora
        ('LINEAFTER', (2, 0), (2, -1), 2, colors.darkblue),
    ])
    t.setStyle(estilo)
    elements.append(t)
    
    # --- VALIDACIÓN DE ECUACIÓN CONTABLE ---
    total_derecho = total_pasivo + total_patrimonio_final
    diferencia = round(total_activo - total_derecho, 2)
    
    elements.append(Spacer(1, 15))
    
    if abs(diferencia) < 0.01:  # Considera descuadres menores a 1 centavo como OK
        msg = "✓ ECUACIÓN CONTABLE VERIFICADA: ACTIVO = PASIVO + PATRIMONIO"
        color_msg = colors.green
    else:
        msg = f"✗ ALERTA: DESCUADRE DE ${abs(diferencia):,.2f} - REVISAR ASIENTOS"
        color_msg = colors.red
    
    validacion_style = ParagraphStyle(
        'Validacion',
        parent=styles['Normal'],
        textColor=color_msg,
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=1  # Centrado
    )
    elements.append(Paragraph(msg, validacion_style))
    
    # Detalle de la ecuación
    elements.append(Spacer(1, 10))
    detalle_ec = f"Activos: ${total_activo:,.2f} | Pasivos: ${total_pasivo:,.2f} | Patrimonio: ${total_patrimonio_final:,.2f}"
    elements.append(Paragraph(detalle_ec, styles['Normal']))
    
    try:
        doc.build(elements)
        print(f"✅ Balance General generado exitosamente: {nombre_archivo}")
        return True
    except Exception as e:
        print(f"❌ Error al generar PDF Balance General: {e}")
        return False
