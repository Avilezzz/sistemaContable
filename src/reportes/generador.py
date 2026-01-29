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
    Genera el Estado de Resultados (Pérdidas y Ganancias).
    Retorna la UTILIDAD DEL EJERCICIO (float) para usarla en el Balance General.
    """
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # Título
    elements.append(Paragraph("<b>ESTADO DE RESULTADOS INTEGRAL</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # 1. INGRESOS (Clase 4)
    total_ingresos = obtener_saldo_cuenta(db, "4")
    
    # 2. GASTOS (Clase 5)
    total_gastos = obtener_saldo_cuenta(db, "5")
    
    # 3. COSTOS (Clase 6 - Opcional si usas costos de venta)
    total_costos = obtener_saldo_cuenta(db, "6")

    utilidad_ejercicio = total_ingresos - (total_gastos + total_costos)

    # Estructura visual
    data = [
        ["RUBRO", "VALOR"],
        ["(+) INGRESOS OPERATIVOS", f"{total_ingresos:,.2f}"],
        ["(-) GASTOS OPERATIVOS", f"{total_gastos:,.2f}"],
        ["(-) COSTOS DE VENTAS", f"{total_costos:,.2f}"],
        ["", ""], # Espacio
        ["UTILIDAD / (PÉRDIDA) DEL EJERCICIO", f"{utilidad_ejercicio:,.2f}"]
    ]

    t = Table(data, colWidths=[300, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'), # Números derecha
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        # Resaltar Resultado Final
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.black if utilidad_ejercicio >= 0 else colors.red),
    ]))
    
    elements.append(t)
    
    try:
        doc.build(elements)
        print(f"Estado de Resultados generado. Utilidad: {utilidad_ejercicio}")
        return utilidad_ejercicio # RETORNAMOS EL VALOR PARA EL BALANCE
    except Exception as e:
        print(f"Error PDF Estado Resultados: {e}")
        return 0.0

def generar_balance_general(db: Session, utilidad_ejercicio: float, nombre_archivo="balance_general.pdf"):
    # Usamos landscape (horizontal) para que quepan bien las dos columnas
    doc = SimpleDocTemplate(nombre_archivo, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("<b>ESTADO DE SITUACIÓN FINANCIERA (BALANCE GENERAL)</b>", styles['Title']))
    elements.append(Spacer(1, 12))

    # --- 1. Obtener saldos detallados ---
    def obtener_cuentas_con_saldo(prefijo):
        cuentas = db.query(Cuenta).filter(Cuenta.codigo.like(f"{prefijo}%")).order_by(Cuenta.codigo).all()
        lista_resultado = []
        total_grupo = 0.0
        for c in cuentas:
            # Solo incluimos cuentas con movimientos o que sean de detalle (puedes ajustar este filtro)
            debe = sum(d.debe for d in c.detalles)
            haber = sum(d.haber for d in c.detalles)
            
            saldo = (debe - haber) if c.naturaleza == 'DEUDORA' else (haber - debe)
            if abs(saldo) > 0.001: # Solo si tiene saldo
                lista_resultado.append([c.codigo, c.nombre, f"{saldo:,.2f}"])
                total_grupo += saldo
        return lista_resultado, total_grupo

    # Obtener datos
    lista_activos, total_activo = obtener_cuentas_con_saldo("1")
    lista_pasivos, total_pasivo = obtener_cuentas_con_saldo("2")
    lista_patrimonio, total_patrimonio_neto = obtener_cuentas_con_saldo("3")
    
    total_patrimonio_final = total_patrimonio_neto + utilidad_ejercicio
    
    # Combinar Pasivo y Patrimonio para el lado derecho
    derecha = [["", "<b>PASIVO</b>", ""]] + lista_pasivos + \
              [["", f"<b>TOTAL PASIVOS</b>", f"<b>{total_pasivo:,.2f}</b>"]] + \
              [["", "", ""], ["", "<b>PATRIMONIO</b>", ""]] + lista_patrimonio + \
              [["", "Resultado Ejercicio", f"{utilidad_ejercicio:,.2f}"],
               ["", f"<b>TOTAL PATRIMONIO</b>", f"<b>{total_patrimonio_final:,.2f}</b>"]]

    izquierda = [["", "<b>ACTIVO</b>", ""]] + lista_activos + \
                [["", f"<b>TOTAL ACTIVOS</b>", f"<b>{total_activo:,.2f}</b>"]]

    # --- 2. Emparejar las listas para la tabla ---
    data = [["CÓDIGO", "CUENTA (ACTIVOS)", "VALOR", "CÓDIGO", "CUENTA (PASIVO + PATR.)", "VALOR"]]
    
    max_rows = max(len(izquierda), len(derecha))
    for i in range(max_rows):
        fila = []
        # Lado izquierdo (Activos)
        if i < len(izquierda): fila.extend(izquierda[i])
        else: fila.extend(["", "", ""])
        
        # Lado derecho (Pasivo + Patrimonio)
        if i < len(derecha): fila.extend(derecha[i])
        else: fila.extend(["", "", ""])
        data.append(fila)

    # Fila final de validación (Ecuación Contable)
    total_derecho = total_pasivo + total_patrimonio_final
    data.append(["", "<b>TOTAL ACTIVO</b>", f"<b>{total_activo:,.2f}</b>", 
                 "", "<b>TOTAL PASIVO + PATRIMONIO</b>", f"<b>{total_derecho:,.2f}</b>"])

    # --- 3. Estilo de la Tabla ---
    t = Table(data, colWidths=[50, 200, 70, 50, 200, 70])
    estilo = TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'), # Valores izquierda
        ('ALIGN', (5, 0), (5, -1), 'RIGHT'), # Valores derecha
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgreen), # Fila final
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    t.setStyle(estilo)
    elements.append(t)

    # Alerta de descuadre
    if round(total_activo, 2) != round(total_derecho, 2):
        diff = round(total_activo - total_derecho, 2)
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b color='red'>ALERTA: EL BALANCE NO CUADRA POR {diff}</b>", styles['Normal']))

    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"Error PDF Balance General: {e}")
        return False