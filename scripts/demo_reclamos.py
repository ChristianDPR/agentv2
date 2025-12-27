#!/usr/bin/env python3
"""
Demo interactivo del Agente de Reclamos

Permite probar la clasificación, routing y auditoría de reclamos en tiempo real.
Incluye modo demo con casos del golden set.
"""

import sys
import os
import asyncio
from pathlib import Path
import json
from datetime import datetime

# Agregar el directorio raíz al PYTHONPATH
WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Cargar variables de entorno desde .env
from dotenv import load_dotenv
load_dotenv(WORKSPACE_ROOT / ".env", override=True)

from src.framework.model_provider import VertexAIProvider
from src.tools.classifier_tool import ClassifierTool
from src.tools.router_tool import RouterTool
from src.tools.audit_tool import AuditTool
from src.tools.finish_tool import FinishTool
from src.agents.reclamos.agent import AgenteReclamos
from src.agents.reclamos.agent_fc import AgenteReclamosFunctionCalling
from src.agents.reclamos.config import CATEGORIES, SLA_RULES


class Colors:
    """ANSI colors para output colorido"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[35m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Imprime header colorido"""
    print(f"\n{Colors.BOLD}{Colors.MAGENTA}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.MAGENTA}{'=' * 70}{Colors.ENDC}\n")


def print_section(text):
    """Imprime sección"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{text}{Colors.ENDC}")
    print(f"{Colors.BLUE}{'-' * 70}{Colors.ENDC}")


def print_success(text):
    """Imprime mensaje de éxito"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Imprime mensaje de error"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")


