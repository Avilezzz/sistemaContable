# src/reportes/encabezado.py
from reportlab.platypus import Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from datetime import datetime

def crear_encabezado_empresa(empresa, titulo_reporte, fecha_inicio=None, fecha_fin=None, moneda="USD"):
    """
    Crea un encabezado LIMPIO y PROFESIONAL para reportes contables.
    
    Formato estándar:
        NOMBRE DE LA EMPRESA
        TÍTULO DEL REPORTE
        Del DD/MM/YYYY al DD/MM/YYYY (si aplica)
        Moneda: USD
    
    Args:
        empresa: Objeto Empresa de la BD
        titulo_reporte: Título del reporte (ej: "LIBRO DIARIO")
        fecha_inicio: Fecha inicial del período (opcional)
        fecha_fin: Fecha final del período (opcional)
        moneda: Código de moneda (default: "USD")
    
    Returns:
        Lista de elementos Platypus para agregar al documento
    """
    elements = []
    styles = getSampleStyleSheet()
    
    # ESTILO 1: Nombre de la Empresa
    estilo_empresa = ParagraphStyle(
        'EmpresaNombre',
        parent=styles['Normal'],
        fontSize=14,
        fontName='Helvetica-Bold',
        alignment=1,  # Centrado
        spaceAfter=4,
        textColor=colors.black
    )
    
    # ESTILO 2: Título del Reporte
    estilo_titulo = ParagraphStyle(
        'TituloReporte',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=1,  # Centrado
        spaceAfter=4,
        textColor=colors.black
    )
    
    # ESTILO 3: Información secundaria (período, moneda)
    estilo_info = ParagraphStyle(
        'InfoReporte',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica',
        alignment=1,  # Centrado
        spaceAfter=3,
        textColor=colors.black
    )
    
    # 1. NOMBRE DE LA EMPRESA
    nombre_empresa = (empresa.nombre_comercial or empresa.nombre).upper()
    elements.append(Paragraph(nombre_empresa, estilo_empresa))
    
    # 2. TÍTULO DEL REPORTE
    elements.append(Paragraph(titulo_reporte.upper(), estilo_titulo))
    
    # 3. PERÍODO (si se proporcionan fechas)
    if fecha_inicio and fecha_fin:
        # Formatear fechas en español
        inicio_str = fecha_inicio.strftime("%d de %B de %Y") if hasattr(fecha_inicio, 'strftime') else str(fecha_inicio)
        fin_str = fecha_fin.strftime("%d de %B de %Y") if hasattr(fecha_fin, 'strftime') else str(fecha_fin)
        
        periodo_text = f"Del {inicio_str} al {fin_str}"
        elements.append(Paragraph(periodo_text, estilo_info))
    elif fecha_inicio:
        # Solo fecha de inicio (para reportes a una fecha específica)
        fecha_str = fecha_inicio.strftime("%d de %B de %Y") if hasattr(fecha_inicio, 'strftime') else str(fecha_inicio)
        elements.append(Paragraph(f"Al {fecha_str}", estilo_info))
    
    # 4. MONEDA
    elements.append(Paragraph(f"Moneda: {moneda}", estilo_info))
    
    # 5. SEPARADOR
    elements.append(Spacer(1, 15))
    
    return elements
