"""
Módulo coordinador de generadores de reportes contables.
Re-exporta todas las funciones desde los módulos especializados.
"""

from .generadores.libro_diario import generar_pdf_libro_diario
from .generadores.libro_mayor import generar_pdf_libro_mayor
from .generadores.balance_comprobacion import generar_balance_comprobacion
from .generadores.estados_financieros import generar_estado_resultados, generar_balance_general

# Re-exportar para mantener compatibilidad con main.py
__all__ = [
    'generar_pdf_libro_diario',
    'generar_pdf_libro_mayor',
    'generar_balance_comprobacion',
    'generar_estado_resultados',
    'generar_balance_general'
]
