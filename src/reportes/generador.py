from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from src.modelos.entidades import Asiento
from src.modelos.entidades import Cuenta
from reportlab.lib.pagesizes import landscape, A4
from datetime import datetime

def generar_pdf_libro_diario(db: Session, nombre_archivo="libro_diario.pdf"):
    """
    Genera un PDF con todos los asientos contables ordenados por fecha.
    """
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # 1. Título del Reporte
    titulo = Paragraph("<b>LIBRO DIARIO</b>", styles['Title'])
    elements.append(titulo)
    elements.append(Spacer(1, 12))

    # 2. Consultar datos
    asientos = db.query(Asiento).order_by(Asiento.fecha).all()

    if not asientos:
        print("No hay datos para generar el reporte.")
        return False

    # 3. Preparar datos para la Tabla
    # Encabezados
    data = [['FECHA', 'CÓDIGO', 'CUENTA / DETALLE', 'DEBE', 'HABER']]
    
    total_debe_general = 0
    total_haber_general = 0

    for asiento in asientos:
        # Fila de Cabecera del Asiento (Fecha y Descripción)
        # Usamos Paragraph para que el texto largo haga salto de línea automático
        desc_asiento = Paragraph(f"<b>Asiento #{asiento.id}:</b> {asiento.descripcion}", styles['Normal'])
        data.append([str(asiento.fecha), "", desc_asiento, "", ""])
        
        # Filas de Detalles (Cuentas)
        for detalle in asiento.detalles:
            nombre_cuenta = Paragraph(detalle.cuenta.nombre, styles['Normal'])
            data.append([
                "", # Fecha vacía
                detalle.cuenta.codigo,
                nombre_cuenta,
                f"{detalle.debe:,.2f}",
                f"{detalle.haber:,.2f}"
            ])
            
            total_debe_general += detalle.debe
            total_haber_general += detalle.haber
        
        # Fila vacía para separar asientos visualmente
        data.append(["", "", "", "", ""])

    # Fila de Totales Generales
    data.append([
        "TOTALES", "", "", 
        f"{total_debe_general:,.2f}", 
        f"{total_haber_general:,.2f}"
    ])

    # 4. Configurar Estilo de la Tabla
    # Table(data, colWidths=[ancho_columna1, ...])
    t = Table(data, colWidths=[70, 60, 250, 60, 60])
    
    estilo_tabla = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'), # Alinear números a la derecha
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        # Resaltar fila de totales (última fila)
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ])
    
    t.setStyle(estilo_tabla)
    elements.append(t)

    # 5. Construir PDF
    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"Error PDF: {e}")
        return False

