import sys
import os
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
from rich.tree import Tree  # Importación necesaria para el árbol
from rich import print as rprint
from src.base_datos.db import init_db, get_db, close_engine
# Importaciones locales
from src.base_datos.db import init_db, get_db
from src.servicios.contabilidad import importar_plan_cuentas_desde_excel, registrar_asiento
from src.modelos.entidades import Cuenta
from src.reportes.generador import (
    generar_pdf_libro_diario, 
    generar_pdf_libro_mayor, 
    generar_balance_comprobacion,
    generar_estado_resultados, 
    generar_balance_general
)
from src.servicios.inventario import crear_producto, registrar_compra, registrar_venta
from src.reportes.kardex_pdf import generar_reporte_fifo, generar_reporte_pmp
from src.servicios.empresa import configurar_empresa, obtener_empresa, empresa_configurada
console = Console()


# Crear nueva función para la vista de empresa
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
    
    input("\nPresione Enter para continuar...")

# --- NUEVA FUNCIÓN: SELECTOR VISUAL DE CUENTAS ---
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
            
            # Crear árbol visual
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
                if seleccion == 0: return None
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

# --- MODIFICADO: VISTA REGISTRAR ASIENTO CON SELECTOR ---
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
        table.add_column("Nombre") # Agregamos nombre para mejor visualización
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
                input("Enter...")
                continue
            if len(movimientos) == 0:
                console.print("[bold red]El asiento está vacío.[/bold red]")
                input("Enter...")
                continue
                
            fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            
            # Pasamos solo los datos necesarios al servicio (limpiamos el campo extra 'nombre_cuenta')
            movimientos_data = [{'cuenta_codigo': m['cuenta_codigo'], 'debe': m['debe'], 'haber': m['haber']} for m in movimientos]
            
            exito, msg = registrar_asiento(db, fecha_obj, descripcion, movimientos_data)
            if exito:
                console.print(f"[bold green]{msg}[/bold green]")
                input("Presione Enter para volver al menú...")
                break
            else:
                console.print(f"[bold red]{msg}[/bold red]")
                input("Enter...")
            continue

        # --- AQUÍ ESTÁ EL CAMBIO: USO DEL SELECTOR ---
        if accion == "a":
            codigo_seleccionado = seleccionar_cuenta_interactiva(db)
            
            if codigo_seleccionado:
                # Buscamos el nombre para mostrarlo bonito en la tabla temporal
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
                    "nombre_cuenta": cuenta_obj.nombre, # Guardamos nombre solo para visualización
                    "debe": debe,
                    "haber": haber
                })

