GRANT USAGE ON SCHEMA app, mart TO app_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO app_rw;
GRANT USAGE ON SCHEMA mart TO text2sql_ro;
REVOKE ALL ON SCHEMA app FROM text2sql_ro;
GRANT SELECT ON mart.v_sales_performance, mart.v_target_achievement, mart.v_pipeline_risk TO text2sql_ro;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rw;

