#!/usr/bin/env bash
# Prépare une release sur une branche partie de develop : calcule la version suivante (SemVer),
# met à jour les fichiers de version, le contrat d'API, CHANGELOG.md et CHANGELOG.fr.md.
# Voir docs/technical/releasing.md.
#
# Usage (Git Bash, macOS, Linux) : ./scripts/prepare-release.sh [--version X.Y.Z] [--dry-run]
#   --version X.Y.Z : impose la version (ex. passage en 1.0.0) au lieu de la calculer
#   --dry-run       : affiche la version calculée sans rien modifier

set -euo pipefail

cd "$(dirname "$0")/.."

usage() { echo "Usage : ./scripts/prepare-release.sh [--version X.Y.Z] [--dry-run]"; }
fail() {
  echo "$1" >&2
  exit 1
}

forced_version=""
dry_run=false
while (($#)); do
  case "$1" in
    --version)
      forced_version=${2:-}
      shift 2 || fail "--version attend un numéro X.Y.Z"
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *) fail "Option inconnue : $1 ($(usage))" ;;
  esac
done

semver='^[0-9]+\.[0-9]+\.[0-9]+$'
[[ -z "$forced_version" || "$forced_version" =~ $semver ]] || fail "Version invalide : $forced_version (attendu : X.Y.Z)"

# Les tags vX.Y.Z sont posés sur main (merge commits), absents de l'historique de develop :
# on prend donc le plus grand tag du dépôt, et la plage last_tag..HEAD exclut tout ce qu'il contient.
git fetch -q --tags origin
last_tag=$(git tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname | head -n 1)
range=${last_tag:+$last_tag..}HEAD
current=${last_tag#v}
current=${current:-0.0.0}

# Incrément déduit des commits squashés (Conventional Commits) depuis la dernière release
bump=none
while IFS= read -r subject; do
  if [[ "$subject" =~ ^[a-z]+(\([^\)]*\))?!: ]]; then
    bump=major
  elif [[ "$subject" =~ ^feat(\(|:) && "$bump" != major ]]; then
    bump=minor
  elif [[ "$subject" =~ ^(fix|perf)(\(|:) && "$bump" == none ]]; then
    bump=patch
  fi
done < <(git log --format=%s "$range")
if git log --format=%b "$range" | grep -q '^BREAKING CHANGE:'; then
  bump=major
fi

IFS=. read -r major minor patch <<< "$current"
case "$bump" in
  # Tant que la version est en 0.x, un breaking change n'incrémente que Y (SemVer, API non stable)
  major) if ((major == 0)); then next="0.$((minor + 1)).0"; else next="$((major + 1)).0.0"; fi ;;
  minor) next="$major.$((minor + 1)).0" ;;
  patch) next="$major.$minor.$((patch + 1))" ;;
  none) next="" ;;
esac
version=${forced_version:-$next}

echo "Dernière release : ${last_tag:-aucune} | changements : $bump | version : ${version:-aucune}"
[[ -n "$version" ]] || fail "Aucun feat, fix, perf ni breaking change depuis ${last_tag:-le début} : rien à publier."
if [[ -n "$last_tag" ]] && [[ "$(printf '%s\n%s\n' "$current" "$version" | sort -V | tail -n 1)" == "$current" ]]; then
  fail "La version $version doit être supérieure à la dernière release ($current)."
fi
$dry_run && exit 0

[[ -f CHANGELOG.fr.md ]] || fail "CHANGELOG.fr.md est introuvable : il reçoit la section française de chaque release."

[[ -z "$(git status --porcelain)" ]] || fail "Le dépôt a des modifications non commitées : commitez-les ou mettez-les de côté."
git fetch -q origin develop
[[ "$(git rev-parse HEAD)" == "$(git rev-parse origin/develop)" ]] ||
  fail "Lancez le script sur une nouvelle branche partie d'origin/develop à jour (git switch -c chore/release-v$version origin/develop)."

echo "[version] backend/pyproject.toml, frontend/package.json, app.version -> $version"
(cd backend && uv version --quiet "$version")
(cd frontend && pnpm version "$version" --no-git-tag-version --no-git-checks --allow-same-version > /dev/null)
sed -i "s/^    version=\"[^\"]*\",$/    version=\"$version\",/" backend/app/main.py

echo "[contrat] openapi.json et schema.d.ts"
(cd backend && uv run python scripts/export_openapi.py > /dev/null)
(cd frontend && pnpm gen:api > /dev/null)

echo "[changelog] CHANGELOG.md, CHANGELOG.fr.md"
# Lancé depuis la racine : avec --repository, git-cliff ne trouve pas cliff.toml (fichier introuvable)
cliff() { frontend/node_modules/.bin/git-cliff --config cliff.toml "$@"; }
# git-cliff veut une plage A..B : sans release précédente, il prend tout l'historique
cliff_range=()
[[ -n "$last_tag" ]] && cliff_range=("$last_tag..HEAD")
# Ajoute la section de la version sous l'en-tête du fichier $1 (options git-cliff en plus : $2…).
# Les sections publiées (et relues) ne sont pas régénérées. (--prepend de git-cliff la placerait
# au-dessus de l'en-tête.)
add_section() {
  local file=$1 section first_section
  shift
  # sed retire les lignes vides de tête (le trim de cliff.toml ne s'applique pas à --body-file)
  section=$(cliff "${cliff_range[@]}" --tag "v$version" --strip header "$@" | tr -d '\r' | sed '/./,$!d')
  first_section=$(grep -n -m 1 '^## \[' "$file" | cut -d: -f1)
  {
    head -n "$((first_section - 1))" "$file"
    printf '%s\n\n' "$section"
    tail -n "+$first_section" "$file"
  } > "$file.new"
  mv "$file.new" "$file"
}
if [[ -f CHANGELOG.md ]]; then
  add_section CHANGELOG.md
else
  cliff "${cliff_range[@]}" --tag "v$version" --output CHANGELOG.md
fi
# Titres en français ; les lignes, issues des sujets de commit en anglais, sont à traduire
add_section CHANGELOG.fr.md --body-file cliff.fr.tera

echo
echo "Release v$version préparée. Relisez CHANGELOG.md, traduisez les lignes de CHANGELOG.fr.md, puis :"
echo "  git add -A && git commit -m \"chore(release): prepare v$version\""
echo "  PR vers develop (squash), puis PR develop -> main \"chore(release): v$version\" (merge commit)."
