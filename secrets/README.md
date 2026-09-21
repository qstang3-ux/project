# Production secret files

Create these files on the deployment host before starting `docker-compose.prod.yml`:

- `postgres_password.txt`
- `app_rw_password.txt`
- `text2sql_ro_password.txt`
- `model_secret_key.txt`

The files are ignored by Git. Store exactly one secret in each file, without surrounding quotes, and restrict access to the deployment account. Use URL-safe random values for database passwords. Keep `model_secret_key.txt` stable and back it up securely; changing it makes persisted model API keys unreadable.