def generar_pdf_libro_mayor(db: Session, nombre_archivo="libro_mayor.pdf"):
    """
    Genera un reporte visual en forma de "CUENTAS T".
    """
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Estilos personalizados para la T
    estilo_centro = ParagraphStyle('Centro', parent=styles['Normal'], alignment=1) # 1 = Center
    estilo_derecha = ParagraphStyle('Derecha', parent=styles['Normal'], alignment=2) # 2 = Right
    estilo_negrita = ParagraphStyle('Negrita', parent=styles['Normal'], fontName='Helvetica-Bold')

    # Título Principal
    elements.append(Paragraph("<b>LIBRO MAYOR (FORMATO T)</b>", styles['Title']))
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
            # Formato de texto para cada movimiento: "Fecha (Asiento) \n Valor"
            txt_detalle = f"{d.asiento.fecha} (As. {d.asiento_id})\n"
            
            if d.debe > 0:
                movs_debe.append((txt_detalle, d.debe))
                sum_debe += d.debe
            if d.haber > 0:
                movs_haber.append((txt_detalle, d.haber))
                sum_haber += d.haber

        # 2. Determinar cuántas filas necesitamos (el lado más largo manda)
        max_filas = max(len(movs_debe), len(movs_haber))

        # 3. Construir la Matriz de la Tabla
        # Encabezado de la T (Nombre de Cuenta)
        data = [[f"{cuenta.codigo} - {cuenta.nombre}", ""]]
        # Sub-encabezados
        data.append(["DEBE", "HABER"])

        # Llenar filas emparejando izquierda y derecha
        for i in range(max_filas):
            # Lado Izquierdo (Debe)
            if i < len(movs_debe):
                txt, val = movs_debe[i]
                celda_izq = Paragraph(f"{txt}<b>$ {val:,.2f}</b>", styles['Normal'])
            else:
                celda_izq = ""

            # Lado Derecho (Haber)
            if i < len(movs_haber):
                txt, val = movs_haber[i]
                celda_der = Paragraph(f"{txt}<b>$ {val:,.2f}</b>", styles['Normal'])
            else:
                celda_der = ""

            data.append([celda_izq, celda_der])

        # 4. Filas de Sumas y Saldos
        data.append([
            Paragraph(f"<b>SUMA: $ {sum_debe:,.2f}</b>", estilo_derecha),
            Paragraph(f"<b>SUMA: $ {sum_haber:,.2f}</b>", estilo_derecha)
        ])

        # Cálculo del Saldo Final
        saldo = sum_debe - sum_haber
        txt_saldo = f"SALDO: $ {abs(saldo):,.2f}"
        
        # Ubicar el saldo visualmente
        if saldo > 0: # Saldo Deudor (Va a la izquierda o abajo izquierda)
            data.append([Paragraph(f"<b>{txt_saldo} (D)</b>", estilo_centro), ""])
        elif saldo < 0: # Saldo Acreedor (Va a la derecha)
            data.append(["", Paragraph(f"<b>{txt_saldo} (A)</b>", estilo_centro)])
        else:
            data.append([Paragraph("<b>SALDO NULO</b>", estilo_centro), ""])

        # --- ESTILOS VISUALES (LA "T") ---
        # Ancho: Mitad de página para cada lado
        t = Table(data, colWidths=[200, 200])
        
        estilo_t = TableStyle([
            # 1. Título de la cuenta (Fila 0)
            ('SPAN', (0, 0), (1, 0)),                       # Unir columnas
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('BACKGROUND', (0, 0), (1, 0), colors.navy),    # Fondo Azul
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            
            # 2. Subtítulos DEBE/HABER (Fila 1)
            ('ALIGN', (0, 1), (1, 1), 'CENTER'),
            ('FONTNAME', (0, 1), (1, 1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (1, 1), colors.lightgrey),
            ('LINEBELOW', (0, 1), (1, 1), 1.5, colors.black), # Línea horizontal fuerte de la T

            # 3. Línea Vertical Central (La pata de la T)
            ('LINEAFTER', (0, 1), (0, -2), 1.5, colors.black), # Línea vertical en col 0 hasta las sumas

            # 4. Línea de Sumas (Antepenúltima fila)
            ('LINEABOVE', (0, -2), (1, -2), 1, colors.black), # Línea antes de las sumas
            ('FONTSIZE', (0, -2), (1, -1), 9),
            
            # 5. Borde Exterior (Opcional, para encerrar la cuenta)
            ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ])
        
        t.setStyle(estilo_t)
        elements.append(t)
        elements.append(Spacer(1, 25)) # Espacio entre T y T

    if not hay_datos:
        print("No hay movimientos.")
        return False

    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"Error PDF Mayor T: {e}")
        return False

# --- Agregar al final de src/reportes/generador.py ---

def generar_balance_comprobacion(db: Session, nombre_archivo="balance_comprobacion.pdf"):
    """
    Genera el Balance de Comprobación de Sumas y Saldos.
    Verifica que (Sumas Debe == Sumas Haber) y (Saldo Deudor == Saldo Acreedor).
    """
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # 1. Título
    elements.append(Paragraph("<b>BALANCE DE COMPROBACIÓN DE SUMAS Y SALDOS</b>", styles['Title']))
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
            Paragraph(cuenta.nombre, styles['Normal']), # Paragraph para texto largo
            f"{sum_debe:,.2f}",
            f"{sum_haber:,.2f}",
            f"{sal_deudor:,.2f}",
            f"{sal_acreedor:,.2f}"
        ])

    # 5. Fila de Totales Finales (La prueba de fuego)
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
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'), # Números a la derecha
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
        msg = "VALIDACIÓN: EL BALANCE CUADRA CORRECTAMENTE."
        color_msg = colors.green
    else:
        msg = "ALERTA: EL BALANCE ESTÁ DESCUADRADO. REVISAR ASIENTOS."
        color_msg = colors.red
        
    p_valid = Paragraph(f"<b>{msg}</b>", 
                        style=ParagraphStyle('Valid', parent=styles['Normal'], textColor=color_msg))
    elements.append(p_valid)

    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"Error PDF Balance: {e}")
        return False

