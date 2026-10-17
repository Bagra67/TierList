#!/usr/bin/env bash
# Restarts the TierList pod after a deployment (docs/technical/deployment.md).
#
# MineStrator has its own panel API (not the Pterodactyl client API):
#   PUT $PANEL_URL/server/$PANEL_SERVER_ID/poweraction   {"poweraction":"restart"}
# with the key of the GitHub environment (PANEL_API_KEY). PANEL_URL defaults to the MineStrator
# panel. Without PANEL_SERVER_ID or PANEL_API_KEY, this step is skipped and the job summary asks
# for a manual restart in the panel; the health check that follows then waits for it.
#
# Answers: 200 = restart requested. 400, 401 and any other answer fail the step with the reason
# in the job summary; 429 (too many requests) is retried once after RESTART_RETRY_DELAY_SECONDS.
#
# Writes restarted=true|false to $GITHUB_OUTPUT.
set -eu

PANEL_URL="${PANEL_URL:-https://mine.sttr.io}"
RETRY_DELAY_SECONDS="${RESTART_RETRY_DELAY_SECONDS:-30}"

summary() {
    printf '%s\n' "$*" >>"${GITHUB_STEP_SUMMARY:-/dev/null}"
}

output() {
    printf '%s\n' "$*" >>"${GITHUB_OUTPUT:-/dev/null}"
}

if [ -z "${PANEL_SERVER_ID:-}" ] || [ -z "${PANEL_API_KEY:-}" ]; then
    echo "::warning::No panel API configured: restart the pod by hand in the MineStrator panel."
    summary "### ⚠️ Restart the pod by hand"
    summary ""
    summary "The new version is uploaded but not running yet: open the MineStrator panel and restart the"
    summary "**${DEPLOY_ENVIRONMENT:-TierList}** pod. The health check below waits for the new version."
    output "restarted=false"
    exit 0
fi

response_file="$(mktemp)"
trap 'rm -f "$response_file"' EXIT

# Prints the HTTP status of the restart request (000 when the panel cannot be reached)
request_restart() {
    curl --silent --max-time 30 \
        --output "$response_file" \
        --write-out '%{http_code}' \
        --request PUT \
        --header "Authorization: Bearer $PANEL_API_KEY" \
        --header "Content-Type: application/json" \
        --data '{"poweraction":"restart"}' \
        "${PANEL_URL%/}/server/$PANEL_SERVER_ID/poweraction" || true
}

status="$(request_restart)"
if [ "$status" = "429" ]; then
    echo "The panel answered 429 (too many requests): new try in ${RETRY_DELAY_SECONDS} s."
    sleep "$RETRY_DELAY_SECONDS"
    status="$(request_restart)"
fi

case "$status" in
    200)
        echo "Restart requested through the MineStrator panel API."
        summary "Pod restarted through the MineStrator panel API."
        output "restarted=true"
        exit 0
        ;;
    400) reason="the panel refused the request (400): check PANEL_SERVER_ID" ;;
    401) reason="the panel refused the key (401): check PANEL_API_KEY" ;;
    429) reason="too many requests to the panel (429), even after a new try" ;;
    000) reason="the panel could not be reached at $PANEL_URL" ;;
    *) reason="unexpected answer of the panel (HTTP $status)" ;;
esac

# The panel's answer helps to understand the refusal; it never contains the key
details="$(head -c 300 "$response_file" | tr -d '\r\n')"
echo "::error::Pod restart failed: $reason."
summary "### ❌ Pod restart failed"
summary ""
summary "The new version is uploaded, but $reason. Restart the pod by hand in the MineStrator panel."
if [ -n "$details" ]; then
    summary ""
    summary "Panel answer: \`$details\`"
fi
output "restarted=false"
exit 1
