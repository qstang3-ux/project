#!/bin/sh
set -eu

read_secret() {
  secret_path="$1"
  if [ ! -r "$secret_path" ]; then
    echo "Required secret is not readable: $secret_path" >&2
    exit 1
  fi
  tr -d '\r\n' < "$secret_path"
}

urlencode() {
  python -c 'import sys; from urllib.parse import quote; print(quote(sys.stdin.read(), safe=""), end="")'
}

database_host="${DATABASE_HOST:-postgres}"
database_port="${DATABASE_PORT:-5432}"
database_name="${POSTGRES_DB:-management_star}"
migration_user="${POSTGRES_USER:-migration_owner}"

migration_password="$(read_secret /run/secrets/postgres_password)"
app_password="$(read_secret /run/secrets/app_rw_password)"
query_password="$(read_secret /run/secrets/text2sql_ro_password)"
model_secret="$(read_secret /run/secrets/model_secret_key)"

migration_password_encoded="$(printf '%s' "$migration_password" | urlencode)"
app_password_encoded="$(printf '%s' "$app_password" | urlencode)"
query_password_encoded="$(printf '%s' "$query_password" | urlencode)"

export MIGRATION_DATABASE_URL="postgresql+psycopg://${migration_user}:${migration_password_encoded}@${database_host}:${database_port}/${database_name}"
export DATABASE_URL="postgresql+psycopg://app_rw:${app_password_encoded}@${database_host}:${database_port}/${database_name}"
export QUERY_DATABASE_URL="postgresql+psycopg://text2sql_ro:${query_password_encoded}@${database_host}:${database_port}/${database_name}"
export MODEL_SECRET_KEY="$model_secret"

unset migration_password app_password query_password model_secret
unset migration_password_encoded app_password_encoded query_password_encoded

exec "$@"