# --- Agregar al final de src/reportes/generador.py ---

def obtener_saldo_cuenta(db: Session, codigo_cuenta: str):
    """Auxiliar: Calcula el saldo final de una cuenta o grupo de cuentas"""
    # Buscamos todas las cuentas que empiecen con ese código (ej: "1" trae todo activo)
    cuentas = db.query(Cuenta).filter(Cuenta.codigo.like(f"{codigo_cuenta}%")).all()
    
    saldo_total = 0.0
    
    for cuenta in cuentas:
        if not cuenta.detalles: continue
        
        debe = sum(d.debe for d in cuenta.detalles)
        haber = sum(d.haber for d in cuenta.detalles)
        
        if cuenta.naturaleza == 'DEUDORA':
            saldo_total += (debe - haber)
        else:
            saldo_total += (haber - debe)
            
    return saldo_total



def generar_estado_resultados(db: Session, nombre_archivo="estado_resultados.pdf"):
    """
    Genera el Estado de Resultados (Pérdidas y Ganancias) según estructura contable profesional.
    Retorna la UTILIDAD DEL EJERCICIO (float) para usarla en el Balance General.
    
    Estructura:
    - Ingresos Operacionales (Ventas)
    - (-) Costo de Ventas
    = UTILIDAD BRUTA
    - (-) Gastos Operacionales
    = UTILIDAD OPERACIONAL
    + Otros Ingresos
    - Otros Gastos
    = UTILIDAD ANTES DE IMPUESTOS
    - Impuestos
    = UTILIDAD NETA DEL EJERCICIO
    """
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4, 
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    styles = getSampleStyleSheet()
    
    # --- ESTILOS MEJORADOS ---
    estilo_titulo = ParagraphStyle(
        'TituloER', 
        parent=styles['Title'], 
        fontSize=18, 
        spaceAfter=8,
        textColor=colors.HexColor('#1a1a2e'),
        fontName='Helvetica-Bold',
        alignment=1  # Centrado
    )
    
    estilo_subtitulo = ParagraphStyle(
        'SubtituloER',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=1
    )
    
    estilo_concepto = ParagraphStyle(
        'ConceptoER',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=15
    )
    
    estilo_concepto_bold = ParagraphStyle(
        'ConceptoBoldER',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        leftIndent=10
    )
    
    estilo_subtotal = ParagraphStyle(
        'SubtotalER',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#2c5f7d')
    )
    
    estilo_total_final = ParagraphStyle(
        'TotalFinalER',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1a1a2e')
    )
    
    estilo_monto = ParagraphStyle(
        'MontoER',
        parent=styles['Normal'],
        fontSize=10,
        alignment=2  # Derecha
    )
    
    estilo_monto_bold = ParagraphStyle(
        'MontoBoldER',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=2
    )
    
    # 1. Encabezado del Reporte
    elements.append(Paragraph("<b>ESTADO DE RESULTADOS INTEGRAL</b>", estilo_titulo))
    fecha_reporte = datetime.now().strftime("%d de %B de %Y")
    elements.append(Paragraph(f"Período: Del 01 de Enero al 31 de Diciembre - Generado: {fecha_reporte}", estilo_subtitulo))
    
    # 2. CÁLCULOS SEGÚN ESTRUCTURA CONTABLE PROFESIONAL
    
    # INGRESOS OPERACIONALES (Clase 4 - Ventas)
    total_ingresos = obtener_saldo_cuenta(db, "4")
    
    # COSTO DE VENTAS (Clase 6)
    total_costos = obtener_saldo_cuenta(db, "6")
    
    # UTILIDAD BRUTA = Ingresos - Costo de Ventas
    utilidad_bruta = total_ingresos - total_costos
    
    # GASTOS OPERACIONALES (Clase 5)
    total_gastos = obtener_saldo_cuenta(db, "5")
    
    # UTILIDAD OPERACIONAL = Utilidad Bruta - Gastos Operacionales
    utilidad_operacional = utilidad_bruta - total_gastos
    
    # OTROS INGRESOS Y GASTOS (puedes ajustar según tu plan de cuentas)
    # Ejemplo: Clase 4 podría tener subcategorías
    otros_ingresos = 0.0  # Ajustar si tienes cuenta específica (ej: 42xx)
    otros_gastos = 0.0     # Ajustar si tienes cuenta específica (ej: 52xx)
    
    # UTILIDAD ANTES DE IMPUESTOS
    utilidad_antes_impuestos = utilidad_operacional + otros_ingresos - otros_gastos
    
    # IMPUESTOS (puedes calcularlo como % o tener cuenta específica)
    # Ejemplo: 25% de impuesto sobre la renta
    tasa_impuesto = 0.0  # Ajustar según legislación local (ej: 0.25 para 25%)
    impuestos = utilidad_antes_impuestos * tasa_impuesto if utilidad_antes_impuestos > 0 else 0.0
    
    # UTILIDAD NETA DEL EJERCICIO (Resultado Final)
    utilidad_neta = utilidad_antes_impuestos - impuestos
    
    # 3. CONSTRUCCIÓN DE LA TABLA CON ESTRUCTURA PROFESIONAL
    
    # Colores
    color_header = colors.HexColor('#2c5f7d')
    color_subtotal = colors.HexColor('#e8f4f8')
    color_total = colors.HexColor('#d4e6f1')
    color_positivo = colors.HexColor('#27ae60')
    color_negativo = colors.HexColor('#c0392b')
    
    data = [
        # Encabezado
        [Paragraph("<b>CONCEPTO</b>", estilo_concepto_bold), Paragraph("<b>VALOR ($)</b>", estilo_monto_bold)],
        
        # SECCIÓN 1: INGRESOS OPERACIONALES
        [Paragraph("<b>INGRESOS OPERACIONALES</b>", estilo_concepto_bold), ""],
        [Paragraph("Ventas / Ingresos por Servicios", estilo_concepto), Paragraph(f"{total_ingresos:,.2f}", estilo_monto)],
        ["", ""],  # Espacio
        
        # SECCIÓN 2: COSTO DE VENTAS
        [Paragraph("<b>(-) COSTO DE VENTAS</b>", estilo_concepto_bold), ""],
        [Paragraph("Costos Directos de Producción/Servicios", estilo_concepto), Paragraph(f"({total_costos:,.2f})", estilo_monto)],
        ["", ""],
        
        # SUBTOTAL 1: UTILIDAD BRUTA
        [Paragraph("<b>= UTILIDAD BRUTA</b>", estilo_subtotal), Paragraph(f"<b>{utilidad_bruta:,.2f}</b>", estilo_monto_bold)],
        ["", ""],
        
        # SECCIÓN 3: GASTOS OPERACIONALES
        [Paragraph("<b>(-) GASTOS OPERACIONALES</b>", estilo_concepto_bold), ""],
        [Paragraph("Gastos de Administración y Ventas", estilo_concepto), Paragraph(f"({total_gastos:,.2f})", estilo_monto)],
        ["", ""],
        
        # SUBTOTAL 2: UTILIDAD OPERACIONAL
        [Paragraph("<b>= UTILIDAD OPERACIONAL</b>", estilo_subtotal), Paragraph(f"<b>{utilidad_operacional:,.2f}</b>", estilo_monto_bold)],
        ["", ""],
    ]
    
    # SECCIÓN 4: OTROS INGRESOS/GASTOS (solo si existen)
    if otros_ingresos > 0 or otros_gastos > 0:
        data.extend([
            [Paragraph("<b>(+) OTROS INGRESOS</b>", estilo_concepto_bold), Paragraph(f"{otros_ingresos:,.2f}", estilo_monto)],
            [Paragraph("<b>(-) OTROS GASTOS</b>", estilo_concepto_bold), Paragraph(f"({otros_gastos:,.2f})", estilo_monto)],
            ["", ""],
        ])
    
    # SUBTOTAL 3: UTILIDAD ANTES DE IMPUESTOS
    data.extend([
        [Paragraph("<b>= UTILIDAD ANTES DE IMPUESTOS</b>", estilo_subtotal), Paragraph(f"<b>{utilidad_antes_impuestos:,.2f}</b>", estilo_monto_bold)],
    ])
    
    # SECCIÓN 5: IMPUESTOS (solo si aplica)
    if tasa_impuesto > 0:
        data.extend([
            ["", ""],
            [Paragraph(f"(-) Impuesto sobre la Renta ({int(tasa_impuesto*100)}%)", estilo_concepto), Paragraph(f"({impuestos:,.2f})", estilo_monto)],
        ])
    
    # RESULTADO FINAL
    data.extend([
        ["", ""],
        [Paragraph("<b>= UTILIDAD / (PÉRDIDA) NETA DEL EJERCICIO</b>", estilo_total_final), 
         Paragraph(f"<b>{utilidad_neta:,.2f}</b>", estilo_monto_bold)],
    ])
    
    # 4. CREAR TABLA
    tabla = Table(data, colWidths=[350, 120])
    
    # Determinar color del resultado final
    color_resultado = color_positivo if utilidad_neta >= 0 else color_negativo
    
    estilo_tabla = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), color_header),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        
        # Alineación general
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        
        # Resaltar Utilidad Bruta (fila 7)
        ('BACKGROUND', (0, 7), (-1, 7), color_subtotal),
        ('LINEABOVE', (0, 7), (-1, 7), 1.5, colors.grey),
        ('LINEBELOW', (0, 7), (-1, 7), 1.5, colors.grey),
        
        # Resaltar Utilidad Operacional (fila 12)
        ('BACKGROUND', (0, 12), (-1, 12), color_subtotal),
        ('LINEABOVE', (0, 12), (-1, 12), 1.5, colors.grey),
        ('LINEBELOW', (0, 12), (-1, 12), 1.5, colors.grey),
    ])
    
    # Resaltar Utilidad Antes de Impuestos (varía según si hay otros ingresos/gastos)
    fila_antes_impuestos = 14 if otros_ingresos > 0 or otros_gastos > 0 else 14
    estilo_tabla.add('BACKGROUND', (0, fila_antes_impuestos), (-1, fila_antes_impuestos), color_subtotal)
    estilo_tabla.add('LINEABOVE', (0, fila_antes_impuestos), (-1, fila_antes_impuestos), 1.5, colors.grey)
    estilo_tabla.add('LINEBELOW', (0, fila_antes_impuestos), (-1, fila_antes_impuestos), 1.5, colors.grey)
    
    # Resaltar RESULTADO FINAL (última fila)
    estilo_tabla.add('BACKGROUND', (0, -1), (-1, -1), color_total)
    estilo_tabla.add('LINEABOVE', (0, -1), (-1, -1), 2, colors.black)
    estilo_tabla.add('FONTSIZE', (0, -1), (-1, -1), 12)
    estilo_tabla.add('TOPPADDING', (0, -1), (-1, -1), 10)
    estilo_tabla.add('BOTTOMPADDING', (0, -1), (-1, -1), 10)
    estilo_tabla.add('TEXTCOLOR', (1, -1), (1, -1), color_resultado)
    
    # Borde exterior
    estilo_tabla.add('BOX', (0, 0), (-1, -1), 1, colors.grey)
    
    tabla.setStyle(estilo_tabla)
    elements.append(tabla)
    
    # 5. INDICADORES DE RENTABILIDAD
    elements.append(Spacer(1, 25))
    
    # Calcular márgenes (solo si hay ingresos)
    if total_ingresos > 0:
        margen_bruto = (utilidad_bruta / total_ingresos) * 100
        margen_operacional = (utilidad_operacional / total_ingresos) * 100
        margen_neto = (utilidad_neta / total_ingresos) * 100
        
        indicadores_data = [
            [Paragraph("<b>INDICADORES DE RENTABILIDAD</b>", estilo_concepto_bold), ""],
            [Paragraph("Margen Bruto", estilo_concepto), Paragraph(f"{margen_bruto:.2f}%", estilo_monto)],
            [Paragraph("Margen Operacional", estilo_concepto), Paragraph(f"{margen_operacional:.2f}%", estilo_monto)],
            [Paragraph("Margen Neto", estilo_concepto), Paragraph(f"{margen_neto:.2f}%", estilo_monto)],
        ]
        
        tabla_indicadores = Table(indicadores_data, colWidths=[350, 120])
        tabla_indicadores.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        elements.append(tabla_indicadores)
    
    # 6. NOTA INTERPRETATIVA
    elements.append(Spacer(1, 20))
    
    if utilidad_neta >= 0:
        mensaje = f"✓ <b>Resultado Positivo:</b> La empresa generó una utilidad neta de <b>${utilidad_neta:,.2f}</b> en el período."
        color_nota = colors.green
    else:
        mensaje = f"⚠ <b>Resultado Negativo:</b> La empresa registró una pérdida neta de <b>${abs(utilidad_neta):,.2f}</b> en el período."
        color_nota = colors.red
    
    nota = Paragraph(
        mensaje,
        ParagraphStyle('Nota', parent=styles['Normal'], fontSize=9, textColor=color_nota)
    )
    elements.append(nota)
    
    # 7. Generación del archivo
    try:
        doc.build(elements)
        print(f"✓ Estado de Resultados generado exitosamente")
        print(f"  → Utilidad Bruta: ${utilidad_bruta:,.2f}")
        print(f"  → Utilidad Operacional: ${utilidad_operacional:,.2f}")
        print(f"  → Utilidad Neta: ${utilidad_neta:,.2f}")
        return utilidad_neta  # RETORNAMOS LA UTILIDAD NETA
    except Exception as e:
        print(f"❌ Error generando PDF Estado de Resultados: {e}")
        return 0.0


