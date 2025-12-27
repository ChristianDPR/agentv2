#!/usr/bin/env python3
"""
Script de Comparación: Agent RAG con y sin Índices

Compara el rendimiento de retrieval usando dos métodos:
1. Sin índices: Lee documentos completos
2. Con índices: Usa filtrado jerárquico

Métricas comparadas:
- Tiempo de respuesta
- Tokens consumidos
- Costo estimado
- Calidad de respuesta

Uso:
    python scripts/compare_agent_rag.py
    python scripts/compare_agent_rag.py --queries 5  # Número de queries a probar
"""

import sys
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any
import json

# Agregar src/ al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rag.agent_retrieval import AgentRetrieval
from src.framework.model_provider import VertexAIProvider


class Colors:
    """Colores ANSI para terminal"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Imprime header con formato"""
    width = 80
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'═' * width}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text.center(width-4)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'═' * width}{Colors.END}\n")


def print_section(title: str):
    """Imprime sección"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}▶ {title}{Colors.END}")
    print(f"{Colors.CYAN}{'─' * (len(title) + 3)}{Colors.END}\n")


def print_comparison_table(results: List[Dict[str, Any]]):
    """Imprime tabla comparativa"""
    print(f"\n{Colors.BOLD}{'Query':<50} {'Método':<15} {'Tiempo':<12} {'Tokens':<12} {'Costo':<10}{Colors.END}")
    print(f"{Colors.CYAN}{'─' * 105}{Colors.END}")

    for result in results:
        query_short = result['query'][:47] + "..." if len(result['query']) > 50 else result['query']

        # Color según método
        method_color = Colors.GREEN if result['method'] == 'Con índices' else Colors.YELLOW

        print(f"{query_short:<50} "
              f"{method_color}{result['method']:<15}{Colors.END} "
              f"{result['time']:.2f}s{' ' * (12 - len(f'{result['time']:.2f}s'))} "
              f"{result['tokens']:,}{' ' * (12 - len(f'{result['tokens']:,}'))} "
              f"${result['cost']:.4f}")


def print_summary(stats: Dict[str, Any]):
    """Imprime resumen de estadísticas"""
    print(f"\n{Colors.BOLD}╔{'═' * 78}╗{Colors.END}")
    print(f"{Colors.BOLD}║{' ' * 30}RESUMEN COMPARATIVO{' ' * 29}║{Colors.END}")
    print(f"{Colors.BOLD}╠{'═' * 78}╣{Colors.END}")

    # Sin índices
    print(f"{Colors.BOLD}║  {Colors.YELLOW}SIN ÍNDICES{Colors.END}{' ' * 67}║")
    print(f"{Colors.BOLD}║{Colors.END}    Tiempo promedio: {stats['without_index']['avg_time']:.2f}s{' ' * (54 - len(f'{stats['without_index']['avg_time']:.2f}s'))}║")
    print(f"{Colors.BOLD}║{Colors.END}    Tokens promedio: {stats['without_index']['avg_tokens']:,}{' ' * (55 - len(f'{stats['without_index']['avg_tokens']:,}'))}║")
    print(f"{Colors.BOLD}║{Colors.END}    Costo promedio: ${stats['without_index']['avg_cost']:.4f}{' ' * (53 - len(f'{stats['without_index']['avg_cost']:.4f}'))}║")
    print(f"{Colors.BOLD}║{' ' * 78}║{Colors.END}")

    # Con índices
    print(f"{Colors.BOLD}║  {Colors.GREEN}CON ÍNDICES{Colors.END}{' ' * 67}║")
    print(f"{Colors.BOLD}║{Colors.END}    Tiempo promedio: {stats['with_index']['avg_time']:.2f}s{' ' * (54 - len(f'{stats['with_index']['avg_time']:.2f}s'))}║")
    print(f"{Colors.BOLD}║{Colors.END}    Tokens promedio: {stats['with_index']['avg_tokens']:,}{' ' * (55 - len(f'{stats['with_index']['avg_tokens']:,}'))}║")
    print(f"{Colors.BOLD}║{Colors.END}    Costo promedio: ${stats['with_index']['avg_cost']:.4f}{' ' * (53 - len(f'{stats['with_index']['avg_cost']:.4f}'))}║")
    print(f"{Colors.BOLD}║{' ' * 78}║{Colors.END}")

    # Mejora
    print(f"{Colors.BOLD}║  {Colors.CYAN}MEJORA{Colors.END}{' ' * 72}║")
    print(f"{Colors.BOLD}║{Colors.END}    Velocidad: {Colors.GREEN}{stats['improvement']['speed']:.1f}x más rápido{Colors.END}{' ' * (47 - len(f'{stats['improvement']['speed']:.1f}x más rápido'))}║")
    print(f"{Colors.BOLD}║{Colors.END}    Tokens: {Colors.GREEN}{stats['improvement']['tokens']:.1f}x menos tokens{Colors.END}{' ' * (48 - len(f'{stats['improvement']['tokens']:.1f}x menos tokens'))}║")
    print(f"{Colors.BOLD}║{Colors.END}    Costo: {Colors.GREEN}{stats['improvement']['cost']:.1f}x más barato{Colors.END}{' ' * (49 - len(f'{stats['improvement']['cost']:.1f}x más barato'))}║")

    print(f"{Colors.BOLD}╚{'═' * 78}╝{Colors.END}\n")


async def run_comparison(queries: List[str], num_queries: int = None):
    """
    Ejecuta comparación entre métodos.

    Args:
        queries: Lista de queries a probar
        num_queries: Limitar número de queries (None = todas)
    """
    # Limitar queries si se especifica
    if num_queries:
        queries = queries[:num_queries]

    print_header("COMPARACIÓN: AGENT RAG CON Y SIN ÍNDICES")

    # Paths
    docs_path = project_root / "data" / "documentos"
    indices_path = project_root / "data" / "indices"

    # Verificar que existan índices
    if not indices_path.exists() or not list(indices_path.glob("*.json")):
        print(f"{Colors.RED}Error: No se encontraron índices en {indices_path}{Colors.END}")
        print(f"{Colors.YELLOW}Ejecuta primero: python scripts/index_documents.py{Colors.END}\n")
        return

    # Inicializar retrieval
    print(f"{Colors.CYAN}Inicializando AgentRetrieval...{Colors.END}")
    model_provider = VertexAIProvider()
    retrieval = AgentRetrieval(
        model_provider=model_provider,
        documents_path=str(docs_path),
        indices_path=str(indices_path)
    )

    # Resultados
    all_results = []

    # Procesar cada query
    for i, query in enumerate(queries, 1):
        print_section(f"Query {i}/{len(queries)}: {query}")

        # Método 1: SIN índices
        print(f"{Colors.YELLOW}Probando sin índices...{Colors.END}")
        start = time.time()
        try:
            result_old = await retrieval.retrieve(
                query=query,
                top_k=3,
                use_index=False
            )
            time_old = time.time() - start

            # Estimar tokens (aproximación)
            tokens_old = len(result_old.get('context', '')) // 4  # ~4 chars por token
            cost_old = (tokens_old / 1_000_000) * 0.50  # $0.50 por 1M tokens (aproximado)

            all_results.append({
                'query': query,
                'method': 'Sin índices',
                'time': time_old,
                'tokens': tokens_old,
                'cost': cost_old,
                'success': True
            })

            print(f"  {Colors.GREEN}✓{Colors.END} Tiempo: {time_old:.2f}s | Tokens: {tokens_old:,} | Costo: ${cost_old:.4f}")

        except Exception as e:
            print(f"  {Colors.RED}✗ Error: {str(e)[:60]}{Colors.END}")
            all_results.append({
                'query': query,
                'method': 'Sin índices',
                'time': 0,
                'tokens': 0,
                'cost': 0,
                'success': False
            })

        # Método 2: CON índices
        print(f"{Colors.GREEN}Probando con índices...{Colors.END}")
        start = time.time()
        try:
            result_new = await retrieval.retrieve(
                query=query,
                top_k=3,
                use_index=True
            )
            time_new = time.time() - start

            # Estimar tokens
            tokens_new = len(result_new.get('context', '')) // 4
            cost_new = (tokens_new / 1_000_000) * 0.50

            all_results.append({
                'query': query,
                'method': 'Con índices',
                'time': time_new,
                'tokens': tokens_new,
                'cost': cost_new,
                'success': True
            })

            print(f"  {Colors.GREEN}✓{Colors.END} Tiempo: {time_new:.2f}s | Tokens: {tokens_new:,} | Costo: ${cost_new:.4f}")

            # Mostrar mejora
            if time_old > 0:
                speed_improvement = time_old / time_new
                token_improvement = tokens_old / tokens_new if tokens_new > 0 else 0
                print(f"\n  {Colors.CYAN}Mejora: {speed_improvement:.1f}x más rápido, "
                      f"{token_improvement:.1f}x menos tokens{Colors.END}")

        except Exception as e:
            print(f"  {Colors.RED}✗ Error: {str(e)[:60]}{Colors.END}")
            all_results.append({
                'query': query,
                'method': 'Con índices',
                'time': 0,
                'tokens': 0,
                'cost': 0,
                'success': False
            })

    # Tabla comparativa
    print_header("TABLA COMPARATIVA")
    print_comparison_table([r for r in all_results if r['success']])

    # Calcular estadísticas
    results_without = [r for r in all_results if r['method'] == 'Sin índices' and r['success']]
    results_with = [r for r in all_results if r['method'] == 'Con índices' and r['success']]

    if results_without and results_with:
        avg_time_without = sum(r['time'] for r in results_without) / len(results_without)
        avg_tokens_without = sum(r['tokens'] for r in results_without) / len(results_without)
        avg_cost_without = sum(r['cost'] for r in results_without) / len(results_without)

        avg_time_with = sum(r['time'] for r in results_with) / len(results_with)
        avg_tokens_with = sum(r['tokens'] for r in results_with) / len(results_with)
        avg_cost_with = sum(r['cost'] for r in results_with) / len(results_with)

        stats = {
            'without_index': {
                'avg_time': avg_time_without,
                'avg_tokens': int(avg_tokens_without),
                'avg_cost': avg_cost_without
            },
            'with_index': {
                'avg_time': avg_time_with,
                'avg_tokens': int(avg_tokens_with),
                'avg_cost': avg_cost_with
            },
            'improvement': {
                'speed': avg_time_without / avg_time_with if avg_time_with > 0 else 0,
                'tokens': avg_tokens_without / avg_tokens_with if avg_tokens_with > 0 else 0,
                'cost': avg_cost_without / avg_cost_with if avg_cost_with > 0 else 0
            }
        }

        print_summary(stats)

        # Guardar resultados en JSON
        output_file = project_root / "data" / "comparison_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'queries': len(queries),
                'results': all_results,
                'statistics': stats
            }, f, indent=2, ensure_ascii=False)

        print(f"{Colors.CYAN}Resultados guardados en: {output_file}{Colors.END}\n")


def get_default_queries() -> List[str]:
    """Retorna lista de queries de prueba"""
    return [
        "¿Cómo puedo jubilarme anticipadamente?",
        "¿Qué documentos necesito para solicitar un traspaso?",
        "¿Cuál es el proceso de afiliación a la AFP?",
        "¿Cómo solicito una devolución de aportes?",
        "¿Qué son los aportes voluntarios y cómo funcionan?",
        "¿Cuáles son los requisitos de edad para jubilarme?",
        "¿Cómo obtengo un certificado de cotizaciones?",
        "¿Qué es la densidad de cotizaciones?",
        "¿Puedo traspasar mi cuenta a otra AFP?",
        "¿Cuánto tiempo demora el proceso de jubilación?"
    ]


def main():
    """Punto de entrada del script"""
    # Parsear argumentos
    num_queries = None
    if '--queries' in sys.argv:
        try:
            idx = sys.argv.index('--queries')
            num_queries = int(sys.argv[idx + 1])
        except (IndexError, ValueError):
            print(f"{Colors.RED}Error: Uso correcto: --queries <número>{Colors.END}")
            return

    # Queries de prueba
    queries = get_default_queries()

    # Ejecutar comparación
    asyncio.run(run_comparison(queries, num_queries))


if __name__ == "__main__":
    main()
