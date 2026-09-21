#!/bin/sh
set -eu

app_rw_password="$(tr -d '\r\n' < /run/secrets/app_rw_password)"
text2sql_ro_password="$(tr -d '\r\n' < /run/secrets/text2sql_ro_password)"

if [ -z "$app_rw_password" ] || [ -z "$text2sql_ro_password" ]; then
  echo "Database role passwords must not be empty" >&2
  exit 1
fi

psql --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=db_name="$POSTGRES_DB" \
  --set=app_rw_password="$app_rw_password" \
  --set=text2sql_ro_password="$text2sql_ro_password" <<'SQL'
SELECT format('CREATE ROLE app_rw LOGIN PASSWORD %L', :'app_rw_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rw') \gexec
ALTER ROLE app_rw PASSWORD :'app_rw_password';

SELECT format('CREATE ROLE text2sql_ro LOGIN PASSWORD %L', :'text2sql_ro_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'text2sql_ro') \gexec
ALTER ROLE text2sql_ro PASSWORD :'text2sql_ro_password';

GRANT CONNECT ON DATABASE :"db_name" TO app_rw, text2sql_ro;
SQL

unset app_rw_password text2sql_ro_password
