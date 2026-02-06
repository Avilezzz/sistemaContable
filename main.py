import sys
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint

# Importaciones locales
from src.base_datos.db import init_db, get_db, close_engine
from src.servicios.contabilidad import importar_plan_cuentas_desde_excel, registrar_asiento
from src.modelos.entidades import Cuenta
from src.reportes.generador import (
    generar_pdf_libro_diario, 
    generar_pdf_libro_mayor, 
    generar_balance_comprobacion,
    generar_estado_resultados, 
    generar_balance_general,
    generar_balance_situacion_inicial
)
from src.servicios.inventario import (
    crear_producto,
    registrar_compra_con_asiento,
    registrar_venta_con_asientos
)

from src.reportes.kardex_pdf import generar_reporte_fifo, generar_reporte_pmp
from src.servicios.empresa import configurar_empresa, obtener_empresa, empresa_configurada

console = Console()

# ============================================
# CONSTANTES DEL MENÚ
# ============================================
class OpcionMenu:
    """Enumeración de opciones del menú principal"""
    CONFIGURAR_EMPRESA = "0"
    LIMPIAR_DATOS = "1"
    IMPORTAR_PLAN = "2"
    REGISTRAR_ASIENTO = "3"
    BALANCE_SITUACION = "4"
    LIBRO_DIARIO = "5"
    LIBRO_MAYOR = "6"
    BALANCE_COMPROBACION = "7"
    ESTADOS_FINANCIEROS = "8"
    INVENTARIOS = "9"
    SALIR = "10"

# ============================================
# FUNCIONES DE UTILIDAD
# ============================================
def pausar():
    """Pausa la ejecución hasta que el usuario presione Enter"""
    input("\n[Presione Enter para continuar...]")

def confirmar_accion(mensaje: str, advertencia: str = None) -> bool:
    """
    Solicita confirmación del usuario para acciones críticas
    
    Args:
        mensaje: Pregunta a mostrar
        advertencia: Mensaje de advertencia adicional (opcional)
    
    Returns:
        bool: True si el usuario confirma, False en caso contrario
    """
    if advertencia:
        console.print(f"\n[bold yellow]⚠ {advertencia}[/bold yellow]")
    
    return Confirm.ask(mensaje, default=False)

# ============================================
# CONFIGURACIÓN DE EMPRESA
# ============================================
def vista_configurar_empresa():
    """Configurar o editar datos de la empresa"""
    console.clear()
    console.print(Panel("[bold cyan]CONFIGURACIÓN DE EMPRESA[/bold cyan]"))
    
    db = next(get_db())
    empresa_actual = obtener_empresa(db)
    
    if empresa_actual:
        console.print("\n[yellow]Empresa existente encontrada. Los datos actuales se sobrescribirán.[/yellow]")
        console.print(f"Nombre actual: {empresa_actual.nombre}")
    
    # Solicitar datos
    datos = {}
    datos['ruc'] = Prompt.ask("RUC/Identificación Fiscal", 
                               default=empresa_actual.ruc if empresa_actual else "")
    datos['nombre'] = Prompt.ask("Nombre Legal de la Empresa",
                                  default=empresa_actual.nombre if empresa_actual else "")
    datos['nombre_comercial'] = Prompt.ask("Nombre Comercial (opcional)",
                                           default=empresa_actual.nombre_comercial if empresa_actual else "")
    datos['direccion'] = Prompt.ask("Dirección",
                                    default=empresa_actual.direccion if empresa_actual else "")
    datos['telefono'] = Prompt.ask("Teléfono",
                                   default=empresa_actual.telefono if empresa_actual else "")
    datos['email'] = Prompt.ask("Email",
                                default=empresa_actual.email if empresa_actual else "")
    datos['ciudad'] = Prompt.ask("Ciudad",
                                 default=empresa_actual.ciudad if empresa_actual else "Babahoyo")
    datos['pais'] = Prompt.ask("País",
                               default=empresa_actual.pais if empresa_actual else "Ecuador")
    
    # Guardar
    exito, msg, empresa = configurar_empresa(db, datos)
    
    if exito:
        console.print(f"\n[bold green]✓ {msg}[/bold green]")
        console.print(f"\n[cyan]Empresa: {empresa.nombre}[/cyan]")
        console.print(f"[cyan]RUC: {empresa.ruc}[/cyan]")
    else:
        console.print(f"\n[bold red]✗ {msg}[/bold red]")
    
    pausar()

