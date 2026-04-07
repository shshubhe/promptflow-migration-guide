#!/bin/bash
# Builds the container image, pushes it to Azure Container Registry,
# and creates a Container App.
#
# Replaces: Prompt Flow Managed Online Endpoint.
#
# Prerequisites: az login completed; ACR and Container Apps environment exist.
# Usage: bash deploy.sh

set -euo pipefail

ACR_NAME="<your-acr>"
RESOURCE_GROUP="<your-rg>"
CONTAINER_APP_ENV="<your-env>"
APP_NAME="maf-app"
IMAGE="${ACR_NAME}.azurecr.io/${APP_NAME}:latest"

az acr build --registry "$ACR_NAME" --image "${APP_NAME}:latest" .

az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_APP_ENV" \
  --image "$IMAGE" \
  --target-port 8000 \
  --ingress external \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --env-vars \
    AZURE_OPENAI_API_KEY=secretref:kv-openai-key \
    AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/ \
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=<deployment> \
    AZURE_AI_SEARCH_ENDPOINT=https://<search>.search.windows.net \
    AZURE_AI_SEARCH_INDEX_NAME=<index> \
    AZURE_AI_SEARCH_API_KEY=secretref:kv-search-key \
    APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:kv-appinsights

APP_URL=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

curl -s -X POST "https://${APP_URL}/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}' | python3 -m json.tool
