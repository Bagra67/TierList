#!/usr/bin/env bash
# Restarts the TierList pod after a deployment (docs/technical/deployment.md).
#
# MineStrator runs a Pterodactyl-like panel: when the GitHub environment sets PANEL_URL,
# PANEL_SERVER_ID and PANEL_API_KEY (a client API key of the panel), the pod is restarted through
# the panel client API. Otherwise this step is skipped and the job summary asks for a manual
# restart in the panel; the health check that follows then waits for it.
#
# Writes restarted=true|false to $GITHUB_OUTPUT.
set -eu

summary() {
    printf '%s\n' "$*" >>"${GITHUB_STEP_SUMMARY:-/dev/null}"
}

if [ -z "${PANEL_URL:-}" ] || [ -z "${PANEL_SERVER_ID:-}" ] || [ -z "${PANEL_API_KEY:-}" ]; then
    echo "::warning::No panel API configured: restart the pod by hand in the MineStrator panel."
    summary "### ⚠️ Restart the pod by hand"
    summary ""
    summary "The new version is uploaded but not running yet: open the MineStrator panel and restart the"
    summary "**${DEPLOY_ENVIRONMENT:-TierList}** pod. The health check below waits for the new version."
    echo "restarted=false" >>"${GITHUB_OUTPUT:-/dev/null}"
    exit 0
fi

# Client API of Pterodactyl: POST /api/client/servers/<id>/power, answers 204
curl --fail-with-body --silent --show-error --max-time 30 \
    --request POST \
    --header "Authorization: Bearer $PANEL_API_KEY" \
    --header "Accept: application/json" \
    --header "Content-Type: application/json" \
    --data '{"signal":"restart"}' \
    "${PANEL_URL%/}/api/client/servers/$PANEL_SERVER_ID/power"
echo "Restart requested through the panel API."
summary "Pod restarted through the panel API."
echo "restarted=true" >>"${GITHUB_OUTPUT:-/dev/null}"
