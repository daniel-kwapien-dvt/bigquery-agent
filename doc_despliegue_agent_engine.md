# Guía Rápida: Despliegue del Agente de BigQuery en Vertex AI Agent Engine

## Introducción

Este documento proporciona una guía concisa para desplegar el agente de BigQuery (desarrollado con ADK y detallado en `doc_creacion_agente_bigquery.md`) en Vertex AI Agent Engine. El despliegue permite que el agente sea accesible y utilizable como un servicio gestionado en Google Cloud.

## Prerrequisitos para el Despliegue

Antes de intentar el despliegue, asegúrate de cumplir con los siguientes prerrequisitos:

1.  **Autenticación con Google Cloud:** Debes estar autenticado con Google Cloud CLI. Generalmente, esto se logra con `gcloud auth application-default login`.
2.  **API de Vertex AI Habilitada:** La API de Vertex AI (`aiplatform.googleapis.com`) debe estar habilitada para tu proyecto de Google Cloud.
3.  **Bucket de Staging de GCS:** Necesitas un bucket de Google Cloud Storage (GCS) para staging. El script del agente (`bq_agent/agent.py`) utiliza `gs://dvt-sp-agentspace-agent-engine-staging` como ejemplo. Asegúrate de que este bucket exista y que tu cuenta tenga permisos de "Administrador de objetos de almacenamiento" (Storage Object Admin) sobre él. Puedes usar este bucket o configurar uno propio.
4.  **Versión de Python:** La versión de Python utilizada debe ser compatible (generalmente >=3.9 y <=3.12).
5.  **Librerías Necesarias:** Las librerías `google-cloud-aiplatform[adk,agent_engines]`, `python-dotenv`, y `google-cloud-bigquery` deben estar instaladas en el entorno Python desde donde se ejecuta el script de despliegue.
6.  **Variables de Entorno para el Despliegue:**
    *   `GOOGLE_CLOUD_PROJECT`: El ID de tu proyecto de Google Cloud.
    *   `GOOGLE_CLOUD_LOCATION`: La región de Google Cloud donde se desplegará el agente (ej. `us-central1`).
    *   Estas variables deben estar configuradas en tu archivo `.env` o en el entorno de ejecución.
7.  **Variables de Entorno para el Agente en Agent Engine:**
    *   `DEFAULT_PROJECT_ID`: El ID del proyecto de BigQuery que el agente consultará.
    *   `DEFAULT_DATASET_ID`: El ID del dataset de BigQuery que el agente consultará.
    *   Estas también se cargan desde `.env` y se pasan al entorno del agente desplegado.

*(Referencia: Sección de errores y prerrequisitos en `bq_agent/agent.py`)*

## Pasos para el Despliegue

El script `bq_agent/agent.py` incluye una sección `if __name__ == '__main__':` que no solo prueba las herramientas del agente, sino que también contiene la lógica para desplegarlo en Vertex AI Agent Engine.

### 1. Inicialización de Vertex AI

El primer paso en el script es inicializar el SDK de Vertex AI con la configuración de tu proyecto, ubicación y el bucket de staging.

```python
# Ejemplo de inicialización de Vertex AI (de bq_agent/agent.py)
import os
import vertexai
from dotenv import load_dotenv

load_dotenv() # Asegura que .env se cargue

AGENT_ENGINE_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
AGENT_ENGINE_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
# El bucket de staging puede ser configurado aquí o directamente en la llamada init
AGENT_ENGINE_STAGING_BUCKET = "gs://dvt-sp-agentspace-agent-engine-staging" # Ejemplo

if AGENT_ENGINE_PROJECT_ID and AGENT_ENGINE_LOCATION and AGENT_ENGINE_STAGING_BUCKET:
    vertexai.init(
        project=AGENT_ENGINE_PROJECT_ID,
        location=AGENT_ENGINE_LOCATION,
        staging_bucket=AGENT_ENGINE_STAGING_BUCKET,
    )
    print("Vertex AI inicializado correctamente.")
else:
    print("Error: GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION, y AGENT_ENGINE_STAGING_BUCKET deben estar configurados.")
```

### 2. Preparación de Variables de Entorno para Agent Engine

El agente desplegado necesitará sus propias variables de entorno (`DEFAULT_PROJECT_ID` y `DEFAULT_DATASET_ID`) para funcionar correctamente. Estas se preparan en un diccionario.