# ============================================
# SELECTOR DE CUENTAS
# ============================================
def seleccionar_cuenta_interactiva(db):
    """
    Permite buscar y seleccionar una cuenta visualmente sin saber el código.
    """
    while True:
        console.print("\n[bold cyan]--- BUSCADOR DE CUENTAS ---[/bold cyan]")
        console.print("Escriba parte del nombre (ej: 'Caja') o presione [Enter] para ver todo.")
        criterio = Prompt.ask("[bold yellow]Buscar[/bold yellow]", default="VER")

        if criterio.upper() == "VER":
            # Mostrar Árbol Completo
            cuentas = db.query(Cuenta).order_by(Cuenta.codigo).all()
            if not cuentas:
                console.print("[red]No hay cuentas. Importe el Excel primero.[/red]")
                return None
            
            # Crear tabla visual
            console.print("\n[bold white]PLAN DE CUENTAS[/bold white]")
            
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("#", style="dim", width=4)
            table.add_column("Código", style="cyan", width=12)
            table.add_column("Cuenta", style="white")
            table.add_column("Tipo", style="green")

            opciones_validas = []
            
            for idx, c in enumerate(cuentas):
                # Indentación visual simple basada en los puntos del código
                indent = "  " * (c.codigo.count('.')) 
                nombre_fmt = f"{indent}{c.nombre}"
                
                table.add_row(str(idx + 1), c.codigo, nombre_fmt, c.naturaleza)
                opciones_validas.append(c)

            console.print(table)
            
            # Selección
            try:
                seleccion = IntPrompt.ask("\n[bold green]Seleccione el número (#)[/bold green] o 0 para cancelar")
                if seleccion == 0: 
                    return None
                if 1 <= seleccion <= len(opciones_validas):
                    return opciones_validas[seleccion - 1].codigo
                else:
                    console.print("[red]Número inválido[/red]")
            except:
                pass

        else:
            # Buscar por texto (filtro)
            cuentas = db.query(Cuenta).filter(Cuenta.nombre.ilike(f"%{criterio}%")).all()
            
            if not cuentas:
                console.print(f"[red]No se encontraron cuentas con '{criterio}'[/red]")
                continue

            # Mostrar tabla de resultados filtrados
            table = Table(title=f"Resultados para '{criterio}'")
            table.add_column("#", justify="right", style="cyan", no_wrap=True)
            table.add_column("Código", style="magenta")
            table.add_column("Nombre", style="green")
            
            for idx, c in enumerate(cuentas):
                table.add_row(str(idx + 1), c.codigo, c.nombre)
            
            console.print(table)
            
            sel_str = Prompt.ask("Seleccione # (o Enter para buscar de nuevo)")
            if sel_str.isdigit():
                sel = int(sel_str)
                if 1 <= sel <= len(cuentas):
                    return cuentas[sel - 1].codigo

