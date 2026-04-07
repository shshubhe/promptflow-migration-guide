#!/bin/bash
# Retires Prompt Flow resources after MAF is confirmed stable in production.
#
# Replaces: Prompt Flow managed online endpoint and connections.
#
# Prerequisites: Traffic already rerouted to MAF. az login completed.
# Usage: bash cutover.sh

set -euo pipefail

PF_ENDPOINT="<your-pf-endpoint>"
PF_CONNECTION="<your-pf-connection>"
RESOURCE_GROUP="<your-rg>"
WORKSPACE="<your-ws>"
FLOW_DIR="<your-flow-directory>"

read -p "Confirm traffic has been rerouted to the MAF endpoint (y/n): " confirm
[[ "$confirm" == "y" ]] || { echo "Aborting."; exit 1; }

echo "Archiving flow YAML..."
pf flow archive --source "$FLOW_DIR"

echo "Deleting PF managed online endpoint..."
az ml online-endpoint delete \
  --name "$PF_ENDPOINT" \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE" \
  --yes

echo "Deleting PF connection..."
az ml connection delete \
  --name "$PF_CONNECTION" \
  --resource-group "$RESOURCE_GROUP" \
  --workspace-name "$WORKSPACE"

echo "Done. Keep the archived flow YAML for at least 30 days before deleting."
