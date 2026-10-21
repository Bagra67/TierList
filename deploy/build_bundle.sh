#!/usr/bin/env bash
# Assemble le bundle de déploiement tierlist-<version>.tar.gz (docs/technical/deployment.md) :
#   backend/        code, migrations Alembic, pyproject.toml, uv.lock, scripts de purge
#   frontend_dist/  build Vite (pnpm build doit avoir été lancé avant)
#   start.sh        démarrage dans le pod
# Ni tests, ni node_modules, ni .env.
#
# Usage (depuis la racine du dépôt) : bash deploy/build_bundle.sh <version> [dossier de sortie]
set -eu

if [ "$#" -lt 1 ]; then
    echo "Usage: bash deploy/build_bundle.sh <version> [output dir]" >&2
    exit 2
fi
version="$1"
output_dir="${2:-bundle}"
if ! printf '%s' "$version" | grep -Eq '^[A-Za-z0-9][A-Za-z0-9._-]*$'; then
    echo "Invalid version: $version" >&2
    exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -f "$repo_root/frontend/dist/index.html" ]; then
    echo "frontend/dist is missing: run pnpm build in frontend/ first" >&2
    exit 1
fi

name="tierlist-$version"
stage_dir="$output_dir/$name"
rm -rf "$stage_dir" "$output_dir/$name.tar.gz"
mkdir -p "$stage_dir/backend/scripts"

cp -R "$repo_root/backend/app" "$repo_root/backend/migrations" "$stage_dir/backend/"
cp "$repo_root/backend/alembic.ini" "$repo_root/backend/pyproject.toml" "$repo_root/backend/uv.lock" \
    "$stage_dir/backend/"
cp "$repo_root"/backend/scripts/purge_*.py "$stage_dir/backend/scripts/"
cp -R "$repo_root/frontend/dist" "$stage_dir/frontend_dist"
cp "$repo_root/deploy/start.sh" "$stage_dir/start.sh"
# Caches Python d'une exécution locale : jamais dans le bundle
find "$stage_dir" -name __pycache__ -type d -prune -exec rm -rf {} +

tar -czf "$output_dir/$name.tar.gz" -C "$output_dir" "$name"
echo "$output_dir/$name.tar.gz"
