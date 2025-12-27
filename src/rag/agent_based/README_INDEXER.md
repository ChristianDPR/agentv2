# Agent RAG Indexer

Sistema completo de indexación para Agent RAG que procesa documentos PDF en batches y genera índices JSON con resúmenes por sección.

## Características

- **Procesamiento por batches**: Agrupa páginas de PDF en batches de 5 para resumir eficientemente
- **Resúmenes LLM**: Usa Vertex AI (Gemini) para generar resúmenes inteligentes
- **Extracción de metadata**: Automática desde contenido y nombre de archivo
- **Keywords por sección**: Generación automática de palabras clave
- **Índices JSON**: Estructura clara para búsqueda rápida

## Uso Básico

```python
import asyncio
from src.rag.agent_based.indexer import AgentRAGIndexer
from src.framework.model_provider import VertexAIProvider

async def index_my_pdfs():
    # 1. Crear provider
    provider = VertexAIProvider()

    # 2. Crear indexer
    indexer = AgentRAGIndexer(provider)

    # 3. Indexar documento
    index = await indexer.index_document(
        pdf_path="data/documentos/jubilacion/proc-jub-001.pdf",
        output_dir="data/indices",
        batch_size=5
    )

    print(f"✅ Indexado: {index['document_id']}")
    print(f"📄 Páginas: {index['total_pages']}")
    print(f"📚 Secciones: {len(index['sections'])}")

# Ejecutar
asyncio.run(index_my_pdfs())
```

## Estructura del Índice JSON

```json
{
  "document_id": "PROC-JUB-001",
  "title": "Jubilación por Vejez",
  "category": "jubilacion",
  "source_file": "proc-jubilacion-001.pdf",
  "total_pages": 15,
  "summary": "Resumen global del documento en 200 palabras...",
  "metadata": {
    "procedure_code": "PROC-JUB-001",
    "version": "1.0",
    "date": "2024-01-15",
    "indexed_at": "2024-11-24T10:30:00Z"
  },
  "sections": [
    {
      "section_id": "1",
      "title": "Sección 1",
      "pages": [1, 2, 3, 4, 5],
      "page_range": "1-5",
      "summary": "Resumen de esta sección generado por LLM...",
      "keywords": ["jubilación", "requisitos", "edad", "legal", "DL-3500"]
    }
  ]
}
```

## Métodos Principales

### `index_document(pdf_path, output_dir, batch_size)`

Procesa un PDF completo y genera su índice.

**Parámetros:**
- `pdf_path` (str): Ruta al archivo PDF
- `output_dir` (str): Directorio donde guardar índices (default: "data/indices")
- `batch_size` (int): Páginas por batch (default: 5)

**Returns:** Dict con el índice generado

**Flujo interno:**
1. Lee PDF completo con pdfplumber
2. Agrupa páginas en batches
3. Resume cada batch con LLM
4. Genera resumen global del documento
5. Extrae metadata automáticamente
6. Crea índice JSON estructurado
7. Guarda en disco

### Métodos Internos

- `_read_pdf_pages(pdf_path)`: Lee PDF página por página
- `_create_batches(pages, batch_size)`: Agrupa páginas en batches
- `_summarize_batch(batch)`: Resume batch con LLM
- `_summarize_document(sections)`: Genera resumen global
- `_extract_metadata_from_content(pages, pdf_path)`: Extrae metadata
- `_create_index(document, global_summary, sections)`: Crea estructura JSON
- `_save_index(index, output_dir)`: Guarda índice en disco
- `_extract_keywords(text, max_keywords)`: Extrae keywords básicos

## Configuración Requerida

### 1. Variables de Entorno (.env)

```bash
# Vertex AI
VERTEX_AI_PROJECT=your-gcp-project-id
VERTEX_AI_LOCATION=us-central1
DEFAULT_LLM_MODEL=gemini-2.0-flash-001
```

### 2. Dependencias

```bash
pip install pdfplumber google-cloud-aiplatform
```

## Testing

Ejecutar el test incluido:

```bash
python src/rag/agent_based/indexer.py
```

Este test:
1. Inicializa el ModelProvider
2. Busca PDFs en `data/documentos/`
3. Indexa el primer PDF encontrado
4. Guarda el índice en `data/indices/`
5. Imprime el resultado

