#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
KEYSTORE_DIR="$ROOT_DIR/keystore"
KEYSTORE_FILE="$KEYSTORE_DIR/rotaai-internal-update.jks"
KEYSTORE_ALIAS="androiddebugkey"
KEYSTORE_PASSWORD="android"
ARTIFACT_NAME="rotaai-signing-key"

mkdir -p "$KEYSTORE_DIR"

restore_from_artifact() {
  [[ -n "${GITHUB_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" ]] || return 1

  local response artifact_url temp_dir
  response="$(curl -fsSL \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/artifacts?name=${ARTIFACT_NAME}&per_page=100")"

  artifact_url="$(python -c 'import json,sys; data=json.load(sys.stdin); items=[a for a in data.get("artifacts",[]) if not a.get("expired")]; items.sort(key=lambda a:a.get("created_at", ""), reverse=True); print(items[0].get("archive_download_url", "") if items else "")' <<<"$response")"
  [[ -n "$artifact_url" ]] || return 1

  temp_dir="$(mktemp -d)"
  trap 'rm -rf "$temp_dir"' RETURN
  curl -fsSL -L \
    -H "Authorization: Bearer ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$artifact_url" -o "$temp_dir/signing.zip"
  unzip -j -o "$temp_dir/signing.zip" 'rotaai-internal-update.jks' -d "$KEYSTORE_DIR" >/dev/null
  [[ -s "$KEYSTORE_FILE" ]]
}

if [[ ! -s "$KEYSTORE_FILE" ]]; then
  if restore_from_artifact; then
    echo "Chave estável restaurada do artefato protegido do GitHub Actions."
  else
    echo "Nenhuma chave estável anterior encontrada. Criando a chave inicial."
    keytool -genkeypair \
      -keystore "$KEYSTORE_FILE" \
      -storepass "$KEYSTORE_PASSWORD" \
      -keypass "$KEYSTORE_PASSWORD" \
      -alias "$KEYSTORE_ALIAS" \
      -keyalg RSA \
      -keysize 3072 \
      -validity 10000 \
      -dname "CN=RotaAi Internal Update, OU=RotaAi, O=Mega Center, L=Santo Andre, ST=SP, C=BR"
  fi
fi

chmod 600 "$KEYSTORE_FILE"
keytool -list -keystore "$KEYSTORE_FILE" -storepass "$KEYSTORE_PASSWORD" -alias "$KEYSTORE_ALIAS" >/dev/null
keytool -list -v -keystore "$KEYSTORE_FILE" -storepass "$KEYSTORE_PASSWORD" -alias "$KEYSTORE_ALIAS" \
  | grep -E 'Alias name:|SHA256:'
