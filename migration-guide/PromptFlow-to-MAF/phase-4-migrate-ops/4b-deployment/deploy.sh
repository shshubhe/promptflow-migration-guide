#!/bin/bash
# Builds the container image, pushes it to Azure Container Registry,
# and creates a Container App.
#
# Replaces: Prompt Flow Managed Online Endpoint.
#
# Prerequisites:
#   - az login completed
#   - ACR and Container Apps environment already exist
#   - export AZURE_OPENAI_API_KEY, AZURE_AI_SEARCH_API_KEY,
#            APPLICATIONINSIGHTS_CONNECTION_STRING before running
#   - or switch to the managed-identity pattern in managed_identity.md
# Usage: bash deploy.sh

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
GUIDE_DIR=$(cd "${SCRIPT_DIR}/../.." && pwd)
cd "$GUIDE_DIR"

ACR_NAME="<your-acr>"
RESOURCE_GROUP="<your-rg>"
CONTAINER_APP_ENV="<your-env>"
APP_NAME="maf-app"
OPENAI_ENDPOINT="https://<resource>.openai.azure.com/"
OPENAI_DEPLOYMENT="<deployment>"
SEARCH_ENDPOINT="https://<search>.search.windows.net"
SEARCH_INDEX="<index>"
IMAGE="${ACR_NAME}.azurecr.io/${APP_NAME}:latest"

az acr build \
  --registry "$ACR_NAME" \
  --image "${APP_NAME}:latest" \
  --file phase-4-migrate-ops/4b-deployment/Dockerfile \
  .

az containerapp create \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --environment "$CONTAINER_APP_ENV" \
  --image "$IMAGE" \
  --target-port 8000 \
  --ingress external \
  --registry-server "${ACR_NAME}.azurecr.io" \
  --secrets \
    openai-key="$AZURE_OPENAI_API_KEY" \
    search-key="$AZURE_AI_SEARCH_API_KEY" \
    appinsights-conn="$APPLICATIONINSIGHTS_CONNECTION_STRING" \
  --env-vars \
    AZURE_OPENAI_API_KEY=secretref:openai-key \
    AZURE_OPENAI_ENDPOINT="$OPENAI_ENDPOINT" \
    AZURE_OPENAI_CHAT_DEPLOYMENT_NAME="$OPENAI_DEPLOYMENT" \
    AZURE_AI_SEARCH_ENDPOINT="$SEARCH_ENDPOINT" \
    AZURE_AI_SEARCH_INDEX_NAME="$SEARCH_INDEX" \
    AZURE_AI_SEARCH_API_KEY=secretref:search-key \
    APPLICATIONINSIGHTS_CONNECTION_STRING=secretref:appinsights-conn

APP_URL=$(az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "properties.configuration.ingress.fqdn" -o tsv)

for _ in {1..12}; do
  if curl --silent --fail "https://${APP_URL}/docs" >/dev/null; then
    break
  fi
  sleep 10
done

curl --fail-with-body -X POST "https://${APP_URL}/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}' | python3 -m json.tool
