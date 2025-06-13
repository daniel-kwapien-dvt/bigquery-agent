# Resumen: Registro y Uso de Agentes ADK con Agentspace

## Introducción

Este documento ofrece un resumen breve sobre cómo registrar y utilizar agentes desarrollados con el Agent Development Kit (ADK) de Google dentro de la plataforma Agentspace. Se basa en la guía "How to register and use ADK Agents with Agentspace". Una vez registrados, los agentes pueden ser invocados por Agentspace para responder a consultas de los usuarios.

El registro de agentes es una tarea administrativa (`agents.manage` IAM permission).

## 1. Autorización de Agentes (Opcional)

Si un agente necesita actuar en nombre del usuario final (por ejemplo, para acceder a datos de BigQuery a los que solo el usuario tiene acceso), se debe configurar la autorización OAuth 2.0.

### Prerrequisitos Clave para OAuth 2.0:

*   **Registrar la aplicación con el proveedor OAuth 2.0:** Obtener un `Client ID` y `Client Secret`.
    *   Asegurarse de añadir `https://vertexaisearch.cloud.google.com/oauth-redirect` a las URIs de redirección permitidas.
*   **Definir Scopes (Ámbitos):** Solicitar solo los permisos necesarios (principio de mínimo privilegio).
*   **URI de Autorización:** Endpoint del proveedor OAuth para solicitar un código de autorización (ej. para Google: `https://accounts.google.com/o/oauth2/v2/auth?...`). Agentspace añade el `redirect_uri` automáticamente.
*   **URI de Token:** Endpoint para intercambiar el código de autorización por tokens de acceso y refresco (ej. para Google: `https://oauth2.googleapis.com/token`).

### Agregar Recurso de Autorización a Agentspace:

Se utiliza un comando `curl` para registrar la configuración de OAuth en Agentspace.

```bash
# Ejemplo resumido del comando curl para crear un recurso de autorización
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/authorizations?authorizationId=AUTH_ID" \
  -d '{
    "name": "projects/PROJECT_ID/locations/global/authorizations/AUTH_ID",
    "serverSideOauth2": {
      "clientId": "OAUTH_CLIENT_ID",
      "clientSecret": "OAUTH_CLIENT_SECRET",
      "authorizationUri": "OAUTH_AUTH_URI",
      "tokenUri": "OAUTH_TOKEN_URI"
    }
  }'
```

Donde `PROJECT_ID`, `AUTH_ID`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET`, `OAUTH_AUTH_URI`, y `OAUTH_TOKEN_URI` deben ser reemplazados por los valores correspondientes. El `name` del recurso de autorización se usará al registrar el agente.

*(Referencia: Secciones "Authorize your agents" y "Add an authorization resource to Agentspace" del PDF)*

## 2. Registro de un Agente en Agentspace

Para usar un agente ADK con Agentspace, primero debe ser desplegado (ver `doc_despliegue_agent_engine.md`). El despliegue proporciona un **nombre de recurso del motor de razonamiento** (Reasoning Engine resource name, también conocido como `ADK_DEPLOYMENT_ID` o el `resource_name` de `agent_engines.create()`), que es necesario para el registro.

### Prerrequisitos Clave para el Registro:

*   Habilitar la API de Discovery Engine (`discoveryengine.googleapis.com`).
*   Otorgar roles `Vertex AI User` y `Vertex AI Viewer` a la cuenta de servicio de Discovery Engine.

### Comando de Registro:

Se utiliza un comando `curl` para registrar el agente desplegado en Agentspace.

```bash
# Ejemplo resumido del comando curl para registrar un agente
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/assistants/default_assistant/agents" \
  -d '{
    "displayName": "DISPLAY_NAME",
    "description": "DESCRIPTION",
    "adk_agent_definition": {
      "tool_settings": {
        "tool_description": "TOOL_DESCRIPTION" /* Usada por el LLM para enrutar */
      },
      "provisioned_reasoning_engine": {
        "reasoning_engine": "projects/PROJECT_ID/locations/global/reasoningEngines/ADK_DEPLOYMENT_ID"
      },
      "authorizations": [ /* Opcional, si se usa OAuth */
        "projects/PROJECT_ID/locations/global/authorizations/AUTH_ID"
      ]
    }
  }'
```

Reemplazar `PROJECT_ID`, `APP_ID` (ID de la app de Agentspace), `DISPLAY_NAME`, `DESCRIPTION` (visible al usuario), `TOOL_DESCRIPTION` (para el LLM), `ADK_DEPLOYMENT_ID` (obtenido del despliegue del agente), y opcionalmente `AUTH_ID`.

La respuesta devuelve el nombre del recurso del agente creado, que se puede usar para futuras actualizaciones o eliminaciones.

*(Referencia: Sección "Register an agent with Agentspace" del PDF)*

## 3. Gestión de Agentes Registrados

Agentspace permite gestionar los agentes registrados mediante comandos `curl` similares para:

*   **Actualizar (`PATCH`):** Modificar campos como `displayName`, `description`, `tool_description`, `reasoning_engine`.
*   **Visualizar (`GET` un agente específico):** Obtener detalles de un agente por su nombre de recurso.
*   **Listar (`GET` colección de agentes):** Ver todos los agentes registrados en una app.
*   **Eliminar (`DELETE`):** Quitar el registro de un agente.

*(Referencia: Secciones "Update", "View", "List", "Delete" del PDF)*

## 4. Uso del Agente en Agentspace

Una vez registrado y, si es necesario, autorizado, los usuarios pueden interactuar con el agente.

### A. Mediante la Aplicación Web de Agentspace:

1.  Navegar a la aplicación Agentspace en la consola de Google Cloud.
2.  Seleccionar la app donde se registró el agente.
3.  Ir a "Integration" y asegurarse de que "Enable the Web App" esté activado.
4.  Copiar y abrir el enlace a la aplicación web.
5.  En la app web, seleccionar el agente deseado en la sección "Agents".
6.  Si es la primera vez y el agente requiere OAuth, se solicitará autorización al usuario.
7.  Tras la autorización (si aplica), se pueden enviar consultas al agente.

*(Referencia: Sección "Get answers from an Agent using the Agentspace app" del PDF)*

### B. Mediante la API (`streamAssist`):

Se puede interactuar con el agente programáticamente usando la API `streamAssist` de Discovery Engine.

```bash
# Ejemplo resumido del comando curl para usar streamAssist
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -H "X-Goog-User-Project: PROJECT_ID" \
  "https://discoveryengine.googleapis.com/v1alpha/projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/assistants/default_assistant:streamAssist" \
  -d '{
    "name": "projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/assistants/default_assistant",
    "query": {
      "text": "QUERY_TEXT"
    },
    "session": "projects/PROJECT_ID/locations/global/collections/default_collection/engines/APP_ID/sessions/-",
    "assistSkippingMode": "REQUEST_ASSIST",
    "answerGenerationMode": "AGENT",
    "agentsConfig": {
      "agent": "AGENT_RESOURCE_NAME" /* Nombre del recurso del agente registrado */
    }
  }'
```

Reemplazar `PROJECT_ID`, `APP_ID`, `QUERY_TEXT`, y `AGENT_RESOURCE_NAME`.

*(Referencia: Sección "Get answers using the API" del PDF)*