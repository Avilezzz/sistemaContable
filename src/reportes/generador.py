from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from src.modelos.entidades import Asiento
from src.modelos.entidades import Cuenta
from reportlab.lib.pagesizes import landscape, A4

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

# ===========================================
# FUNCIONES CORREGIDAS PARA ESTADOS FINANCIEROS
# ===========================================

def obtener_saldo_cuenta(db: Session, codigo_cuenta: str):
    """
    Auxiliar: Calcula el saldo final de una cuenta o grupo de cuentas.
    CORRECCIÓN: Ahora respeta correctamente la naturaleza de cada cuenta.
    """
    # Buscamos todas las cuentas que empiecen con ese código (ej: "1" trae todo activo)
    cuentas = db.query(Cuenta).filter(Cuenta.codigo.like(f"{codigo_cuenta}%")).all()
    
    saldo_total = 0.0
    
    for cuenta in cuentas:
        if not cuenta.detalles: 
            continue
        
        debe = sum(d.debe for d in cuenta.detalles)
        haber = sum(d.haber for d in cuenta.detalles)
        
        # CORRECCIÓN: Respetar la naturaleza de la cuenta
        if cuenta.naturaleza.upper() == 'DEUDORA':
            # Para cuentas deudoras: DEBE aumenta, HABER disminuye
            saldo_total += (debe - haber)
        else:  # ACREEDORA
            # Para cuentas acreedoras: HABER aumenta, DEBE disminuye
            saldo_total += (haber - debe)
            
    return saldo_total

def generar_estado_resultados(db: Session, nombre_archivo="estado_resultados.pdf"):
    """
    VERSIÓN CORREGIDA: Genera el Estado de Resultados (Pérdidas y Ganancias).
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
    elements.append(Paragraph("<b>ESTADO DE RESULTADOS INTEGRAL</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # 1. INGRESOS (Clase 4 - ACREEDORA)
    # Los ingresos aumentan con HABER, disminuyen con DEBE
    total_ingresos = obtener_saldo_cuenta(db, "4")
    
    # 2. COSTOS DE VENTAS (Clase 6 - DEUDORA) 
    # Los costos aumentan con DEBE, disminuyen con HABER
    total_costos = obtener_saldo_cuenta(db, "6")
    
    # 3. UTILIDAD BRUTA
    utilidad_bruta = total_ingresos - total_costos
    
    # 4. GASTOS OPERACIONALES (Clase 5 - DEUDORA)
    # Los gastos aumentan con DEBE, disminuyen con HABER
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
        ["    Gastos Administrativos y de Ventas", f"{total_gastos:,.2f}", ""],
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
        f"<b>Nota:</b> Los saldos se calculan respetando la naturaleza de cada cuenta. "
        f"Ingresos (Acreedores) = Haber - Debe. Gastos y Costos (Deudores) = Debe - Haber.",
        nota_style
    )
    elements.append(nota)
    
    try:
        doc.build(elements)
        print(f"Estado de Resultados generado. Utilidad: ${utilidad_ejercicio:,.2f}")
        return utilidad_ejercicio # RETORNAMOS EL VALOR PARA EL BALANCE
    except Exception as e:
        print(f"Error PDF Estado Resultados: {e}")
        return 0.0

def generar_balance_general(db: Session, utilidad_ejercicio: float, nombre_archivo="balance_general.pdf"):
    """
    VERSIÓN CORREGIDA: Genera el Balance General (Estado de Situación Financiera).
    
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
    
    elements.append(Paragraph("<b>ESTADO DE SITUACIÓN FINANCIERA (BALANCE GENERAL)</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # --- FUNCIÓN AUXILIAR MEJORADA ---
    def obtener_cuentas_con_saldo_detallado(prefijo):
        """
        Obtiene las cuentas con saldo de un grupo específico.
        Retorna: (lista_filas, total_grupo)
        """
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
            
            # CORRECCIÓN: Calcular saldo según naturaleza
            if c.naturaleza.upper() == 'DEUDORA':
                saldo = debe - haber
            else:  # ACREEDORA
                saldo = haber - debe
            
            # Solo incluir si tiene saldo significativo
            if abs(saldo) > 0.01:
                # Indentación visual según nivel de cuenta
                nivel = c.codigo.count('.')
                indent = "    " * nivel
                nombre_indentado = f"{indent}{c.nombre}"
                
                lista_resultado.append([
                    c.codigo, 
                    Paragraph(nombre_indentado, styles['Normal']), 
                    f"{saldo:,.2f}"
                ])
                total_grupo += saldo
        
        return lista_resultado, total_grupo

    # --- OBTENER DATOS ---
    # ACTIVOS (Clase 1 - DEUDORA)
    lista_activos, total_activo = obtener_cuentas_con_saldo_detallado("1")
    
    # PASIVOS (Clase 2 - ACREEDORA)
    lista_pasivos, total_pasivo = obtener_cuentas_con_saldo_detallado("2")
    
    # PATRIMONIO (Clase 3 - ACREEDORA)
    lista_patrimonio_base, total_patrimonio_base = obtener_cuentas_con_saldo_detallado("3")
    
    # PATRIMONIO TOTAL = Patrimonio Base + Utilidad del Ejercicio
    total_patrimonio_final = total_patrimonio_base + utilidad_ejercicio
    
    # --- CONSTRUCCIÓN DEL LADO IZQUIERDO (ACTIVOS) ---
    izquierda = [
        ["", Paragraph("<b>ACTIVOS</b>", styles['Heading3']), ""]
    ] + lista_activos + [
        ["", "", ""],
        ["", Paragraph("<b>TOTAL ACTIVOS</b>", styles['Heading3']), f"<b>{total_activo:,.2f}</b>"]
    ]

    # --- CONSTRUCCIÓN DEL LADO DERECHO (PASIVOS + PATRIMONIO) ---
    derecha = [
        ["", Paragraph("<b>PASIVOS</b>", styles['Heading3']), ""]
    ] + lista_pasivos + [
        ["", "", ""],
        ["", Paragraph("<b>TOTAL PASIVOS</b>", styles['Normal']), f"<b>{total_pasivo:,.2f}</b>"],
        ["", "", ""],
        ["", Paragraph("<b>PATRIMONIO</b>", styles['Heading3']), ""]
    ] + lista_patrimonio_base + [
        ["", Paragraph("Resultado del Ejercicio", styles['Normal']), f"{utilidad_ejercicio:,.2f}"],
        ["", "", ""],
        ["", Paragraph("<b>TOTAL PATRIMONIO</b>", styles['Normal']), f"<b>{total_patrimonio_final:,.2f}</b>"],
        ["", "", ""],
        ["", Paragraph("<b>TOTAL PASIVO + PATRIMONIO</b>", styles['Heading3']), f"<b>{(total_pasivo + total_patrimonio_final):,.2f}</b>"]
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
        print(f"Balance General generado exitosamente.")
        return True
    except Exception as e:
        print(f"Error al generar PDF Balance General: {e}")
        return False