# Documentación: Creación de un Agente ADK para Interacción con BigQuery

## Introducción

Este documento describe el proceso de creación de un agente utilizando el Agent Development Kit (ADK) de Google, diseñado específicamente para interactuar con Google BigQuery. El propósito principal de este agente es permitir la consulta de tablas, la obtención de esquemas y la ejecución de consultas SQL en un proyecto y dataset de BigQuery preconfigurados.

## Configuración Inicial y Dependencias

Antes de definir el agente, es crucial configurar las variables de entorno necesarias y asegurarse de que todas las dependencias de Python estén disponibles.

### Variables de Entorno

El agente depende de dos variables de entorno principales para identificar el proyecto y el dataset por defecto en BigQuery:

*   `DEFAULT_PROJECT_ID`: El ID del proyecto de Google Cloud donde reside el dataset de BigQuery.
*   `DEFAULT_DATASET_ID`: El ID del dataset dentro del proyecto especificado.

Estas variables se cargan típicamente desde un archivo `.env` al inicio del script del agente.

```python
# Ejemplo de carga de variables de entorno (de bq_agent/agent.py)
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# IDs por defecto del Proyecto y Dataset de BigQuery cargados desde variables de entorno
DEFAULT_PROJECT_ID = os.getenv("DEFAULT_PROJECT_ID")
DEFAULT_DATASET_ID = os.getenv("DEFAULT_DATASET_ID")

if not DEFAULT_PROJECT_ID or not DEFAULT_DATASET_ID:
    raise ValueError(
        "DEFAULT_PROJECT_ID y DEFAULT_DATASET_ID deben estar configurados en el archivo .env o en el entorno."
    )
```

### Librerías Python

El agente utiliza varias librerías de Python. Las principales incluyen:

*   `google-cloud-bigquery`: Para interactuar con la API de BigQuery.
*   `google-adk`: El kit de desarrollo de agentes de Google.
*   `python-dotenv`: Para cargar variables de entorno desde un archivo `.env`.
*   `vertexai`: Para interactuar con Vertex AI, especialmente para el despliegue.

A continuación, se muestran las importaciones relevantes del script del agente:

```python
# Importaciones principales (de bq_agent/agent.py)
import os
import datetime
from decimal import Decimal
from dotenv import load_dotenv
from google.cloud import bigquery
from google.adk.agents import Agent
import vertexai
from vertexai.preview import reasoning_engines
from vertexai import agent_engines # Importación actualizada
```

## Definición del Agente ADK

El núcleo del sistema es un agente ADK, implementado utilizando la clase `Agent` de la librería `google.adk.agents`.

### Parámetros del Agente

El agente se configura con los siguientes parámetros:

*   **`name`**: Un nombre identificador para el agente (ej. "BigQueryAssistant").
*   **`model`**: El modelo de lenguaje grande (LLM) que potenciará al agente (ej. "gemini-1.5-flash-preview-0514").
*   **`instruction`**: Un prompt detallado que guía el comportamiento del agente, especificando su flujo de trabajo y cómo debe utilizar sus herramientas.
*   **`description`**: Una breve descripción de las capacidades del agente.
*   **`tools`**: Una lista de funciones Python que el agente puede invocar para realizar tareas específicas.

### Instrucción del Agente (Prompt)

La instrucción es fundamental para el correcto funcionamiento del agente. Define cómo debe procesar las solicitudes del usuario y coordinar el uso de sus herramientas.