## Ejemplo de Salida

```
============================================================
TEST: AgentRAGIndexer
============================================================

1️⃣  Inicializando ModelProvider...
   ✓ Provider: VertexAIProvider(project=your-project, model=gemini-2.0-flash-001)

2️⃣  Creando indexer...
   ✓ Indexer creado

3️⃣  Buscando PDFs de ejemplo...
   ✓ Usando: data/documentos/jubilacion/proc-jub-001.pdf

4️⃣  Indexando documento...

📄 Indexando: data/documentos/jubilacion/proc-jub-001.pdf
   ✓ Leídas 15 páginas
   ✓ Creados 3 batches de 5 páginas
   📝 Resumiendo batch 1/3...
   📝 Resumiendo batch 2/3...
   📝 Resumiendo batch 3/3...
   ✓ 3 secciones resumidas
   📝 Generando resumen global del documento...
   ✅ Índice guardado: data/indices/PROC-JUB-001.json

5️⃣  RESULTADO:
============================================================
Document ID: PROC-JUB-001
Title: Jubilación por Vejez
Category: jubilacion
Total Pages: 15
Sections: 3

Global Summary:
Este documento describe el procedimiento completo para solicitar jubilación
por vejez en AFP Integra. Los requisitos principales incluyen: tener 60 años
(mujeres) o 65 años (hombres), estar afiliado al sistema AFP, y cumplir con
20 años de cotizaciones...

First Section:
  - Pages: 1-5
  - Keywords: jubilación, requisitos, edad, cotizaciones, legal
  - Summary: Esta sección establece el marco legal del procedimiento...
============================================================

✅ Test completado!
📁 Índice guardado en: data/indices/PROC-JUB-001.json
```

## Integración con Agent RAG

El indexer está diseñado para trabajar junto con el resto del Agent RAG:

1. **Fase de Indexación** (offline):
   - Se procesan todos los PDFs con `indexer.py`
   - Se generan índices JSON en `data/indices/`

2. **Fase de Consulta** (runtime):
   - El agente busca primero en índices (rápido)
   - Si necesita más detalle, lee documento completo con `document_reader.py`
   - Usa resúmenes y keywords para búsqueda eficiente

## Ventajas vs Vector RAG

| Característica | Agent RAG (Indexer) | Vector RAG |
|---------------|---------------------|------------|
| **Setup** | Simple (solo LLM) | Complejo (vectores + DB) |
| **Costo** | Bajo (1 vez) | Alto (embeddings) |
| **Búsqueda** | Metadata + keywords | Similarity search |
| **Resúmenes** | Sí (por sección) | No |
| **Flexibilidad** | Alta (JSON) | Media (vectores) |

## Troubleshooting

### Error: "pdfplumber no está instalado"

```bash
pip install pdfplumber
```

### Error: "project_id es requerido"

Configurar `.env`:
```bash
VERTEX_AI_PROJECT=your-gcp-project-id
```

### Error: "No hay PDFs en data/documentos/"

Generar PDFs primero:
```bash
python scripts/generate_synthetic_pdfs.py
```

### LLM falla al resumir

El indexer tiene fallback automático:
- Si el LLM falla, usa las primeras 200 palabras del batch
- El proceso continúa sin interrumpirse

## Próximos Pasos

1. Indexar todos los documentos:
   ```python
   from pathlib import Path

   async def index_all():
       indexer = AgentRAGIndexer(provider)
       for pdf in Path("data/documentos").rglob("*.pdf"):
           await indexer.index_document(str(pdf))
   ```

2. Crear búsqueda por índices:
   ```python
   async def search_indices(query: str):
       # Buscar en índices JSON por keywords/metadata
       # Más rápido que leer PDFs completos
   ```

3. Integrar con Agente RAG completo:
   ```python
   class AgentRAG:
       def __init__(self, indexer, reader, model):
           self.indexer = indexer
           self.reader = reader
           self.model = model
   ```

## Referencias

- **CLAUDE.md**: Arquitectura completa del sistema
- **document_reader.py**: Lectura directa de documentos
- **model_provider.py**: Integración con Vertex AI
