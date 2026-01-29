from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy.orm import Session
from src.modelos.entidades import Producto

def _crear_pdf_kardex(nombre_archivo, titulo, lista_datos_productos):
    """
    Función visual que genera el documento PDF. 
    Recibe los datos ya calculados por FIFO o PMP.
    """
    doc = SimpleDocTemplate(nombre_archivo, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()

    elements.append(Paragraph(f"<b>{titulo}</b>", styles['Title']))
    elements.append(Spacer(1, 15))

    if not lista_datos_productos:
        elements.append(Paragraph("No hay movimientos registrados en el sistema.", styles['Normal']))
        try:
            doc.build(elements)
            return True
        except: return False

    for prod_data in lista_datos_productos:
        elements.append(Paragraph(f"PRODUCTO: {prod_data['codigo']} - {prod_data['nombre']}", styles['Heading2']))
        elements.append(Spacer(1, 5))

        headers_1 = ['FECHA', 'DETALLE', 'ENTRADAS', '', '', 'SALIDAS', '', '', 'SALDOS', '', '']
        headers_2 = ['', '', 'Cant', 'Costo', 'Total', 'Cant', 'Costo', 'Total', 'Cant', 'Costo', 'Total']

        data = [headers_1, headers_2]
        data.extend(prod_data['filas'])

        t = Table(data, colWidths=[65, 60, 40, 45, 55, 40, 45, 55, 40, 45, 55])
        
        estilo = TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('SPAN', (0, 0), (0, 1)), ('SPAN', (1, 0), (1, 1)),
            ('SPAN', (2, 0), (4, 0)), ('SPAN', (5, 0), (7, 0)), ('SPAN', (8, 0), (10, 0)),
            ('BACKGROUND', (0, 0), (-1, 1), colors.darkcyan),
            ('TEXTCOLOR', (0, 0), (-1, 1), colors.white),
            ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ])
        
        t.setStyle(estilo)
        elements.append(t)
        elements.append(Spacer(1, 20))

    try:
        doc.build(elements)
        return True
    except Exception as e:
        print(f"Error PDF: {e}")
        return False

# ==========================================
# LÓGICA DE RECALCULO FIFO (PEPS)
# ==========================================
def generar_reporte_fifo(db: Session):
    productos = db.query(Producto).all()
    datos_procesados = []

    for prod in productos:
        filas = []
        lotes_fifo = [] # Memoria temporal: [{'cant': int, 'costo': float}]
        saldo_cant = 0
        saldo_valor = 0.0

        movimientos = sorted(prod.movimientos, key=lambda x: (x.fecha, x.id))

        for m in movimientos:
            row = [str(m.fecha), m.tipo]
            
            if m.tipo == 'COMPRA':
                lotes_fifo.append({'cant': m.cantidad, 'costo': m.costo_unitario})
                row.extend([str(m.cantidad), f"{m.costo_unitario:.2f}", f"{m.costo_total:.2f}", "", "", ""])
                saldo_cant += m.cantidad
                saldo_valor += m.costo_total
            else: # VENTA
                cant_a_vender = m.cantidad
                costo_venta_total = 0.0
                
                # Consumimos lotes virtuales para el reporte
                while cant_a_vender > 0 and lotes_fifo:
                    lote = lotes_fifo[0]
                    tomar = min(cant_a_vender, lote['cant'])
                    costo_venta_total += tomar * lote['costo']
                    lote['cant'] -= tomar
                    cant_a_vender -= tomar
                    if lote['cant'] == 0:
                        lotes_fifo.pop(0)

                costo_unit_puro = costo_venta_total / m.cantidad if m.cantidad > 0 else 0
                row.extend(["", "", "", str(m.cantidad), f"{costo_unit_puro:.2f}", f"{costo_venta_total:.2f}"])
                saldo_cant -= m.cantidad
                saldo_valor -= costo_venta_total

            unit_saldo = saldo_valor / saldo_cant if saldo_cant > 0 else 0
            row.extend([str(saldo_cant), f"{unit_saldo:.2f}", f"{saldo_valor:.2f}"])
            filas.append(row)

        datos_procesados.append({'codigo': prod.codigo, 'nombre': prod.nombre, 'filas': filas})

    return _crear_pdf_kardex("reporte_fifo.pdf", "KARDEX MÉTODO FIFO (RECALCULADO)", datos_procesados)

# ==========================================
# LÓGICA DE RECALCULO PMP (PROMEDIO)
# ==========================================
def generar_reporte_pmp(db: Session):
    productos = db.query(Producto).all()
    datos_procesados = []

    for prod in productos:
        filas = []
        saldo_cant = 0
        saldo_valor = 0.0
        promedio_actual = 0.0

        movimientos = sorted(prod.movimientos, key=lambda x: (x.fecha, x.id))

        for m in movimientos:
            row = [str(m.fecha), m.tipo]
            
            if m.tipo == 'COMPRA':
                row.extend([str(m.cantidad), f"{m.costo_unitario:.2f}", f"{m.costo_total:.2f}", "", "", ""])
                saldo_cant += m.cantidad
                saldo_valor += m.costo_total
                promedio_actual = saldo_valor / saldo_cant if saldo_cant > 0 else 0
            else: # VENTA
                costo_venta = m.cantidad * promedio_actual
                row.extend(["", "", "", str(m.cantidad), f"{promedio_actual:.2f}", f"{costo_venta:.2f}"])
                saldo_cant -= m.cantidad
                saldo_valor -= costo_venta
                # El promedio no cambia en la venta, solo en la compra

            row.extend([str(saldo_cant), f"{promedio_actual:.2f}", f"{saldo_valor:.2f}"])
            filas.append(row)

        datos_procesados.append({'codigo': prod.codigo, 'nombre': prod.nombre, 'filas': filas})

    return _crear_pdf_kardex("reporte_pmp.pdf", "KARDEX PROMEDIO PONDERADO (RECALCULADO)", datos_procesados)