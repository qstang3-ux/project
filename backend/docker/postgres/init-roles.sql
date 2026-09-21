CREATE ROLE app_rw LOGIN PASSWORD 'app_rw';
CREATE ROLE text2sql_ro LOGIN PASSWORD 'text2sql_ro';
GRANT CONNECT ON DATABASE management_star TO app_rw, text2sql_ro;

