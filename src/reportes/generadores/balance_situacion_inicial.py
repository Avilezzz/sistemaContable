"""
Generador de Balance de Situación Inicial.
Muestra la situación financiera al inicio de las operaciones.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from src.modelos.entidades import Asiento, Cuenta
from src.servicios.empresa import obtener_empresa
from src.reportes.encabezado import crear_encabezado_empresa

def generar_balance_situacion_inicial(db: Session, nombre_archivo="balance_situacion_inicial.pdf"):
    """
    Genera el Balance de Situación Inicial usando el PRIMER asiento registrado.
    Este asiento debe ser el "Asiento de Apertura" que registra los saldos iniciales.
    
    Returns:
        bool: True si se generó exitosamente, False en caso contrario
    """
    # 1. OBTENER DATOS
    empresa = obtener_empresa(db)
    primer_asiento = db.query(Asiento).order_by(Asiento.fecha).first()
    
    if not primer_asiento:
        print("❌ No hay asientos registrados.")
        return False


    doc = SimpleDocTemplate(nombre_archivo, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    
    # 2. ENCABEZADO PROFESIONAL
    if empresa:
        elements.extend(
            crear_encabezado_empresa(
                empresa,
                "BALANCE DE SITUACIÓN INICIAL",
                fecha_inicio=primer_asiento.fecha,
                moneda="USD"
            )
        )
    else:
        elements.append(Paragraph("BALANCE DE SITUACIÓN INICIAL", styles['Title']))
        elements.append(Spacer(1, 12))
    
    # --- OBTENER EL PRIMER ASIENTO ---
    primer_asiento = db.query(Asiento).order_by(Asiento.fecha).first()
    
    if not primer_asiento:
        print("❌ No hay asientos registrados. Crea primero un asiento de apertura.")
        return False
    
    # Mostrar información del asiento de apertura
    fecha_texto = f"Al: {primer_asiento.fecha.strftime('%d de %B de %Y')}"
    elements.append(Paragraph(fecha_texto, styles['Heading3']))
    elements.append(Paragraph(f"Basado en: {primer_asiento.descripcion}", styles['Normal']))
    elements.append(Spacer(1, 15))
    
    # --- PROCESAR SOLO EL PRIMER ASIENTO ---
    # Diccionarios para agrupar por cuenta
    cuentas_activo = {}
    cuentas_pasivo = {}
    cuentas_patrimonio = {}
    
    for detalle in primer_asiento.detalles:
        cuenta = detalle.cuenta
        codigo_clase = cuenta.codigo[0]  # Primer dígito del código
        
        # Calcular el saldo de esta cuenta en el asiento
        saldo = detalle.debe - detalle.haber
        
        # Clasificar según la clase de cuenta
        if codigo_clase == '1':  # ACTIVOS (DEUDORA)
            if cuenta.codigo not in cuentas_activo:
                cuentas_activo[cuenta.codigo] = {
                    'nombre': cuenta.nombre,
                    'saldo': 0.0
                }
            cuentas_activo[cuenta.codigo]['saldo'] += saldo
            
        elif codigo_clase == '2':  # PASIVOS (ACREEDORA)
            if cuenta.codigo not in cuentas_pasivo:
                cuentas_pasivo[cuenta.codigo] = {
                    'nombre': cuenta.nombre,
                    'saldo': 0.0
                }
            # Para pasivos, el saldo es HABER - DEBE
            cuentas_pasivo[cuenta.codigo]['saldo'] += (detalle.haber - detalle.debe)
            
        elif codigo_clase == '3':  # PATRIMONIO (ACREEDORA)
            if cuenta.codigo not in cuentas_patrimonio:
                cuentas_patrimonio[cuenta.codigo] = {
                    'nombre': cuenta.nombre,
                    'saldo': 0.0
                }
            # Para patrimonio, el saldo es HABER - DEBE
            cuentas_patrimonio[cuenta.codigo]['saldo'] += (detalle.haber - detalle.debe)
    
    # --- CONSTRUIR LISTAS PARA LA TABLA ---
    def construir_lista(cuentas_dict, titulo):
        """Construye lista formateada de cuentas"""
        lista = [["", Paragraph(titulo, styles['Heading3']), ""]]
        total = 0.0
        
        for codigo in sorted(cuentas_dict.keys()):
            info = cuentas_dict[codigo]
            if abs(info['saldo']) > 0.01:  # Solo mostrar si tiene saldo
                lista.append([
                    codigo,
                    Paragraph(info['nombre'], styles['Normal']),
                    f"{info['saldo']:,.2f}"
                ])
                total += info['saldo']
        
        return lista, total
    
    # LADO IZQUIERDO - ACTIVOS
    lista_activos, total_activo = construir_lista(cuentas_activo, "ACTIVOS")
    izquierda = lista_activos + [
        ["", "", ""],
        ["", Paragraph("TOTAL ACTIVOS", styles['Heading3']), f"{total_activo:,.2f}"]
    ]
    
    # LADO DERECHO - PASIVOS + PATRIMONIO
    lista_pasivos, total_pasivo = construir_lista(cuentas_pasivo, "PASIVOS")
    lista_patrimonio, total_patrimonio = construir_lista(cuentas_patrimonio, "PATRIMONIO")
    
    total_pasivo_patrimonio = total_pasivo + total_patrimonio
    
    derecha = lista_pasivos + [
        ["", "", ""],
        ["", Paragraph("TOTAL PASIVOS", styles['Normal']), f"{total_pasivo:,.2f}"],
        ["", "", ""]
    ] + lista_patrimonio + [
        ["", "", ""],
        ["", Paragraph("TOTAL PATRIMONIO", styles['Normal']), f"{total_patrimonio:,.2f}"],
        ["", "", ""],
        ["", Paragraph("TOTAL PASIVO + PATRIMONIO", styles['Heading3']), f"{total_pasivo_patrimonio:,.2f}"]
    ]
    
    # --- EMPAREJAR COLUMNAS ---
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
    
    # --- CREAR TABLA ---
    t = Table(data, colWidths=[45, 200, 75, 45, 200, 75])
    estilo = TableStyle([
        # Encabezado
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        # Alineación
        ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        # Línea separadora
        ('LINEAFTER', (2, 0), (2, -1), 2, colors.darkgreen),
    ])
    t.setStyle(estilo)
    elements.append(t)
    
    # --- VALIDACIÓN ---
    diferencia = round(total_activo - total_pasivo_patrimonio, 2)
    elements.append(Spacer(1, 15))
    
    if abs(diferencia) < 0.01:
        msg = "✓ BALANCE CUADRADO: ACTIVO = PASIVO + PATRIMONIO"
        color_msg = colors.green
    else:
        msg = f"✗ DESCUADRE: ${abs(diferencia):,.2f}"
        color_msg = colors.red
    
    validacion_style = ParagraphStyle(
        'Validacion',
        parent=styles['Normal'],
        textColor=color_msg,
        fontSize=11,
        fontName='Helvetica-Bold',
        alignment=1
    )
    elements.append(Paragraph(msg, validacion_style))
    
    # Detalle
    elements.append(Spacer(1, 10))
    detalle = f"Activos: ${total_activo:,.2f} | Pasivos: ${total_pasivo:,.2f} | Patrimonio: ${total_patrimonio:,.2f}"
    elements.append(Paragraph(detalle, styles['Normal']))
    
    try:
        doc.build(elements)
        print(f"✅ Balance de Situación Inicial generado: {nombre_archivo}")
        return True
    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")
        return False