```python
# Ejemplo de preparación de variables de entorno para Agent Engine (de bq_agent/agent.py)
env_vars_for_agent_engine = {}
DEFAULT_PROJECT_ID_FOR_AGENT = os.getenv("DEFAULT_PROJECT_ID")
DEFAULT_DATASET_ID_FOR_AGENT = os.getenv("DEFAULT_DATASET_ID")

if DEFAULT_PROJECT_ID_FOR_AGENT and DEFAULT_DATASET_ID_FOR_AGENT:
    env_vars_for_agent_engine["DEFAULT_PROJECT_ID"] = DEFAULT_PROJECT_ID_FOR_AGENT
    env_vars_for_agent_engine["DEFAULT_DATASET_ID"] = DEFAULT_DATASET_ID_FOR_AGENT
    print(f"Variables de entorno preparadas para Agent Engine: {env_vars_for_agent_engine}")
else:
    print("Advertencia: DEFAULT_PROJECT_ID o DEFAULT_DATASET_ID no encontrados. Las variables de entorno para Agent Engine podrían estar incompletas.")
```

### 3. Comando de Despliegue (`agent_engines.create()`)

El despliegue se realiza utilizando la función `agent_engines.create()`. Esta función toma el objeto `Agent` (`root_agent` en el script), un nombre para mostrar, los requisitos de Python y las variables de entorno preparadas.

```python
# Ejemplo de despliegue a Agent Engine (de bq_agent/agent.py)
# Asumiendo que 'root_agent' está definido como en doc_creacion_agente_bigquery.md
from vertexai import agent_engines # Asegurar importación

# ... (definición de root_agent y env_vars_for_agent_engine) ...

try:
    print("Desplegando agente a Agent Engine... Esto puede tardar varios minutos.")
    remote_app = agent_engines.create(
        agent_engine=root_agent, # El objeto Agent definido
        display_name="BigQuery Assistant Agent", # Nombre para mostrar en la consola
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]",
            "python-dotenv",
            "google-cloud-bigquery"
        ],
        env_vars=env_vars_for_agent_engine # Variables de entorno para el agente desplegado
    )
    print("Despliegue del agente a Agent Engine iniciado.")
    print(f"Agente desplegado exitosamente. Nombre del recurso: {remote_app.resource_name}")
except Exception as e:
    print(f"Ocurrió un error durante las operaciones de Vertex AI Agent Engine: {e}")
```

## Verificación y Uso

Una vez que el comando `agent_engines.create()` se completa exitosamente:

*   Se imprimirá un **nombre de recurso** (ej. `projects/PROJECT_ID/locations/LOCATION/agentEngines/AGENT_ENGINE_ID`). Este ID es crucial para interactuar con el agente desplegado o para registrarlo en Agentspace (ver `doc_registro_agentspace.md`).
*   El agente estará disponible en la sección de Vertex AI Agent Engine en la consola de Google Cloud.

## Limpieza de Recursos (Opcional)

Si necesitas eliminar el agente desplegado y sus recursos asociados de Google Cloud, el script `bq_agent/agent.py` proporciona un ejemplo de código para hacerlo. Este código utiliza `agent_engines.get()` para obtener una referencia al agente desplegado por su nombre de recurso y luego llama a `delete()`.

```python
# Ejemplo de código de limpieza (de bq_agent/agent.py)
# import os
# import vertexai
# from vertexai import agent_engines
# from dotenv import load_dotenv
# load_dotenv() # Asegurar que .env se cargue si se ejecuta por separado
# AGENT_ENGINE_PROJECT_ID_CLEANUP = os.getenv('GOOGLE_CLOUD_PROJECT', 'tu-proyecto-gcp')
# AGENT_ENGINE_LOCATION_CLEANUP = os.getenv('GOOGLE_CLOUD_LOCATION', 'tu-region')
# DEPLOYED_AGENT_RESOURCE_NAME = 'projects/tu-proyecto-gcp/locations/tu-region/agentEngines/tu-id-agente' # Reemplazar con el nombre real

# vertexai.init(project=AGENT_ENGINE_PROJECT_ID_CLEANUP, location=AGENT_ENGINE_LOCATION_CLEANUP)
# try:
#   remote_app_to_delete = agent_engines.get(DEPLOYED_AGENT_RESOURCE_NAME)
#   if remote_app_to_delete:
#     print(f'Intentando eliminar agente: {DEPLOYED_AGENT_RESOURCE_NAME}')
#     remote_app_to_delete.delete(force=True) # force=True puede ser necesario
#     print(f'Eliminación del agente iniciada exitosamente: {DEPLOYED_AGENT_RESOURCE_NAME}')
#   else:
#     print(f'Agente no encontrado: {DEPLOYED_AGENT_RESOURCE_NAME}')
# except Exception as e_delete:
#   print(f'Error eliminando agente {DEPLOYED_AGENT_RESOURCE_NAME}: {e_delete}')
```

Para ejecutar esta limpieza, necesitarías descomentar el código, reemplazar los placeholders con tus valores reales (especialmente `DEPLOYED_AGENT_RESOURCE_NAME`) y ejecutarlo en un entorno Python con las configuraciones y autenticaciones adecuadas.