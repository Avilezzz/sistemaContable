"""
Generador de Estados Financieros (Estado de Resultados y Balance General).
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from .utilidades import obtener_saldo_cuenta, obtener_cuentas_con_saldo_detallado
from src.modelos.entidades import Asiento
from src.servicios.empresa import obtener_empresa
from src.reportes.encabezado import crear_encabezado_empresa


def generar_estado_resultados(db: Session, nombre_archivo="estado_resultados.pdf"):
    """
    Estado de Resultados SIMPLE - CORREGIDO
    """
    empresa = obtener_empresa(db)
    asientos = db.query(Asiento).order_by(Asiento.fecha).all()
    fecha_inicio = asientos[0].fecha if asientos else None
    fecha_fin = asientos[-1].fecha if asientos else None
    
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Encabezado
    if empresa:
        elements.extend(crear_encabezado_empresa(
            empresa, "ESTADO DE RESULTADOS", fecha_inicio, fecha_fin
        ))
    else:
        elements.append(Paragraph("ESTADO DE RESULTADOS", styles['Title']))
    
    elements.append(Spacer(1, 12))
    
    # Obtener datos
    lista_ingresos, total_ingresos = obtener_cuentas_con_saldo_detallado(db, "4", styles)
    lista_costos, total_costos = obtener_cuentas_con_saldo_detallado(db, "6", styles)
    lista_gastos, total_gastos = obtener_cuentas_con_saldo_detallado(db, "5", styles)
    
    # Cálculos
    utilidad_bruta = total_ingresos - total_costos
    utilidad_neta = utilidad_bruta - total_gastos
    
    # Tabla simple
    data = [
        ["CONCEPTO", "VALOR"]
    ]
    
    # === INGRESOS ===
    data.append(["INGRESOS OPERACIONALES", ""])
    for item in lista_ingresos:
        # item[1] es un Paragraph, lo usamos directamente
        data.append([item[1], item[2]])
    data.append(["", f"{total_ingresos:,.2f}"])
    data.append(["", ""])
    
    # === COSTOS ===
    data.append(["(-) COSTO DE VENTAS", ""])
    if lista_costos:
        for item in lista_costos:
            data.append([item[1], item[2]])
    data.append(["", f"{total_costos:,.2f}"])
    data.append(["", ""])
    
    # === UTILIDAD BRUTA ===
    data.append(["UTILIDAD BRUTA", f"{utilidad_bruta:,.2f}"])
    data.append(["", ""])
    
    # === GASTOS ===
    data.append(["(-) GASTOS OPERACIONALES", ""])
    for item in lista_gastos:
        data.append([item[1], item[2]])
    data.append(["", f"{total_gastos:,.2f}"])
    data.append(["", ""])
    
    # === UTILIDAD NETA ===
    data.append(["UTILIDAD NETA", f"{utilidad_neta:,.2f}"])
    
    # Crear tabla
    t = Table(data, colWidths=[320, 100])
    
    # Estilos SIMPLES
    t.setStyle(TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        
        # Alineación de valores
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        
        # Bordes
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Negrita para UTILIDAD NETA
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 10),
        ('LINEABOVE', (0, -1), (-1, -1), 2, colors.black),
    ]))
    
    elements.append(t)
    
    try:
        doc.build(elements)
        print(f"✅ Reporte generado: ${utilidad_neta:,.2f}")
        return utilidad_neta
    except Exception as e:
        print(f"❌ Error: {e}")
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
    empresa = obtener_empresa(db)
    asientos = db.query(Asiento).order_by(Asiento.fecha).all()
    fecha_corte = asientos[-1].fecha if asientos else None

    doc = SimpleDocTemplate(nombre_archivo, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    
    if empresa:
        # Se muestra la fecha de corte final
        elements.extend(crear_encabezado_empresa(empresa, "BALANCE GENERAL", fecha_corte))
    else:
        elements.append(Paragraph("BALANCE GENERAL", styles['Title']))
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