# --- FUNCIÓN DE SUBMENÚ INVENTARIO ---
def menu_inventario():
    while True:
        console.clear()
        console.print(Panel("[bold magenta]MÓDULO DE INVENTARIOS Y KARDEX (SISTEMA HÍBRIDO)[/bold magenta]"))
        console.print("[1] 📦 Crear Producto Nuevo (Neutro)")
        console.print("[2] 📥 Registrar COMPRA (Entrada)")
        console.print("[3] 📤 Registrar VENTA (Salida)")
        console.print("[4] 📄 Reportes KARDEX (PDF)")
        console.print("[5] 🔙 Volver al Menú Principal")
        
        op = Prompt.ask("Seleccione", choices=["1", "2", "3", "4", "5"])
        
        db = next(get_db()) # Obtener sesión de base de datos
        
        if op == "1":
            # Eliminamos la pregunta del método para que el producto sea neutro
            cod = Prompt.ask("Código Producto")
            nom = Prompt.ask("Nombre")
            try:
                crear_producto(db, cod, nom) # Llamada simplificada
                console.print(f"[green]Producto '{nom}' creado exitosamente.[/green]")
            except:
                console.print("[red]Error: El código ya existe o hubo un problema con la BD.[/red]")
            input("Presione Enter para continuar...")
            
        elif op == "2":
            cod = Prompt.ask("Código Producto")
            cant = int(Prompt.ask("Cantidad"))
            costo = float(Prompt.ask("Costo Unitario"))
            fecha_str = Prompt.ask("Fecha (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            
            ok, msg = registrar_compra(db, cod, fecha, cant, costo)
            console.print(f"[{'green' if ok else 'red'}]{msg}[/]")
            input("Enter...")

        elif op == "3":
            cod = Prompt.ask("Código Producto")
            cant = int(Prompt.ask("Cantidad a Vender"))
            fecha_str = Prompt.ask("Fecha (YYYY-MM-DD)", default=datetime.now().strftime("%Y-%m-%d"))
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            
            ok, msg = registrar_venta(db, cod, fecha, cant)
            console.print(f"[{'green' if ok else 'red'}]{msg}[/]")
            input("Enter...")

        elif op == "4":
            # Submenú para elegir cómo ver el mismo inventario
            console.print("\n[bold cyan]SELECCIONE LÓGICA DE REPORTE:[/bold cyan]")
            console.print("[1] 📊 Ver bajo lógica FIFO (PEPS)")
            console.print("[2] 📈 Ver bajo lógica Promedio Ponderado (PMP)")
            console.print("[0] Cancelar")
            
            sub_op = Prompt.ask("Opción", choices=["1", "2", "0"])
            
            if sub_op == "1":
                if generar_reporte_fifo(db):
                     console.print("[bold green]✔ Reporte generado: reporte_fifo.pdf[/bold green]")
                     try: os.startfile("reporte_fifo.pdf")
                     except: pass
                else:
                    console.print("[yellow]No se pudo generar el reporte FIFO.[/yellow]")
            
            elif sub_op == "2":
                if generar_reporte_pmp(db):
                     console.print("[bold green]✔ Reporte generado: reporte_pmp.pdf[/bold green]")
                     try: os.startfile("reporte_pmp.pdf")
                     except: pass
                else:
                    console.print("[yellow]No se pudo generar el reporte PMP.[/yellow]")
            
            input("Presione Enter para continuar...")

        elif op == "5":
            break

# --- MENÚ PRINCIPAL ---
def mostrar_menu():
    console.clear()
    # Mostrar información de empresa si existe
    db = next(get_db())
    empresa = obtener_empresa(db)
    
    if empresa:
        titulo = f"[bold cyan]SISTEMA CONTABLE - {empresa.nombre_comercial or empresa.nombre}[/bold cyan]"
    else:
        titulo = "[bold cyan]SISTEMA CONTABLE PROFESIONAL CLI[/bold cyan]"
    
    console.print(Panel.fit(titulo, subtitle="v2.1"))
    
    if not empresa:
        console.print("[bold yellow]⚠ ADVERTENCIA: Configure los datos de su empresa primero (opción 0)[/bold yellow]\n")
    console.print("[0] ⚙️  Configurar Datos de Empresa")  # NUEVA OPCIÓN    
    console.print(Panel.fit("[bold cyan]SISTEMA CONTABLE PROFESIONAL CLI[/bold cyan]", subtitle="v2.0"))
    console.print("[1] 📂 Inicializar/Resetear Base de Datos")
    console.print("[2] 📥 Importar Plan de Cuentas (Excel)")
    console.print("[3] 📝 Registrar Asiento (Libro Diario)")
    console.print(Panel("[bold]REPORTES[/bold]", style="white"))
    console.print("[4] 📄 Libro Diario")
    console.print("[5] 📒 Libro Mayor")
    console.print("[6] ⚖  Balance de Comprobación") 
    console.print("[7] 💰 Estados Financieros (Balance y Resultados)")
    console.print("[8] 📦 Módulo de Inventarios")
    console.print("[9] ❌ Salir")

def main():
    init_db()
    while True:
        mostrar_menu()
        opcion = Prompt.ask("\n[bold yellow]Seleccione una opción[/bold yellow]", choices=[str(i) for i in range(0, 10)])
        
        if opcion == "0":  # NUEVA OPCIÓN
            vista_configurar_empresa()

        if opcion == "1":
            if Prompt.ask("¿Resetear BD? SE BORRARÁ TODO", choices=["s", "n"]) == "s":
                
                # 1. Cerramos la conexión primero
                close_engine()
                
                # 2. Ahora sí intentamos borrar
                try:
                    if os.path.exists("datos/contabilidad.sqlite"):
                        os.remove("datos/contabilidad.sqlite")
                    console.print("[yellow]Archivo eliminado.[/yellow]")
                except PermissionError:
                    console.print("[bold red]Error: Windows bloqueó el archivo. Reinicia la terminal e intenta de nuevo.[/bold red]")
                    continue
                except FileNotFoundError:
                    pass
                
                # 3. Volvemos a crear las tablas limpias
                init_db()
                console.print("[bold green]✔ Base de datos reseteada correctamente (Sistema en cero).[/bold green]")
                input("Presione Enter...")
        elif opcion == "2":
            ruta = Prompt.ask("Ruta Excel", default="datos/plan_cuentas.xlsx")
            db = next(get_db())
            exito, msg = importar_plan_cuentas_desde_excel(ruta, db)
            console.print(f"[green]{msg}[/green]" if exito else f"[red]{msg}[/red]")
            input("Enter...")
        elif opcion == "3":
            vista_registrar_asiento()
        elif opcion == "4":
            db = next(get_db())
            with console.status("[bold blue]Generando PDF...[/bold blue]"):
                if generar_pdf_libro_diario(db):
                    console.print(f"[bold green]✔ Reporte generado exitosamente: libro_diario.pdf[/bold green]")
                    try: os.startfile("libro_diario.pdf")
                    except: pass
                else:
                    console.print("[bold red]Error al generar el reporte.[/bold red]")
            input("Presione Enter...")

        elif opcion == "5":
            db = next(get_db())
            with console.status("[bold blue]Mayorizando cuentas...[/bold blue]"):
                if generar_pdf_libro_mayor(db):
                    console.print(f"[bold green]✔ Reporte generado: libro_mayor.pdf[/bold green]")
                    try: os.startfile("libro_mayor.pdf")
                    except: pass
                else:
                    console.print("[bold yellow]No hay datos o hubo un error.[/bold yellow]")
            input("Presione Enter...")
            
        elif opcion == "6":
            db = next(get_db())
            with console.status("[bold blue]Calculando sumas y saldos...[/bold blue]"):
                if generar_balance_comprobacion(db):
                    console.print(f"[bold green]✔ Reporte generado: balance_comprobacion.pdf[/bold green]")
                    try: os.startfile("balance_comprobacion.pdf")
                    except: pass
                else:
                    console.print("[bold red]Error al generar el reporte.[/bold red]")
            input("Presione Enter...")

        elif opcion == "7":
            db = next(get_db())
            with console.status("[bold blue]Generando Estados Financieros...[/bold blue]"):
                utilidad = generar_estado_resultados(db)
                console.print(f"[green]✔ Estado de Resultados generado (Utilidad: {utilidad:.2f})[/green]")
                
                if generar_balance_general(db, utilidad):
                    console.print(f"[green]✔ Balance General generado correctamente[/green]")
                    try:
                        os.startfile("estado_resultados.pdf")
                        os.startfile("balance_general.pdf")
                    except: pass
                else:
                    console.print("[red]Error generando Balance General[/red]")
            input("Presione Enter...")

        elif opcion == "8":
            menu_inventario()
        elif opcion == "9":
            sys.exit()

if __name__ == "__main__":
    main()