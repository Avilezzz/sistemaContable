"""
Generador de Libro Mayor en formato de Cuentas T.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from src.modelos.entidades import Cuenta, Asiento
from src.servicios.empresa import obtener_empresa
from src.reportes.encabezado import crear_encabezado_empresa


def generar_pdf_libro_mayor(db: Session, nombre_archivo="libro_mayor.pdf"):
    """
    Genera un reporte visual en forma de "CUENTAS T".
    """
    empresa = obtener_empresa(db)
    asientos = db.query(Asiento).order_by(Asiento.fecha).all()
    fecha_inicio = asientos[0].fecha if asientos else None
    fecha_fin = asientos[-1].fecha if asientos else None

    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados para la T
    estilo_centro = ParagraphStyle('Centro', parent=styles['Normal'], alignment=1)  # 1 = Center
    estilo_derecha = ParagraphStyle('Derecha', parent=styles['Normal'], alignment=2)  # 2 = Right
    estilo_negrita = ParagraphStyle('Negrita', parent=styles['Normal'], fontName='Helvetica-Bold')
    
    if empresa:
        elements.extend(crear_encabezado_empresa(empresa, "LIBRO MAYOR (FORMATO T)", fecha_inicio, fecha_fin))
    else:
        elements.append(Paragraph("LIBRO MAYOR (FORMATO T)", styles['Title']))
        elements.append(Spacer(1, 15))
    
    # Consultar cuentas
    cuentas = db.query(Cuenta).order_by(Cuenta.codigo).all()
    hay_datos = False
    
    for cuenta in cuentas:
        if not cuenta.detalles:
            continue
        
        hay_datos = True
        
        # --- PREPARACIÓN DE DATOS TIPO T ---
        # 1. Separar movimientos en Debe y Haber
        movs_debe = []
        movs_haber = []
        sum_debe = 0.0
        sum_haber = 0.0
        
        for d in cuenta.detalles:
            txt_detalle = f"{d.asiento.fecha} (As. {d.asiento_id})\n"
            
            if d.debe > 0:
                movs_debe.append((txt_detalle, d.debe))
                sum_debe += d.debe
            
            if d.haber > 0:
                movs_haber.append((txt_detalle, d.haber))
                sum_haber += d.haber
        
        # 2. Determinar cuántas filas necesitamos
        max_filas = max(len(movs_debe), len(movs_haber))
        
        # 3. Construir la Matriz de la Tabla
        data = [[f"{cuenta.codigo} - {cuenta.nombre}", ""]]
        data.append(["DEBE", "HABER"])
        
        # Llenar filas emparejando izquierda y derecha
        for i in range(max_filas):
            # Lado Izquierdo (Debe)
            if i < len(movs_debe):
                txt, val = movs_debe[i]
                celda_izq = Paragraph(f"{txt}$ {val:,.2f}", styles['Normal'])
            else:
                celda_izq = ""
            
            # Lado Derecho (Haber)
            if i < len(movs_haber):
                txt, val = movs_haber[i]
                celda_der = Paragraph(f"{txt}$ {val:,.2f}", styles['Normal'])
            else:
                celda_der = ""
            
            data.append([celda_izq, celda_der])
        
        # 4. Filas de Sumas y Saldos
        data.append([
            Paragraph(f"SUMA: $ {sum_debe:,.2f}", estilo_derecha),
            Paragraph(f"SUMA: $ {sum_haber:,.2f}", estilo_derecha)
        ])
        
        # Cálculo del Saldo Final
        saldo = sum_debe - sum_haber
        txt_saldo = f"SALDO: $ {abs(saldo):,.2f}"
        
        # Ubicar el saldo visualmente
        if saldo > 0:  # Saldo Deudor
            data.append([Paragraph(f"{txt_saldo} (D)", estilo_centro), ""])
        elif saldo < 0:  # Saldo Acreedor
            data.append(["", Paragraph(f"{txt_saldo} (A)", estilo_centro)])
        else:
            data.append([Paragraph("SALDO NULO", estilo_centro), ""])
        
        # --- ESTILOS VISUALES (LA "T") ---
        t = Table(data, colWidths=[200, 200])
        estilo_t = TableStyle([
            # 1. Título de la cuenta (Fila 0)
            ('SPAN', (0, 0), (1, 0)),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('BACKGROUND', (0, 0), (1, 0), colors.navy),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            # 2. Subtítulos DEBE/HABER (Fila 1)
            ('ALIGN', (0, 1), (1, 1), 'CENTER'),
            ('FONTNAME', (0, 1), (1, 1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (1, 1), colors.lightgrey),
            ('LINEBELOW', (0, 1), (1, 1), 1.5, colors.black),
            # 3. Línea Vertical Central (La pata de la T)
            ('LINEAFTER', (0, 1), (0, -2), 1.5, colors.black),
            # 4. Línea de Sumas
            ('LINEABOVE', (0, -2), (1, -2), 1, colors.black),
            ('FONTSIZE', (0, -2), (1, -1), 9),
            # 5. Borde Exterior
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ])
        t.setStyle(estilo_t)
        elements.append(t)
        elements.append(Spacer(1, 25))
    
    if not hay_datos:
        print("No hay movimientos.")
        return False
    
    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"Error PDF Mayor T: {e}")
        return False
