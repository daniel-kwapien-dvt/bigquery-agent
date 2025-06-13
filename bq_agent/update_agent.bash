curl -X PATCH \
-H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: dvt-sp-agentspace" \
"https://discoveryengine.googleapis.com/v1alpha/projects/239233954615/locations/global/collections/default_collection/engines/demo-agentspace_1748511960047/assistants/default_assistant/agents/3332440909036624252" \
-d '{
"displayName": "BigQuery Agent Simple",
"description": "Agente simple de BigQuery",

"adk_agent_definition": {
"tool_settings": {
"tool_description": "TOOL_DESCRIPTION"
},
"provisioned_reasoning_engine": {
"reasoning_engine":"projects/239233954615/locations/us-central1/reasoningEngines/6444554309743935488"
}
}
}'