# ============================================
# REGISTRO DE ASIENTOS
# ============================================
def vista_registrar_asiento():
    """Interfaz interactiva para crear un asiento"""
    console.clear()
    console.print(Panel("[bold cyan]NUEVO ASIENTO CONTABLE[/bold cyan]"))
    
    fecha_str = Prompt.ask("Fecha (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
    descripcion = Prompt.ask("Descripción del asiento")
    
    movimientos = []
    
    # Obtenemos sesión de BD una vez para usarla en el selector
    db_gen = get_db()
    db = next(db_gen)
    
    while True:
        console.clear()
        console.print(Panel(f"[bold]Asiento:[/bold] {descripcion} ({fecha_str})"))
        
        # Mostrar tabla temporal del asiento en construcción
        table = Table()
        table.add_column("Cta")
        table.add_column("Nombre")
        table.add_column("Debe", justify="right", style="green")
        table.add_column("Haber", justify="right", style="red")
        
        sum_debe = 0
        sum_haber = 0
        
        for m in movimientos:
            table.add_row(m['cuenta_codigo'], m['nombre_cuenta'], f"{m['debe']:.2f}", f"{m['haber']:.2f}")
            sum_debe += m['debe']
            sum_haber += m['haber']
            
        console.print(table)
        console.print(f"Total Debe: [green]{sum_debe:.2f}[/green] | Total Haber: [red]{sum_haber:.2f}[/red]")
        diferencia = round(sum_debe - sum_haber, 2)
        
        if diferencia == 0 and len(movimientos) > 0:
            console.print("[bold green]✔ ASIENTO CUADRADO - LISTO PARA GUARDAR[/bold green]")
        elif len(movimientos) > 0:
            console.print(f"[bold red]⚠ DESCUADRE: {diferencia}[/bold red]")

        # Menú de acciones
        console.print("\n[bold]Opciones:[/bold]")
        console.print("[A] Agregar Cuenta | [G] Guardar Asiento | [C] Cancelar y Salir")
        accion = Prompt.ask("Elija opción", choices=["a", "g", "c"], default="a")
        
        if accion == "c":
            break
            
        if accion == "g":
            if diferencia != 0:
                console.print("[bold red]No se puede guardar un asiento descuadrado.[/bold red]")
                pausar()
                continue
            if len(movimientos) == 0:
                console.print("[bold red]El asiento está vacío.[/bold red]")
                pausar()
                continue
                
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            
            # Pasamos solo los datos necesarios al servicio
            movimientos_data = [{'cuenta_codigo': m['cuenta_codigo'], 'debe': m['debe'], 'haber': m['haber']} for m in movimientos]
            
            exito, msg = registrar_asiento(db, fecha_obj, descripcion, movimientos_data)
            if exito:
                console.print(f"[bold green]{msg}[/bold green]")
                pausar()
                break
            else:
                console.print(f"[bold red]{msg}[/bold red]")
                pausar()
            continue

        # Uso del selector
        if accion == "a":
            codigo_seleccionado = seleccionar_cuenta_interactiva(db)
            
            if codigo_seleccionado:
                cuenta_obj = db.query(Cuenta).filter(Cuenta.codigo == codigo_seleccionado).first()
                
                console.print(f"\n[italic cyan]Seleccionado: {cuenta_obj.nombre} ({cuenta_obj.codigo})[/italic cyan]")
                
                monto_str = Prompt.ask("Monto (Escriba valor positivo)")
                try:
                    monto = float(monto_str)
                except ValueError:
                    console.print("[red]Monto inválido[/red]")
                    continue

                tipo_mov = Prompt.ask("¿Va al [D]ebe o al [H]aber?", choices=["d", "h"], default="d")
                
                debe = monto if tipo_mov == "d" else 0.0
                haber = monto if tipo_mov == "h" else 0.0
                
                movimientos.append({
                    "cuenta_codigo": cuenta_obj.codigo,
                    "nombre_cuenta": cuenta_obj.nombre,
                    "debe": debe,
                    "haber": haber
                })

# ============================================
# MÓDULO DE INVENTARIOS
# ============================================
def menu_inventario():
    """Submenú del módulo de inventarios"""
    while True:
        console.clear()
        console.print(Panel("[bold magenta]MÓDULO DE INVENTARIOS Y KARDEX (SISTEMA HÍBRIDO)[/bold magenta]"))
        console.print("[1] 📦 Crear Producto Nuevo (Neutro)")
        console.print("[2] 📥 Registrar COMPRA (Entrada)")
        console.print("[3] 📤 Registrar VENTA (Salida)")
        console.print("[4] 📄 Reportes KARDEX (PDF)")
        console.print("[5] 🔙 Volver al Menú Principal")
        
        op = Prompt.ask("Seleccione", choices=["1", "2", "3", "4", "5"])
        
        db = next(get_db())
        
        if op == "1":
            cod = Prompt.ask("Código Producto")
            nom = Prompt.ask("Nombre")
            try:
                crear_producto(db, cod, nom)
                console.print(f"[green]✓ Producto '{nom}' creado exitosamente.[/green]")
            except:
                console.print("[red]✗ Error: El código ya existe o hubo un problema con la BD.[/red]")
            pausar()
            
        elif op == "2":
            cod = Prompt.ask("Código Producto")
            cant = int(Prompt.ask("Cantidad"))
            costo = float(Prompt.ask("Costo Unitario"))
            fecha_str = Prompt.ask("Fecha (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()

            es_credito = Confirm.ask("¿Compra a crédito (Proveedores)?", default=False)

            ok, msg = registrar_compra_con_asiento(db, cod, fecha, cant, costo, es_credito=es_credito)
            console.print(f"[{'green' if ok else 'red'}]{msg}[/]")
            pausar()


        elif op == "3":
            cod = Prompt.ask("Código Producto")
            cant = int(Prompt.ask("Cantidad a Vender"))
            precio = float(Prompt.ask("Precio Unitario de Venta (sin IVA)"))
        
            fecha_str = Prompt.ask("Fecha (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        
            es_credito = Confirm.ask("¿Venta a crédito (Clientes)?", default=False)
        
            ok, msg = registrar_venta_con_asientos(db, cod, fecha, cant, precio_unit_venta=precio, es_credito=es_credito)
            console.print(f"[{'green' if ok else 'red'}]{msg}[/]")
            pausar()


        elif op == "4":
            console.print("\n[bold cyan]SELECCIONE LÓGICA DE REPORTE:[/bold cyan]")
            console.print("[1] 📊 Ver bajo lógica FIFO (PEPS)")
            console.print("[2] 📈 Ver bajo lógica Promedio Ponderado (PMP)")
            console.print("[0] Cancelar")
            
            sub_op = Prompt.ask("Opción", choices=["1", "2", "0"])
            
            if sub_op == "1":
                if generar_reporte_fifo(db):
                     console.print("[bold green]✔ Reporte generado: reporte_fifo.pdf[/bold green]")
                     try: 
                         os.startfile("reporte_fifo.pdf")
                     except: 
                         pass
                else:
                    console.print("[yellow]No se pudo generar el reporte FIFO.[/yellow]")
            
            elif sub_op == "2":
                if generar_reporte_pmp(db):
                     console.print("[bold green]✔ Reporte generado: reporte_pmp.pdf[/bold green]")
                     try: 
                         os.startfile("reporte_pmp.pdf")
                     except: 
                         pass
                else:
                    console.print("[yellow]No se pudo generar el reporte PMP.[/yellow]")
            
            pausar()

        elif op == "5":
            break

# ============================================
# OPCIONES DEL MENÚ PRINCIPAL
# ============================================
def opcion_limpiar_datos():
    """Limpiar todos los datos de la base de datos (ideal para demos en clase)"""
    console.clear()
    console.print(Panel(
        "[bold cyan]🧹 LIMPIAR TODOS LOS DATOS[/bold cyan]\n\n"
        "[yellow]Esta opción es ideal para demostraciones en clase[/yellow]\n\n"
        "Se eliminarán:\n"
        "  ✓ Todos los asientos contables\n"
        "  ✓ Todas las cuentas del plan\n"
        "  ✓ Todos los productos e inventarios\n"
        "  ✓ Configuración de empresa\n\n"
        "[green]La estructura de la base de datos permanece intacta[/green]\n"
        "[cyan]Después podrá importar el plan de cuentas nuevamente[/cyan]",
        border_style="cyan"
    ))
    
    # Confirmación simple para demos rápidas
    if not Confirm.ask("\n¿Limpiar todos los datos?", default=False):
        console.print("[yellow]Operación cancelada[/yellow]")
        pausar()
        return
    
    try:
        db = next(get_db())
        
        with console.status("[bold blue]Limpiando base de datos...[/bold blue]", spinner="dots"):
            # Importar los modelos necesarios
            from src.modelos.entidades import (
                Empresa, Cuenta, Asiento, DetalleAsiento,
                Producto, MovimientoInventario
            )
            
            # Contar registros antes de eliminar
            total_registros = (
                db.query(DetalleAsiento).count() +
                db.query(Asiento).count() +
                db.query(MovimientoInventario).count() +
                db.query(Producto).count() +
                db.query(Cuenta).count() +
                db.query(Empresa).count()
            )
            
            # Eliminar en orden: primero detalles, luego maestros
            db.query(DetalleAsiento).delete()
            db.query(Asiento).delete()
            db.query(MovimientoInventario).delete()
            db.query(Producto).delete()
            db.query(Cuenta).delete()
            db.query(Empresa).delete()
            
            # Guardar cambios
            db.commit()
        
        console.print("\n" + "="*60)
        console.print("[bold green]✔ DATOS LIMPIADOS EXITOSAMENTE[/bold green]")
        console.print("="*60)
        console.print(f"[cyan]Se eliminaron {total_registros} registros en total[/cyan]\n")
        console.print("[yellow]💡 Pasos sugeridos para nueva demostración:[/yellow]")
        console.print("   1️⃣  Configurar empresa (Opción 0)")
        console.print("   2️⃣  Importar plan de cuentas (Opción 2)")
        console.print("   3️⃣  ¡Listo para registrar asientos!")
        
    except Exception as e:
        db.rollback()
        console.print(f"\n[bold red]✗ ERROR: {str(e)}[/bold red]")
        console.print("[yellow]No se pudieron limpiar los datos[/yellow]")
    finally:
        db.close()
    
    pausar()

def opcion_importar_plan():
    """Importar plan de cuentas desde Excel"""
    console.clear()
    console.print(Panel("[bold cyan]IMPORTAR PLAN DE CUENTAS[/bold cyan]"))
    
    ruta = Prompt.ask("Ruta del archivo Excel", default="datos/plan_cuentas.xlsx")
    
    if not os.path.exists(ruta):
        console.print(f"[bold red]✗ El archivo '{ruta}' no existe[/bold red]")
        console.print(f"[yellow]Verifique que el archivo exista en: {os.path.abspath(ruta)}[/yellow]")
        pausar()
        return
    
    db = next(get_db())
    
    with console.status("[bold blue]Importando plan de cuentas...[/bold blue]"):
        exito, msg = importar_plan_cuentas_desde_excel(ruta, db)
    
    if exito:
        console.print(f"[bold green]✔ {msg}[/bold green]")
    else:
        console.print(f"[bold red]✗ {msg}[/bold red]")
    
    pausar()

def opcion_generar_reporte_simple(db, generador_func, nombre_archivo, titulo):
    """Generar reporte PDF simple"""
    with console.status(f"[bold blue]Generando {titulo}...[/bold blue]"):
        if generador_func(db):
            console.print(f"[bold green]✔ {titulo} generado: {nombre_archivo}[/bold green]")
            try: 
                os.startfile(nombre_archivo)
            except: 
                console.print(f"[yellow]Abra manualmente: {nombre_archivo}[/yellow]")
        else:
            console.print(f"[bold red]✗ Error al generar {titulo}[/bold red]")
    pausar()

def opcion_estados_financieros():
    """Generar Estados Financieros"""
    console.clear()
    console.print(Panel("[bold cyan]ESTADOS FINANCIEROS[/bold cyan]"))
    
    db = next(get_db())
    
    with console.status("[bold blue]Generando Estados Financieros...[/bold blue]"):
        utilidad = generar_estado_resultados(db)
        console.print(f"[green]✔ Estado de Resultados generado (Utilidad: ${utilidad:,.2f})[/green]")
        
        if generar_balance_general(db, utilidad):
            console.print("[green]✔ Balance General generado correctamente[/green]")
            try:
                os.startfile("estado_resultados.pdf")
                os.startfile("balance_general.pdf")
            except: 
                console.print("[yellow]Abra los archivos manualmente[/yellow]")
        else:
            console.print("[red]✗ Error generando Balance General[/red]")
    
    pausar()

# ============================================
# MENÚ PRINCIPAL
# ============================================
def mostrar_menu():
    """Muestra el menú principal del sistema"""
    console.clear()
    
    # Obtener información de la empresa
    db = next(get_db())
    empresa = obtener_empresa(db)
    
    # Título dinámico según configuración
    if empresa:
        titulo = f"SISTEMA CONTABLE - {empresa.nombre_comercial or empresa.nombre}"
        subtitulo = f"RUC: {empresa.ruc} | v2.1"
    else:
        titulo = "SISTEMA CONTABLE PROFESIONAL CLI"
        subtitulo = "v2.1 - Listo para Configurar"
    
    # Panel principal
    console.print(Panel.fit(
        f"[bold cyan]{titulo}[/bold cyan]",
        subtitle=subtitulo,
        border_style="cyan"
    ))
    
    # Advertencia si no hay empresa configurada
    if not empresa:
        console.print(
            "[bold yellow]⚠ Configure su empresa primero (Opción 0)[/bold yellow]\n"
        )
    
    # Tabla de opciones organizada
    tabla = Table(show_header=False, box=None, padding=(0, 2))
    tabla.add_column("Opción", style="bold cyan", width=8)
    tabla.add_column("Descripción", style="white")
    
    # Configuración
    tabla.add_row("", "[bold magenta]═══ CONFIGURACIÓN ═══[/bold magenta]")
    tabla.add_row("[0]", "⚙️  Configurar Datos de Empresa")
    tabla.add_row("[1]", "🧹 Limpiar Datos (Reset para Demo)")
    tabla.add_row("[2]", "📥 Importar Plan de Cuentas (Excel)")
    
    # Operaciones
    tabla.add_row("", "\n[bold green]═══ OPERACIONES ═══[/bold green]")
    tabla.add_row("[3]", "📝 Registrar Asiento Contable")
    
    # Reportes
    tabla.add_row("", "\n[bold yellow]═══ REPORTES ═══[/bold yellow]")
    tabla.add_row("[4]", "📄 Balance de Situacion Inicial")
    tabla.add_row("[5]", "📄 Libro Diario")
    tabla.add_row("[6]", "📒 Libro Mayor")
    tabla.add_row("[7]", "⚖️  Balance de Comprobación")
    tabla.add_row("[8]", "💰 Estados Financieros")
    
    # Módulos
    tabla.add_row("", "\n[bold blue]═══ MÓDULOS ═══[/bold blue]")
    tabla.add_row("[9]", "📦 Inventarios (FIFO/PMP)")
    
    # Salir
    tabla.add_row("", "")
    tabla.add_row("[10]", "❌ Salir")
    
    console.print(tabla)

# ============================================
# FUNCIÓN PRINCIPAL
# ============================================
def main():
    """Función principal del sistema contable"""
    try:
        # Inicializar base de datos
        with console.status("[bold blue]Inicializando sistema...[/bold blue]"):
            init_db()
        
        # Bucle principal
        while True:
            try:
                mostrar_menu()
                
                opcion = Prompt.ask(
                    "\n[bold yellow]Seleccione una opción[/bold yellow]",
                    choices=[str(i) for i in range(0, 11)],
                    show_choices=False
                )
                
                # Ejecutar opción seleccionada
                if opcion == OpcionMenu.CONFIGURAR_EMPRESA:
                    vista_configurar_empresa()
                
                elif opcion == OpcionMenu.LIMPIAR_DATOS:
                    opcion_limpiar_datos()
                
                elif opcion == OpcionMenu.IMPORTAR_PLAN:
                    opcion_importar_plan()
                
                elif opcion == OpcionMenu.REGISTRAR_ASIENTO:
                    vista_registrar_asiento()
                
                elif opcion == OpcionMenu.BALANCE_SITUACION:
                    db = next(get_db())
                    opcion_generar_reporte_simple(
                        db, generar_balance_situacion_inicial, 
                        "balance_situacion_inicial.pdf", "Balance de Situación Inicial"
                    )
                    
                elif opcion == OpcionMenu.LIBRO_DIARIO:
                    db = next(get_db())
                    opcion_generar_reporte_simple(
                        db, generar_pdf_libro_diario, 
                        "libro_diario.pdf", "Libro Diario"
                    )
                
                elif opcion == OpcionMenu.LIBRO_MAYOR:
                    db = next(get_db())
                    opcion_generar_reporte_simple(
                        db, generar_pdf_libro_mayor, 
                        "libro_mayor.pdf", "Libro Mayor"
                    )
                
                elif opcion == OpcionMenu.BALANCE_COMPROBACION:
                    db = next(get_db())
                    opcion_generar_reporte_simple(
                        db, generar_balance_comprobacion, 
                        "balance_comprobacion.pdf", "Balance de Comprobación"
                    )
                
                elif opcion == OpcionMenu.ESTADOS_FINANCIEROS:
                    opcion_estados_financieros()
                
                elif opcion == OpcionMenu.INVENTARIOS:
                    menu_inventario()
                
                elif opcion == OpcionMenu.SALIR:
                    console.clear()
                    console.print(Panel.fit(
                        "[bold cyan]¡Gracias por usar el Sistema Contable![/bold cyan]\n"
                        "[white]Desarrollado con ❤️ en Python[/white]",
                        border_style="cyan"
                    ))
                    sys.exit(0)
            
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠ Operación cancelada por el usuario[/yellow]")
                if confirmar_accion("¿Desea salir del sistema?"):
                    sys.exit(0)
                continue
            
            except Exception as e:
                console.print(f"\n[bold red]✗ ERROR INESPERADO: {str(e)}[/bold red]")
                console.print("[yellow]El sistema intentará continuar...[/yellow]")
                pausar()
                continue
    
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Sistema cerrado por el usuario[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]ERROR CRÍTICO: {str(e)}[/bold red]")
        sys.exit(1)
    finally:
        # Limpiar recursos
        try:
            close_engine()
        except:
            pass

# ============================================
# PUNTO DE ENTRADA
# ============================================
if __name__ == "__main__":
    main()