def print_warning(text):
    """Imprime advertencia"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")


def print_info(text):
    """Imprime información"""
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")


def get_priority_color(priority: str) -> str:
    """Retorna color según prioridad"""
    colors = {
        "critical": Colors.RED,
        "high": Colors.YELLOW,
        "normal": Colors.CYAN,
        "low": Colors.GREEN
    }
    return colors.get(priority, Colors.ENDC)


def get_priority_emoji(priority: str) -> str:
    """Retorna emoji según prioridad"""
    emojis = {
        "critical": "🔴",
        "high": "🟠",
        "normal": "🟡",
        "low": "🟢"
    }
    return emojis.get(priority, "⚪")


async def initialize_components(use_function_calling: bool = False):
    """Inicializa todos los componentes necesarios"""
    mode_name = "Function Calling" if use_function_calling else "Flujo Fijo"
    print_section(f"Inicializando componentes (Modo: {mode_name})...")

    # Verificar env vars
    required_vars = ["VERTEX_AI_PROJECT"]
    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print_error(f"Faltan variables de entorno: {', '.join(missing)}")
        print_info("Asegúrate de tener configurado el archivo .env")
        return None

    try:
        # Model Provider
        model_provider = VertexAIProvider(
            project_id=os.getenv("VERTEX_AI_PROJECT"),
            location=os.getenv("VERTEX_AI_LOCATION", "us-central1"),
            model_name=os.getenv("DEFAULT_LLM_MODEL", "gemini-2.0-flash")
        )
        print_success(f"ModelProvider inicializado ({model_provider.model_name})")

        # Tools
        classifier_tool = ClassifierTool(model_provider=model_provider)
        print_success("ClassifierTool inicializada")

        router_tool = RouterTool()
        print_success("RouterTool inicializada")

        audit_tool = AuditTool(log_to_file=False)
        print_success("AuditTool inicializada")

        if use_function_calling:
            # Agente con Function Calling
            finish_tool = FinishTool()
            print_success("FinishTool inicializada")

            agente = AgenteReclamosFunctionCalling(
                model_provider=model_provider,
                classifier_tool=classifier_tool,
                router_tool=router_tool,
                audit_tool=audit_tool,
                finish_tool=finish_tool
            )
            print_success("AgenteReclamosFunctionCalling creado")
            print_info("El LLM decide qué tools usar y en qué orden")
        else:
            # Agente con Flujo Fijo
            agente = AgenteReclamos(
                model_provider=model_provider,
                classifier_tool=classifier_tool,
                router_tool=router_tool,
                audit_tool=audit_tool
            )
            print_success("AgenteReclamos creado")
            print_info("Flujo fijo: clasificar → rutear → auditar")

        return {
            "agente": agente,
            "model_provider": model_provider,
            "use_function_calling": use_function_calling
        }

    except Exception as e:
        print_error(f"Error al inicializar: {e}")
        import traceback
        traceback.print_exc()
        return None


def display_result(result, show_details=True):
    """Muestra el resultado de forma formateada"""

    # Mensaje principal
    print(f"\n{Colors.BOLD}📝 RESPUESTA AL CLIENTE{Colors.ENDC}")
    print("-" * 70)
    print(f"{Colors.CYAN}{result.content}{Colors.ENDC}")

    if not show_details:
        return

    metadata = result.metadata

    # Clasificación
    if "classification" in metadata:
        cls = metadata["classification"]
        priority = cls.get("priority", "normal")
        priority_color = get_priority_color(priority)
        priority_emoji = get_priority_emoji(priority)

        print(f"\n{Colors.BOLD}🏷️  CLASIFICACIÓN{Colors.ENDC}")
        print("-" * 70)
        print(f"  Categoría:   {Colors.BOLD}{cls.get('category', 'N/A').upper()}{Colors.ENDC}")
        print(f"  Prioridad:   {priority_color}{priority_emoji} {priority.upper()}{Colors.ENDC}")
        print(f"  SLA:         {cls.get('sla_hours', 'N/A')} horas")
        print(f"  Confianza:   {cls.get('confidence', 0):.0%}")

        if cls.get("reasoning"):
            print(f"\n  {Colors.YELLOW}Razonamiento:{Colors.ENDC}")
            print(f"  {cls['reasoning']}")

        if cls.get("keywords_detected"):
            print(f"\n  {Colors.YELLOW}Keywords detectadas:{Colors.ENDC}")
            print(f"  {', '.join(cls['keywords_detected'])}")

    # Routing
    if "routing" in metadata:
        rt = metadata["routing"]

        print(f"\n{Colors.BOLD}📍 ROUTING{Colors.ENDC}")
        print("-" * 70)
        print(f"  Departamento: {Colors.BOLD}{rt.get('department', 'N/A').replace('_', ' ').title()}{Colors.ENDC}")
        print(f"  Cola:         {rt.get('queue', 'N/A')}")

        if rt.get("escalated"):
            print(f"  {Colors.RED}⚡ ESCALADO: {rt.get('escalation_reason', 'Sí')}{Colors.ENDC}")

        if rt.get("applied_rules"):
            print(f"\n  {Colors.YELLOW}Reglas aplicadas:{Colors.ENDC}")
            for rule in rt["applied_rules"]:
                print(f"    • {rule}")

    # Auditoría
    if "audit_log" in metadata:
        audit = metadata["audit_log"]

        print(f"\n{Colors.BOLD}📋 AUDITORÍA{Colors.ENDC}")
        print("-" * 70)
        print(f"  Trace ID:    {audit.get('trace_id', 'N/A')}")
        print(f"  Timestamp:   {audit.get('timestamp', 'N/A')}")
        print(f"  Claim ID:    {metadata.get('claim_id', 'N/A')}")

    # Observaciones (para mode function_calling)
    if metadata.get("mode") == "function_calling" and "observations" in metadata:
        observations = metadata["observations"]
        print(f"\n{Colors.BOLD}🔄 PASOS DEL AGENTE (Function Calling){Colors.ENDC}")
        print("-" * 70)
        print(f"{Colors.YELLOW}El LLM decidió usar las tools en este orden:{Colors.ENDC}")
        for obs in observations:
            step = obs.get("step", "?")
            tool = obs.get("tool", "unknown")
            args = obs.get("input", {})

            # Formato compacto de argumentos
            if isinstance(args, dict):
                args_str = ", ".join(f"{k}={v}" for k, v in list(args.items())[:2])
            else:
                args_str = str(args)[:50]

            print(f"\n  {Colors.CYAN}Paso {step}:{Colors.ENDC} {Colors.BOLD}{tool}{Colors.ENDC}")
            print(f"    Args: {args_str}")

            # Resumen del resultado
            output = obs.get("output", {})
            if tool == "classify_claim":
                cat = output.get("category", "?")
                pri = output.get("priority", "?")
                print(f"    → Categoría: {cat}, Prioridad: {pri}")
            elif tool == "route_claim":
                dept = output.get("department", "?")
                queue = output.get("queue", "?")
                print(f"    → Departamento: {dept}, Cola: {queue}")
            elif tool == "audit_log":
                trace = output.get("trace_id", "?")
                print(f"    → Trace ID: {trace}")
            elif tool == "finish":
                print(f"    → Finalizando procesamiento")

        # Advertencia si no siguió el orden esperado
        tool_order = [obs.get("tool") for obs in observations]
        expected_order = ["classify_claim", "route_claim", "audit_log", "finish"]
        if tool_order != expected_order[:len(tool_order)]:
            print(f"\n{Colors.YELLOW}  ⚠ NOTA: El LLM usó un orden diferente al flujo fijo{Colors.ENDC}")

        # Mostrar iteraciones
        iterations = metadata.get("iterations", len(observations))
        print(f"\n  Total iteraciones: {iterations}")

    # Tiempo de procesamiento
    if "processing_time_ms" in metadata:
        time_ms = metadata["processing_time_ms"]
        print(f"\n{Colors.YELLOW}⏱️  Tiempo de procesamiento: {time_ms}ms ({time_ms/1000:.2f}s){Colors.ENDC}")


async def process_claim(agente, claim_text: str, channel: str = "web", claim_id: str = None):
    """Procesa un reclamo y muestra el resultado"""

    print_section(f"Procesando reclamo...")
    print(f"\n{Colors.BOLD}Reclamo:{Colors.ENDC}")
    print(f'"{claim_text}"')
    print(f"\n{Colors.YELLOW}Canal: {channel}{Colors.ENDC}")

    import time
    start = time.time()

    context = {
        "channel": channel,
        "claim_id": claim_id
    }

    result = await agente.run(query=claim_text, context=context)

    elapsed = time.time() - start

    display_result(result)

    return result


async def interactive_mode(components):
    """Modo interactivo de consultas"""
    use_fc = components.get("use_function_calling", False)
    arch_name = "Function Calling" if use_fc else "Flujo Fijo"
    print_header(f"MODO INTERACTIVO - AGENTE DE RECLAMOS AFP ({arch_name})")

    print("Escribe un reclamo y el agente lo clasificará, derivará y registrará.\n")
    print("Comandos disponibles:")
    print("  - Escribe tu reclamo y presiona Enter")
    print("  - 'canal <nombre>' - Cambiar canal (app, web, presencial, call_center)")
    print("  - 'categorias' - Ver categorías disponibles")
    print("  - 'sla' - Ver reglas de SLA")
    print("  - 'ejemplo' - Ver un ejemplo de reclamo")
    print("  - 'quit' - Salir")
    print()

    current_channel = "web"
    agente = components["agente"]

    while True:
        try:
            # Mostrar canal actual
            prompt = f"{Colors.BOLD}{Colors.GREEN}[{current_channel}] Tu reclamo > {Colors.ENDC}"
            claim_text = input(f"\n{prompt}").strip()

            if not claim_text:
                continue

            # Comandos especiales
            if claim_text.lower() in ['quit', 'exit', 'salir']:
                print_warning("¡Hasta luego!")
                break

            elif claim_text.lower().startswith('canal '):
                new_channel = claim_text.split(' ', 1)[1].lower()
                valid_channels = ['app', 'web', 'presencial', 'call_center', 'email']
                if new_channel in valid_channels:
                    current_channel = new_channel
                    print_success(f"Canal cambiado a: {current_channel}")
                else:
                    print_error(f"Canal inválido. Opciones: {', '.join(valid_channels)}")
                continue

            elif claim_text.lower() == 'categorias':
                print_section("Categorías de Reclamos")
                for key, cat in CATEGORIES.items():
                    print(f"\n{Colors.BOLD}{key.upper()}{Colors.ENDC}: {cat['description']}")
                    print(f"  Keywords: {', '.join(cat['keywords'][:5])}...")
                continue

            elif claim_text.lower() == 'sla':
                print_section("Reglas de SLA")
                for priority, config in SLA_RULES.items():
                    emoji = get_priority_emoji(priority)
                    color = get_priority_color(priority)
                    print(f"\n{emoji} {color}{priority.upper()}{Colors.ENDC}")
                    print(f"   Tiempo: {config['hours']} horas")
                    print(f"   {config['description']}")
                continue

            elif claim_text.lower() == 'ejemplo':
                ejemplos = [
                    "Detecté un cargo de S/500 que no reconozco en mi cuenta.",
                    "No he recibido mi estado de cuenta de los últimos 2 meses.",
                    "Quiero demandar a la AFP por mal manejo de mis fondos.",
                    "La aplicación no me deja ingresar con mi contraseña.",
                    "Quiero saber los requisitos para jubilarme anticipadamente."
                ]
                print_section("Ejemplos de Reclamos")
                for i, ej in enumerate(ejemplos, 1):
                    print(f"{i}. {ej}")
                continue

            # Procesar el reclamo
            await process_claim(
                agente=agente,
                claim_text=claim_text,
                channel=current_channel
            )

        except KeyboardInterrupt:
            print_warning("\n¡Hasta luego!")
            break
        except Exception as e:
            print_error(f"Error: {e}")
            import traceback
            traceback.print_exc()


async def demo_mode(components):
    """Modo demo con casos del golden set"""
    use_fc = components.get("use_function_calling", False)
    arch_name = "Function Calling" if use_fc else "Flujo Fijo"
    print_header(f"MODO DEMO - CASOS DE PRUEBA ({arch_name})")

    agente = components["agente"]

    # Cargar golden set
    golden_set_path = WORKSPACE_ROOT / "data" / "golden_sets" / "reclamos.json"

    try:
        with open(golden_set_path, 'r', encoding='utf-8') as f:
            golden_set = json.load(f)
    except FileNotFoundError:
        print_error(f"No se encontró el golden set en: {golden_set_path}")
        return

    cases = golden_set.get("cases", [])[:5]  # Solo primeros 5 para demo

    print(f"Ejecutando {len(cases)} casos de prueba del golden set...\n")

    results = []

    for i, case in enumerate(cases, 1):
        print(f"\n{Colors.BOLD}{'=' * 70}{Colors.ENDC}")
        print(f"{Colors.BOLD}CASO {i}/{len(cases)}: {case['description']}{Colors.ENDC}")
        print(f"{Colors.BOLD}{'=' * 70}{Colors.ENDC}")

        # Procesar
        result = await process_claim(
            agente=agente,
            claim_text=case["input"]["text"],
            channel=case["input"].get("channel", "web"),
            claim_id=case["id"]
        )

        # Comparar con esperado
        expected = case["expected"]
        actual_cls = result.metadata.get("classification", {})
        actual_rt = result.metadata.get("routing", {})

        print(f"\n{Colors.BOLD}📊 EVALUACIÓN vs ESPERADO{Colors.ENDC}")
        print("-" * 70)

        # Categoría
        cat_match = actual_cls.get("category") == expected["category"]
        cat_icon = "✅" if cat_match else "❌"
        print(f"  Categoría:  {cat_icon} {actual_cls.get('category', 'N/A')} (esperado: {expected['category']})")

        # Prioridad
        pri_match = actual_cls.get("priority") == expected["priority"]
        pri_icon = "✅" if pri_match else "❌"
        print(f"  Prioridad:  {pri_icon} {actual_cls.get('priority', 'N/A')} (esperado: {expected['priority']})")

        # Departamento
        dept_match = actual_rt.get("department") == expected["department"]
        dept_icon = "✅" if dept_match else "❌"
        print(f"  Depto:      {dept_icon} {actual_rt.get('department', 'N/A')} (esperado: {expected['department']})")

        # Escalamiento
        esc_match = actual_rt.get("escalated", False) == expected.get("escalated", False)
        esc_icon = "✅" if esc_match else "❌"
        print(f"  Escalado:   {esc_icon} {actual_rt.get('escalated', False)} (esperado: {expected.get('escalated', False)})")

        # Resultado
        all_match = cat_match and pri_match and dept_match and esc_match
        results.append(all_match)

        if all_match:
            print(f"\n{Colors.GREEN}✅ CASO PASADO{Colors.ENDC}")
        else:
            print(f"\n{Colors.RED}❌ CASO FALLIDO{Colors.ENDC}")

        if i < len(cases):
            input(f"\n{Colors.YELLOW}Presiona Enter para continuar...{Colors.ENDC}")

    # Resumen final
    print_header("RESUMEN DE EVALUACIÓN")

    passed = sum(results)
    total = len(results)
    accuracy = passed / total if total > 0 else 0

    print(f"Casos pasados: {passed}/{total}")
    print(f"Accuracy: {accuracy:.0%}")

    if accuracy >= 0.85:
        print(f"\n{Colors.GREEN}✅ CRITERIO DE ACEPTACIÓN CUMPLIDO (≥85%){Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}❌ CRITERIO DE ACEPTACIÓN NO CUMPLIDO (<85%){Colors.ENDC}")


async def batch_mode(components):
    """Modo batch - procesa todos los casos del golden set"""
    use_fc = components.get("use_function_calling", False)
    arch_name = "Function Calling" if use_fc else "Flujo Fijo"
    print_header(f"MODO BATCH - EVALUACIÓN COMPLETA ({arch_name})")

    agente = components["agente"]

    # Cargar golden set
    golden_set_path = WORKSPACE_ROOT / "data" / "golden_sets" / "reclamos.json"

    try:
        with open(golden_set_path, 'r', encoding='utf-8') as f:
            golden_set = json.load(f)
    except FileNotFoundError:
        print_error(f"No se encontró el golden set en: {golden_set_path}")
        return

    cases = golden_set.get("cases", [])
    print(f"Procesando {len(cases)} casos...\n")

    results = {
        "total": len(cases),
        "passed": 0,
        "failed": 0,
        "category_accuracy": 0,
        "priority_accuracy": 0,
        "routing_accuracy": 0,
        "details": []
    }

    category_correct = 0
    priority_correct = 0
    routing_correct = 0

    for i, case in enumerate(cases, 1):
        print(f"Procesando caso {i}/{len(cases)}: {case['id']}...", end=" ")

        try:
            result = await agente.run(
                query=case["input"]["text"],
                context={
                    "channel": case["input"].get("channel", "web"),
                    "claim_id": case["id"]
                }
            )

            expected = case["expected"]
            actual_cls = result.metadata.get("classification", {})
            actual_rt = result.metadata.get("routing", {})

            # Evaluar
            cat_match = actual_cls.get("category") == expected["category"]
            pri_match = actual_cls.get("priority") == expected["priority"]
            dept_match = actual_rt.get("department") == expected["department"]

            if cat_match:
                category_correct += 1
            if pri_match:
                priority_correct += 1
            if dept_match:
                routing_correct += 1

            all_match = cat_match and pri_match and dept_match

            if all_match:
                results["passed"] += 1
                print(f"{Colors.GREEN}✅{Colors.ENDC}")
            else:
                results["failed"] += 1
                print(f"{Colors.RED}❌{Colors.ENDC}")

            results["details"].append({
                "case_id": case["id"],
                "passed": all_match,
                "expected": expected,
                "actual": {
                    "category": actual_cls.get("category"),
                    "priority": actual_cls.get("priority"),
                    "department": actual_rt.get("department")
                }
            })

        except Exception as e:
            print(f"{Colors.RED}ERROR: {e}{Colors.ENDC}")
            results["failed"] += 1

    # Calcular métricas
    total = results["total"]
    results["category_accuracy"] = category_correct / total if total > 0 else 0
    results["priority_accuracy"] = priority_correct / total if total > 0 else 0
    results["routing_accuracy"] = routing_correct / total if total > 0 else 0
    overall_accuracy = results["passed"] / total if total > 0 else 0

    # Mostrar resultados
    print_header("RESULTADOS DE EVALUACIÓN")

    print(f"Total casos:        {total}")
    print(f"Pasados:            {results['passed']}")
    print(f"Fallidos:           {results['failed']}")
    print()
    print(f"Accuracy categoría: {results['category_accuracy']:.1%}")
    print(f"Accuracy prioridad: {results['priority_accuracy']:.1%}")
    print(f"Accuracy routing:   {results['routing_accuracy']:.1%}")
    print(f"Accuracy general:   {overall_accuracy:.1%}")

    # Criterios de aceptación
    print_section("Criterios de Aceptación")

    criteria = golden_set.get("acceptance_criteria", {})

    cat_ok = results["category_accuracy"] >= criteria.get("category_accuracy", 0.85)
    pri_ok = results["priority_accuracy"] >= criteria.get("priority_accuracy", 0.80)
    rt_ok = results["routing_accuracy"] >= criteria.get("routing_accuracy", 1.0)

    print(f"  Categoría ≥{criteria.get('category_accuracy', 0.85):.0%}: {'✅' if cat_ok else '❌'}")
    print(f"  Prioridad ≥{criteria.get('priority_accuracy', 0.80):.0%}: {'✅' if pri_ok else '❌'}")
    print(f"  Routing ≥{criteria.get('routing_accuracy', 1.0):.0%}: {'✅' if rt_ok else '❌'}")

    if cat_ok and pri_ok and rt_ok:
        print(f"\n{Colors.GREEN}✅ TODOS LOS CRITERIOS CUMPLIDOS{Colors.ENDC}")
    else:
        print(f"\n{Colors.RED}❌ ALGUNOS CRITERIOS NO CUMPLIDOS{Colors.ENDC}")

    # Mostrar casos fallidos
    failed_cases = [d for d in results["details"] if not d["passed"]]
    if failed_cases:
        print_section("Casos Fallidos")
        for case in failed_cases[:5]:  # Mostrar máximo 5
            print(f"\n{case['case_id']}:")
            print(f"  Esperado:  {case['expected']}")
            print(f"  Actual:    {case['actual']}")


async def main():
    """Main function"""
    print_header("AGENTE DE RECLAMOS AFP - DEMO")
    print(f"{Colors.CYAN}Prototipo 2 del curso COE-IA-TRAINING{Colors.ENDC}")

    # Selección de arquitectura del agente
    print(f"\n{Colors.BOLD}Selecciona arquitectura del agente:{Colors.ENDC}")
    print("  1. Flujo Fijo (código decide: clasificar → rutear → auditar)")
    print("  2. Function Calling (LLM decide qué tools usar y en qué orden)")
    print()
    print(f"{Colors.YELLOW}  PEDAGOGÍA: Compara ambos enfoques - ¿cuál es mejor para compliance?{Colors.ENDC}")
    print()

    arch_choice = input(f"{Colors.GREEN}Arquitectura (1/2): {Colors.ENDC}").strip()

    use_function_calling = arch_choice == "2"

    # Inicializar componentes con la arquitectura elegida
    components = await initialize_components(use_function_calling=use_function_calling)
    if not components:
        return 1

    # Menú de modo
    print(f"\n{Colors.BOLD}Selecciona modo:{Colors.ENDC}")
    print("  1. Interactivo (escribe tus reclamos)")
    print("  2. Demo (5 casos del golden set)")
    print("  3. Batch (evaluar todo el golden set)")
    print()

    choice = input(f"{Colors.GREEN}Opción (1/2/3): {Colors.ENDC}").strip()

    try:
        if choice == "1":
            await interactive_mode(components)
        elif choice == "2":
            await demo_mode(components)
            # Después del demo, ofrecer modo interactivo
            print()
            cont = input(f"{Colors.GREEN}¿Continuar en modo interactivo? (s/n): {Colors.ENDC}").strip()
            if cont.lower() in ['s', 'si', 'y', 'yes']:
                await interactive_mode(components)
        elif choice == "3":
            await batch_mode(components)
        else:
            print_error("Opción inválida")

    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()

    print_success("\n¡Demo finalizado!")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