def generar_balance_general(db: Session, utilidad_ejercicio: float, nombre_archivo="balance_general.pdf"):
    """
    Genera un Balance General profesional en formato de cuenta:
    Activos (Izquierda) | Pasivo + Patrimonio (Derecha).
    ✨ Versión Mejorada - Sin columna de código
    """
    # Configuramos la página en horizontal (landscape) para que quepan las dos columnas
    doc = SimpleDocTemplate(nombre_archivo, pagesize=landscape(A4), 
                            rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    styles = getSampleStyleSheet()
    
    # --- ESTILOS MEJORADOS ---
    estilo_titulo = ParagraphStyle(
        'TituloMB', 
        parent=styles['Title'], 
        fontSize=18, 
        spaceAfter=8,
        textColor=colors.HexColor('#1a1a2e'),
        fontName='Helvetica-Bold'
    )
    
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=20,
        alignment=1  # Centrado
    )
    
    estilo_h = ParagraphStyle(
        'Header', 
        parent=styles['Normal'], 
        fontSize=10, 
        fontName='Helvetica-Bold', 
        textColor=colors.whitesmoke,
        alignment=1  # Centrado
    )
    
    estilo_txt = ParagraphStyle(
        'Texto', 
        parent=styles['Normal'], 
        fontSize=9,
        leftIndent=10
    )
    
    estilo_monto = ParagraphStyle(
        'Monto', 
        parent=styles['Normal'], 
        fontSize=9, 
        alignment=2  # Derecha
    )
    
    estilo_monto_bold = ParagraphStyle(
        'MontoB', 
        parent=styles['Normal'], 
        fontSize=10, 
        fontName='Helvetica-Bold', 
        alignment=2
    )
    
    # 1. Encabezado del Reporte
    elements.append(Paragraph("<b>ESTADO DE SITUACIÓN FINANCIERA</b>", estilo_titulo))
    fecha_reporte = datetime.now().strftime("%d de %B de %Y - %H:%M")
    elements.append(Paragraph(f"Generado el: {fecha_reporte}", estilo_subtitulo))

    # 2. Función auxiliar para obtener cuentas detalladas con saldo
    def obtener_datos_grupo(prefijo):
        cuentas = db.query(Cuenta).filter(Cuenta.codigo.like(f"{prefijo}%")).order_by(Cuenta.codigo).all()
        filas = []
        total = 0.0
        for c in cuentas:
            # Calculamos saldo según naturaleza
            d_sum = sum(d.debe for d in c.detalles)
            h_sum = sum(d.haber for d in c.detalles)
            saldo = (d_sum - h_sum) if c.naturaleza == 'DEUDORA' else (h_sum - d_sum)
            
            # Solo incluimos cuentas con saldo real (evitamos ceros)
            if abs(saldo) > 0.001:
                filas.append([
                    Paragraph(c.nombre, estilo_txt), 
                    Paragraph(f"$ {saldo:,.2f}", estilo_monto)
                ])
                total += saldo
        return filas, total

    # 3. Obtener Cuentas
    lista_activos, total_activo = obtener_datos_grupo("1")
    lista_pasivos, total_pasivo = obtener_datos_grupo("2")
    lista_patrimonio, total_patr_inicial = obtener_datos_grupo("3")
    
    total_patr_final = total_patr_inicial + utilidad_ejercicio
    total_pas_pat = total_pasivo + total_patr_final

    # 4. Construir Columnas Paralelas
    # LADO IZQUIERDO (ACTIVO)
    col_izq = [[Paragraph("<b>ACTIVO</b>", estilo_h), Paragraph("<b>VALOR</b>", estilo_h)]]
    col_izq += lista_activos
    
    # Línea subtotal
    col_izq.append([
        Paragraph("<b>TOTAL ACTIVOS</b>", estilo_txt), 
        Paragraph(f"<b>$ {total_activo:,.2f}</b>", estilo_monto_bold)
    ])

    # LADO DERECHO (PASIVO + PATRIMONIO)
    col_der = [[Paragraph("<b>PASIVO</b>", estilo_h), Paragraph("<b>VALOR</b>", estilo_h)]]
    col_der += lista_pasivos
    col_der.append([
        Paragraph("<b>TOTAL PASIVOS</b>", estilo_txt), 
        Paragraph(f"<b>$ {total_pasivo:,.2f}</b>", estilo_monto_bold)
    ])
    
    # Espacio separador visual
    col_der.append(["", ""])
    
    # Sección Patrimonio
    col_der.append([
        Paragraph("<b>PATRIMONIO</b>", estilo_h), 
        Paragraph("<b>VALOR</b>", estilo_h)
    ])
    col_der += lista_patrimonio
    col_der.append([
        Paragraph("Resultado del Ejercicio", estilo_txt), 
        Paragraph(f"$ {utilidad_ejercicio:,.2f}", estilo_monto)
    ])
    col_der.append([
        Paragraph("<b>TOTAL PATRIMONIO</b>", estilo_txt), 
        Paragraph(f"<b>$ {total_patr_final:,.2f}</b>", estilo_monto_bold)
    ])

    # 5. Unificar en una sola tabla de 5 columnas (2 Izq + 1 Separador + 2 Der)
    data_final = []
    num_filas = max(len(col_izq), len(col_der))
    
    for i in range(num_filas):
        fila = []
        # Activos
        fila += col_izq[i] if i < len(col_izq) else ["", ""]
        # Columna de espacio central
        fila += [""]
        # Pasivo + Patrimonio
        fila += col_der[i] if i < len(col_der) else ["", ""]
        data_final.append(fila)

    # Fila final de validación (Ecuación Contable)
    data_final.append([
        Paragraph("<b>TOTAL ACTIVO</b>", estilo_h), 
        Paragraph(f"<b>$ {total_activo:,.2f}</b>", estilo_monto_bold),
        "",  # Espacio
        Paragraph("<b>TOTAL PASIVO + PATRIMONIO</b>", estilo_h), 
        Paragraph(f"<b>$ {total_pas_pat:,.2f}</b>", estilo_monto_bold)
    ])

    # 6. Estilo de la Tabla con colores modernos
    # Anchos: [Nombre, Valor, Espacio, Nombre, Valor]
    tabla = Table(data_final, colWidths=[230, 90, 30, 230, 90])
    
    # Colores modernos
    color_activo = colors.HexColor('#2c5f7d')  # Azul profesional
    color_pasivo = colors.HexColor('#8b3a3a')  # Rojo oscuro elegante
    color_fondo_total = colors.HexColor('#e8f4f8')  # Azul claro suave
    color_borde = colors.HexColor('#d0d0d0')  # Gris claro
    
    estilo_tabla = TableStyle([
        # Alineación general
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),  # Valores Activo
        ('ALIGN', (4, 0), (4, -1), 'RIGHT'),  # Valores Pasivo/Patrimonio
        
        # Encabezado Activo
        ('BACKGROUND', (0, 0), (1, 0), color_activo),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        
        # Encabezado Pasivo
        ('BACKGROUND', (3, 0), (4, 0), color_pasivo),
        ('TEXTCOLOR', (3, 0), (4, 0), colors.white),
        ('FONTNAME', (3, 0), (4, 0), 'Helvetica-Bold'),
        
        # Encabezado Patrimonio (encontrar su posición)
        ('BACKGROUND', (3, len(lista_pasivos)+3), (4, len(lista_pasivos)+3), color_pasivo),
        ('TEXTCOLOR', (3, len(lista_pasivos)+3), (4, len(lista_pasivos)+3), colors.white),
        ('FONTNAME', (3, len(lista_pasivos)+3), (4, len(lista_pasivos)+3), 'Helvetica-Bold'),
        
        # Rejilla suave
        ('GRID', (0, 0), (1, -2), 0.5, color_borde),
        ('GRID', (3, 0), (4, -2), 0.5, color_borde),
        
        # Padding para mejor legibilidad
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        
        # Resaltar la última fila (Totales finales)
        ('LINEABOVE', (0, -1), (1, -1), 2, colors.black),
        ('LINEABOVE', (3, -1), (4, -1), 2, colors.black),
        ('BACKGROUND', (0, -1), (1, -1), color_fondo_total),
        ('BACKGROUND', (3, -1), (4, -1), color_fondo_total),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
    ])

    # Si no cuadra, poner los totales en naranja llamativo
    if round(total_activo, 2) != round(total_pas_pat, 2):
        estilo_tabla.add('BACKGROUND', (0, -1), (1, -1), colors.orange)
        estilo_tabla.add('BACKGROUND', (3, -1), (4, -1), colors.orange)
        estilo_tabla.add('TEXTCOLOR', (0, -1), (-1, -1), colors.red)

    tabla.setStyle(estilo_tabla)
    elements.append(tabla)
    
    # 8. Nota al pie con validación
    elements.append(Spacer(1, 20))
    
    cuadra = round(total_activo, 2) == round(total_pas_pat, 2)
    if cuadra:
        nota_validacion = Paragraph(
            "✓ <b>Balance validado correctamente</b> - La ecuación contable se cumple (Activo = Pasivo + Patrimonio)",
            ParagraphStyle('Nota', parent=styles['Normal'], fontSize=8, textColor=colors.green)
        )
    else:
        nota_validacion = Paragraph(
            "⚠ <b>ADVERTENCIA:</b> El balance presenta inconsistencias. Revisar asientos contables.",
            ParagraphStyle('Nota', parent=styles['Normal'], fontSize=8, textColor=colors.red)
        )
    
    elements.append(nota_validacion)

    # 9. Generación del archivo
    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"Error PDF Balance General: {e}")
        return False