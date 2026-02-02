"""
Generador de Libro Diario en formato PDF.
"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from src.modelos.entidades import Asiento
from src.servicios.empresa import obtener_empresa
from src.reportes.encabezado import crear_encabezado_empresa


def generar_pdf_libro_diario(db: Session, nombre_archivo="libro_diario.pdf"):
    """
    Genera un PDF con todos los asientos contables ordenados por fecha.
    Incluye encabezado profesional con datos de la empresa.
    
    FORMATO CONTABLE TRADICIONAL:
    - Cuentas del DEBE: Sin sangría (izquierda)
    - Cuentas del HABER: Con sangría (derecha) mediante indentación
    """
    # 1. OBTENER EMPRESA
    empresa = obtener_empresa(db)
    if not empresa:
        print("⚠️ [ADVERTENCIA] No hay empresa configurada. El reporte no tendrá encabezado.")
    
    # 2. CONSULTAR DATOS PRIMERO (para obtener el período)
    asientos = db.query(Asiento).order_by(Asiento.fecha).all()
    if not asientos:
        print("❌ No hay datos para generar el reporte.")
        return False
    
    # 3. OBTENER RANGO DE FECHAS (del primer al último asiento)
    fecha_inicio = asientos[0].fecha
    fecha_fin = asientos[-1].fecha
    
    # 4. CONFIGURAR DOCUMENTO
    doc = SimpleDocTemplate(nombre_archivo, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # 5. AGREGAR ENCABEZADO DE EMPRESA (SI EXISTE)
    if empresa:
        elements.extend(
            crear_encabezado_empresa(
                empresa,
                "LIBRO DIARIO",
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                moneda="USD"
            )
        )
    else:
        # Encabezado simple (fallback)
        titulo = Paragraph("LIBRO DIARIO", styles['Title'])
        elements.append(titulo)
        elements.append(Spacer(1, 12))
    
    # 6. PREPARAR DATOS PARA LA TABLA
    data = [['FECHA', 'CÓDIGO', 'CUENTA / DETALLE', 'DEBE', 'HABER']]
    total_debe_general = 0
    total_haber_general = 0
    
    # Procesar cada asiento
    for asiento in asientos:
        # Fila de Cabecera del Asiento (Fecha y Descripción)
        desc_asiento = Paragraph(
            f"Asiento #{asiento.id}: {asiento.descripcion}",
            styles['Normal']
        )
        data.append([str(asiento.fecha), "", desc_asiento, "", ""])
        
        # 1) SEPARAR PRIMERO EN DOS LISTAS: DEBE y HABER
        filas_debe = []
        filas_haber = []
        
        for detalle in asiento.detalles:
            # Cuenta del DEBE (sin sangría)
            if detalle.debe > 0:
                nombre_cuenta_debe = Paragraph(
                    f"{detalle.cuenta.nombre}",
                    styles['Normal']
                )
                filas_debe.append([
                    "",  # Fecha vacía
                    detalle.cuenta.codigo,
                    nombre_cuenta_debe,
                    f"{detalle.debe:,.2f}",
                    ""  # Haber vacío
                ])
            
            # Cuenta del HABER (con sangría)
            if detalle.haber > 0:
                nombre_cuenta_haber = Paragraph(
                    f"    {detalle.cuenta.nombre}",
                    styles['Normal']
                )
                filas_haber.append([
                    "",  # Fecha vacía
                    detalle.cuenta.codigo,
                    nombre_cuenta_haber,
                    "",  # Debe vacío
                    f"{detalle.haber:,.2f}"
                ])
            
            # Acumular totales generales
            total_debe_general += detalle.debe
            total_haber_general += detalle.haber
        
        # 2) PRIMERO AGREGAMOS TODAS LAS DEL DEBE
        for fila in filas_debe:
            data.append(fila)
        
        # 3) LUEGO TODAS LAS DEL HABER (ordenadas e identadas)
        for fila in filas_haber:
            data.append(fila)
        
        data.append(["", "", "", "", ""])
    
    # Fila de Totales Generales
    data.append([
        "TOTALES", "", "",
        f"{total_debe_general:,.2f}",
        f"{total_haber_general:,.2f}"
    ])
    
    # 7. CREAR Y ESTILIZAR LA TABLA
    t = Table(data, colWidths=[70, 60, 250, 60, 60])
    estilo_tabla = TableStyle([
        # Encabezado de columnas
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # Alineación general
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),  # Números a la derecha
        # Bordes
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        # Resaltar fila de totales
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ])
    t.setStyle(estilo_tabla)
    elements.append(t)
    
    # 8. AGREGAR PIE DE PÁGINA
    elements.append(Spacer(1, 20))
    estilo_footer = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1
    )
    footer_text = f"Total de asientos registrados: {len(asientos)}"
    elements.append(Paragraph(footer_text, estilo_footer))
    
    # Verificación de cuadre
    if abs(total_debe_general - total_haber_general) < 0.01:
        validacion = Paragraph(
            "✓ Libro Diario Cuadrado (Debe = Haber)",
            ParagraphStyle('Valid', parent=styles['Normal'],
                         textColor=colors.green, alignment=1, fontSize=9)
        )
    else:
        validacion = Paragraph(
            f"⚠ ADVERTENCIA: Descuadre de ${abs(total_debe_general - total_haber_general):,.2f}",
            ParagraphStyle('Alert', parent=styles['Normal'],
                         textColor=colors.red, alignment=1, fontSize=9)
        )
    elements.append(validacion)
    
    # 9. CONSTRUIR PDF
    try:
        doc.build(elements)
        print(f"✅ PDF generado exitosamente: {nombre_archivo}")
        return True
    except Exception as e:
        print(f"❌ Error al generar PDF: {e}")
        return False
