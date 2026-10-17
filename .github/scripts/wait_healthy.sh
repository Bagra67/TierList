#!/usr/bin/env bash
# Waits for the deployed version to answer (docs/technical/deployment.md): /api/health must report
# the expected release (not the previous one, still running until the pod restarts), then
# /api/health/db must answer 200. Fails after the last attempt.
#
# Usage: wait_healthy.sh <base url> <expected release> [attempts] [seconds between attempts]
set -eu

if [ "$#" -lt 2 ]; then
    echo "Usage: wait_healthy.sh <base url> <expected release> [attempts] [interval]" >&2
    exit 2
fi
base_url="${1%/}"
expected_release="$2"
attempts="${3:-30}"
interval="${4:-5}"

running_release() {
    curl --silent --fail --max-time 10 "$base_url/api/health" \
        | python3 -c 'import json, sys; print(json.load(sys.stdin).get("release", ""))' \
        2>/dev/null || true
}

attempt=1
while [ "$attempt" -le "$attempts" ]; do
    release="$(running_release)"
    if [ "$release" = "$expected_release" ]; then
        if curl --silent --fail --max-time 10 --output /dev/null "$base_url/api/health/db"; then
            echo "$base_url runs $expected_release and reaches its database."
            exit 0
        fi
        echo "Attempt $attempt/$attempts: $expected_release is running, the database does not answer yet."
    else
        echo "Attempt $attempt/$attempts: running release '${release:-none}', waiting for '$expected_release'."
    fi
    attempt=$((attempt + 1))
    sleep "$interval"
done

echo "::error::$base_url did not serve $expected_release with a working database in time."
exit 1