```python
# Instrucción dinámica del agente (de bq_agent/agent.py)
agent_instruction = (
    f"Eres un asistente que consulta Google BigQuery desde un proyecto y dataset preconfigurados. "
    f"El ID del proyecto por defecto es '{DEFAULT_PROJECT_ID}' y el ID del dataset por defecto es '{DEFAULT_DATASET_ID}'. "
    f"Tu flujo de trabajo es el siguiente:\n"
    f"1. Cuando se te pida encontrar información, primero llama a `list_dataset_tables` para ver las tablas disponibles del dataset por defecto (que es {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}).\n"
    f"2. Basándote en la solicitud del usuario y la lista de tablas, identifica el `table_id` más relevante.\n"
    f"3. Llama a `get_bigquery_table_schema` con el `table_id` seleccionado para entender su estructura (esta tabla estará en {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}).\n"
    f"4. Construye una consulta SQL basándote en la solicitud del usuario y el esquema de la tabla. IMPORTANTE CRÍTICO: Al construir la consulta SQL, DEBES usar el nombre completamente cualificado de la tabla en el formato `{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.selected_table_id` (ej., 'SELECT * FROM `{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.my_table` ...'). Asegúrate de usar acentos graves (backticks) alrededor de la ruta completa si contiene caracteres especiales, o alrededor de cada componente si es necesario.\n"
    f"5. Llama a `run_bigquery_sql_query` con la consulta SQL completamente construida.\n"
    f"6. Presenta los resultados o las ideas derivadas de la consulta al usuario.\n"
    f"No necesitas pedir project_id o dataset_id ya que están preconfigurados con los valores '{DEFAULT_PROJECT_ID}' y '{DEFAULT_DATASET_ID}' respectivamente."
)
```

### Creación de la Instancia del Agente

```python
# Definición del Agente ADK (de bq_agent/agent.py)
root_agent = Agent(
    name="BigQueryAssistant",
    model="gemini-1.5-flash-preview-0514", # O tu modelo Gemini preferido
    instruction=agent_instruction,
    description=(
        "Un agente que lista tablas de un dataset por defecto de BigQuery, "
        "selecciona una tabla, obtiene su esquema y ejecuta consultas SQL."
    ),
    tools=[
        list_dataset_tables,
        get_bigquery_table_schema,
        run_bigquery_sql_query,
    ],
    # enable_code_execution=True # Habilitar si es necesario
)
```

## Herramientas del Agente (Tools)

El agente está equipado con un conjunto de herramientas (funciones Python) que le permiten interactuar directamente con BigQuery.

### 1. `list_dataset_tables() -> list[str]`

*   **Propósito:** Lista todas las tablas dentro del proyecto y dataset de BigQuery preconfigurados.
*   **Retorno:** Una lista de strings, donde cada string es el ID de una tabla.

```python
# Función list_dataset_tables (de bq_agent/agent.py)
def list_dataset_tables() -> list[str]:
    """
    Lista todas las tablas dentro del proyecto y dataset por defecto de BigQuery.
    El proyecto y dataset por defecto están determinados por las variables de entorno
    DEFAULT_PROJECT_ID y DEFAULT_DATASET_ID.

    Returns:
        Una lista de strings con los IDs de las tablas.
        Retorna una lista vacía si ocurre un error o no se encuentran tablas.
    """
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        dataset_ref = client.dataset(DEFAULT_DATASET_ID)
        tables = client.list_tables(dataset_ref)
        table_ids = [table.table_id for table in tables]
        if not table_ids:
            print(f"No se encontraron tablas en el dataset {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.")
            return []
        return table_ids
    except Exception as e:
        print(f"Error listando tablas para {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}: {e}")
        return []
```

### 2. `get_bigquery_table_schema(table_id: str) -> list[dict]`

*   **Propósito:** Recupera el esquema (nombres de columna, tipos, modos) de una tabla específica en el proyecto y dataset preconfigurados.
*   **Argumentos:**
    *   `table_id (str)`: El ID de la tabla de BigQuery.
*   **Retorno:** Una lista de diccionarios, donde cada diccionario representa un campo en el esquema de la tabla.

```python
# Función get_bigquery_table_schema (de bq_agent/agent.py)
def get_bigquery_table_schema(table_id: str) -> list[dict]:
    """
    Recupera el esquema de una tabla específica en el proyecto y dataset por defecto de BigQuery.
    El proyecto y dataset por defecto están determinados por las variables de entorno
    DEFAULT_PROJECT_ID y DEFAULT_DATASET_ID.

    Args:
        table_id: El ID de la tabla de BigQuery.

    Returns:
        Una lista de diccionarios, donde cada diccionario representa un campo
        en el esquema de la tabla (ej., {'name': field.name, 'type': field.field_type, 'mode': field.mode}).
        Retorna una lista vacía si ocurre un error.
    """
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        table_ref = client.dataset(DEFAULT_DATASET_ID).table(table_id)
        table = client.get_table(table_ref)
        schema_info = []
        for field in table.schema:
            schema_info.append({
                "name": field.name,
                "type": field.field_type,
                "mode": field.mode
            })
        if not schema_info:
            print(f"Esquema no encontrado o vacío para la tabla {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{table_id}.")
            return []
        return schema_info
    except Exception as e:
        print(f"Error obteniendo esquema para {DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.{table_id}: {e}")
        return []
```

### 3. `run_bigquery_sql_query(query: str) -> list[dict]`

*   **Propósito:** Ejecuta una consulta SQL dada contra BigQuery y devuelve los resultados. La facturación de la consulta se asocia al proyecto por defecto.
*   **Argumentos:**
    *   `query (str)`: La consulta SQL a ejecutar.
*   **Retorno:** Una lista de diccionarios, donde cada diccionario representa una fila del resultado de la consulta.

```python
# Función run_bigquery_sql_query (de bq_agent/agent.py)
def run_bigquery_sql_query(query: str) -> list[dict]:
    """
    Ejecuta una consulta SQL dada contra BigQuery usando el ID del proyecto por defecto para la facturación.
    El proyecto por defecto está determinado por la variable de entorno DEFAULT_PROJECT_ID.

    Args:
        query: La cadena de consulta SQL a ejecutar.

    Returns:
        Una lista de diccionarios, donde cada diccionario representa una fila
        del resultado de la consulta. Retorna una lista vacía si ocurre un error o
        la consulta no devuelve resultados.
    """
    try:
        client = bigquery.Client(project=DEFAULT_PROJECT_ID)
        query_job = client.query(query)  # Solicitud a la API
        results = query_job.result()  # Espera a que el trabajo se complete.

        # Procesar filas para asegurar que todos los datos sean serializables a JSON
        processed_rows = []
        for row in results:
            processed_row = {}
            for key, value in row.items():
                if isinstance(value, (datetime.date, datetime.datetime)):
                    processed_row[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    processed_row[key] = str(value) # Convertir Decimal a string
                else:
                    processed_row[key] = value
            processed_rows.append(processed_row)
        
        if not processed_rows:
            print(f"La consulta no devolvió resultados: {query}")
            return []
        return processed_rows
    except Exception as e:
        print(f"Error ejecutando consulta '{query}': {e}")
        return []
```

## Flujo de Trabajo del Agente

El agente sigue un flujo de trabajo estructurado, definido en su `instruction` (prompt), para responder a las solicitudes del usuario:

1.  **Listar Tablas:** Ante una solicitud de información, el agente primero invoca `list_dataset_tables()` para obtener una lista de las tablas disponibles en el dataset preconfigurado (`{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}`).
2.  **Identificar Tabla Relevante:** Basándose en la solicitud del usuario y la lista de tablas, el LLM del agente identifica la tabla (`table_id`) más pertinente para la consulta.
3.  **Obtener Esquema de Tabla:** Luego, el agente llama a `get_bigquery_table_schema()` con el `table_id` seleccionado para comprender la estructura de la tabla (columnas, tipos de datos).
4.  **Construir Consulta SQL:** Con el conocimiento del esquema y la solicitud del usuario, el agente construye una consulta SQL. Es crucial que la consulta utilice el nombre completamente cualificado de la tabla: `` `{DEFAULT_PROJECT_ID}.{DEFAULT_DATASET_ID}.selected_table_id}` ``.
5.  **Ejecutar Consulta SQL:** El agente invoca `run_bigquery_sql_query()` con la consulta SQL generada.
6.  **Presentar Resultados:** Finalmente, el agente procesa los resultados de la consulta y los presenta al usuario de manera comprensible.

Este flujo asegura que el agente pueda explorar autónomamente los datos disponibles y construir consultas precisas para satisfacer las necesidades del usuario sin requerir que este especifique los nombres exactos de las tablas o sus esquemas.

A continuación, se muestra un diagrama conceptual del flujo (adaptado de `bigquery_agent_plan.md`):

```mermaid
graph TD
    A[Solicitud del Usuario: Obtener información de BigQuery] --> B{Agente ADK (BigQueryAssistant)};

    subgraph Agente ADK
        direction LR
        B -- invoca --> T1[Herramienta: list_dataset_tables];
        B -- invoca --> T2[Herramienta: get_bigquery_table_schema];
        B -- invoca --> T3[Herramienta: run_bigquery_sql_query];
    end

    T1 --> BQ1[API de BigQuery: Listar Tablas];
    T2 --> BQ2[API de BigQuery: Obtener Metadatos de Tabla];
    T3 --> BQ3[API de BigQuery: Ejecutar Consulta];

    BQ1 -- Lista de Tablas --> T1;
    BQ2 -- Esquema de Tabla --> T2;
    BQ3 -- Resultados de Consulta --> T3;

    T1 -- Provee lista de tablas a --> B;
    T2 -- Provee esquema a --> B;
    T3 -- Provee datos de consulta a --> B;

    B -- Devuelve información/resultados --> L[Usuario: Información/Resultados];
    ```