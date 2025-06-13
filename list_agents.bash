curl -X GET -H "Authorization: Bearer $(gcloud auth print-access-token)" \
-H "Content-Type: application/json" \
-H "X-Goog-User-Project: dvt-sp-agentspace" \
"https://discoveryengine.googleapis.com/v1alpha/projects/dvt-sp-agentspace/locations/global/collections/default_collection/engines/demo-agentspace_1748511960047/assistants/default_assistant/agents"