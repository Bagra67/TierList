#!/usr/bin/env bash
# Runs an sftp batch file against the TierList pod (docs/technical/deployment.md): SFTP is the only
# way in, there is no SSH shell. The host key is pinned (no "accept any key"); sshpass gives the
# password, and -oBatchMode=no lets sftp use it with a batch file.
#
# Usage: pod_sftp.sh <batch file>
# Environment: SFTP_HOST, SFTP_PORT, SFTP_USER, SSHPASS (password), SFTP_KNOWN_HOSTS.
set -eu

if [ "$#" -ne 1 ]; then
    echo "Usage: pod_sftp.sh <batch file>" >&2
    exit 2
fi

known_hosts="$(mktemp)"
trap 'rm -f "$known_hosts"' EXIT
printf '%s\n' "$SFTP_KNOWN_HOSTS" >"$known_hosts"
sshpass -e sftp -oBatchMode=no -oStrictHostKeyChecking=yes \
    -oUserKnownHostsFile="$known_hosts" -oPubkeyAuthentication=no \
    -P "$SFTP_PORT" -b "$1" "$SFTP_USER@$SFTP_HOST"
