"""Initial app and mart schemas.

Revision ID: 20260916_0001
Revises:
Create Date: 2026-09-16
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260916_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DDL = r"""
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE app.seed_versions (
    version varchar(64) PRIMARY KEY,
    seed integer NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mart.business_units (id uuid PRIMARY KEY, code varchar(32) UNIQUE NOT NULL, name varchar(100) UNIQUE NOT NULL, region varchar(50), active boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE mart.industries (id uuid PRIMARY KEY, code varchar(32) UNIQUE NOT NULL, major_name varchar(100) NOT NULL, name varchar(100) NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(major_name,name));
CREATE TABLE mart.product_lines (id uuid PRIMARY KEY, code varchar(32) UNIQUE NOT NULL, name varchar(100) UNIQUE NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE mart.customers (id uuid PRIMARY KEY, name varchar(200) UNIQUE NOT NULL, customer_level varchar(30), customer_category varchar(50), province varchar(50), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE mart.contracts (
    id uuid PRIMARY KEY, contract_no varchar(64) UNIQUE NOT NULL, opportunity_no varchar(64), contract_name varchar(200) NOT NULL,
    signed_at date NOT NULL, seller_name varchar(200) NOT NULL, buyer_name varchar(200), final_customer_id uuid REFERENCES mart.customers(id),
    business_unit_id uuid NOT NULL REFERENCES mart.business_units(id), industry_id uuid REFERENCES mart.industries(id), product_line_id uuid NOT NULL REFERENCES mart.product_lines(id),
    product_model varchar(100), quantity integer CHECK(quantity >= 0), tax_rate numeric(6,4) CHECK(tax_rate >= 0),
    contract_amount_tax_included numeric(18,2) NOT NULL CHECK(contract_amount_tax_included >= 0),
    contract_amount_tax_excluded numeric(18,2) NOT NULL CHECK(contract_amount_tax_excluded >= 0),
    status varchar(30) NOT NULL CHECK(status IN ('active','cancelled','completed')), is_statistical boolean NOT NULL DEFAULT true,
    special_program varchar(100), created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE mart.revenue_facts (id uuid PRIMARY KEY, contract_id uuid NOT NULL REFERENCES mart.contracts(id), recognized_at date NOT NULL, recognized_amount numeric(18,2) NOT NULL CHECK(recognized_amount >= 0), source_type varchar(30) NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE mart.payment_facts (id uuid PRIMARY KEY, contract_id uuid NOT NULL REFERENCES mart.contracts(id), paid_at date NOT NULL, payment_amount numeric(18,2) NOT NULL CHECK(payment_amount >= 0), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE mart.sales_targets (id uuid PRIMARY KEY, business_unit_id uuid NOT NULL REFERENCES mart.business_units(id), year smallint NOT NULL CHECK(year BETWEEN 2000 AND 2100), commercial_target_amount numeric(18,2) NOT NULL CHECK(commercial_target_amount >= 0), solution_target_amount numeric(18,2) NOT NULL CHECK(solution_target_amount >= 0), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(business_unit_id,year));
CREATE TABLE mart.project_pipeline (id uuid PRIMARY KEY, contract_id uuid REFERENCES mart.contracts(id), opportunity_no varchar(64) UNIQUE NOT NULL, project_name varchar(200) NOT NULL, business_unit_id uuid NOT NULL REFERENCES mart.business_units(id), industry_id uuid REFERENCES mart.industries(id), product_line_id uuid REFERENCES mart.product_lines(id), stage varchar(30) NOT NULL, competition_risk varchar(10), signing_risk varchar(10), delivery_risk varchar(10), overall_risk varchar(10), expected_landing_date date, amount_tax_excluded numeric(18,2) CHECK(amount_tax_excluded >= 0), production_scheduled boolean NOT NULL DEFAULT false, progress_note text, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.data_sources (id uuid PRIMARY KEY, name varchar(100) UNIQUE NOT NULL, description text, "group" varchar(20) NOT NULL DEFAULT 'ledger', enabled boolean NOT NULL DEFAULT true, is_default boolean NOT NULL DEFAULT false, unavailable_reason varchar(500), data_as_of date NOT NULL, allowed_objects jsonb NOT NULL DEFAULT '[]', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE app.qa_sessions (id uuid PRIMARY KEY, owner_id varchar(64) NOT NULL DEFAULT 'demo-user', title varchar(60) NOT NULL DEFAULT '新对话', pinned boolean NOT NULL DEFAULT false, parent_session_id uuid REFERENCES app.qa_sessions(id), created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), deleted_at timestamptz);
CREATE TABLE app.qa_messages (id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES app.qa_sessions(id) ON DELETE CASCADE, role varchar(20) NOT NULL CHECK(role IN ('user','assistant','system_event')), content text NOT NULL, source_message_id uuid REFERENCES app.qa_messages(id), created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE app.model_configs (id uuid PRIMARY KEY, name varchar(100) UNIQUE NOT NULL, provider varchar(50) NOT NULL, base_url text NOT NULL, model_name varchar(200) NOT NULL, encrypted_api_key text, active boolean NOT NULL DEFAULT false, enabled boolean NOT NULL DEFAULT true, timeout_seconds integer NOT NULL DEFAULT 30 CHECK(timeout_seconds BETWEEN 1 AND 120), last_test_status varchar(30), last_tested_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE UNIQUE INDEX model_one_active ON app.model_configs(active) WHERE active;
CREATE TABLE app.qa_executions (id uuid PRIMARY KEY, request_id varchar(64) NOT NULL, idempotency_key varchar(128) UNIQUE NOT NULL, session_id uuid NOT NULL REFERENCES app.qa_sessions(id), user_message_id uuid NOT NULL REFERENCES app.qa_messages(id), assistant_message_id uuid REFERENCES app.qa_messages(id), model_config_id uuid REFERENCES app.model_configs(id), status varchar(20) NOT NULL CHECK(status IN ('queued','running','completed','failed','cancelled','rejected')), question text NOT NULL, data_source_ids jsonb NOT NULL, selected_objects jsonb NOT NULL DEFAULT '[]', generated_sql text, executed_sql text, validation_summary text, result_json jsonb, answer text, chart_json jsonb, follow_up_questions jsonb NOT NULL DEFAULT '[]', model_name varchar(200), token_usage jsonb NOT NULL DEFAULT '{}', row_count integer, duration_ms integer, error_code varchar(80), error_message text, regenerated_from_execution_id uuid REFERENCES app.qa_executions(id), created_at timestamptz NOT NULL DEFAULT now(), completed_at timestamptz);
CREATE TABLE app.qa_execution_steps (id uuid PRIMARY KEY, execution_id uuid NOT NULL REFERENCES app.qa_executions(id) ON DELETE CASCADE, step_type varchar(40) NOT NULL, status varchar(20) NOT NULL, summary text NOT NULL DEFAULT '', started_at timestamptz, completed_at timestamptz);
CREATE TABLE app.qa_answer_versions (id uuid PRIMARY KEY, assistant_message_id uuid NOT NULL REFERENCES app.qa_messages(id), execution_id uuid NOT NULL REFERENCES app.qa_executions(id), version_no integer NOT NULL, is_current boolean NOT NULL DEFAULT true, created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(assistant_message_id,version_no));
CREATE TABLE app.qa_feedback (id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES app.qa_sessions(id), assistant_message_id uuid NOT NULL REFERENCES app.qa_messages(id), execution_id uuid NOT NULL REFERENCES app.qa_executions(id), reason varchar(30) NOT NULL CHECK(reason IN ('sql_error','result_error','metric_error','answer_error','other')), description varchar(2000), status varchar(20) NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','resolved','ignored')), resolution_note varchar(2000), version integer NOT NULL DEFAULT 1, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE app.favorite_questions (id uuid PRIMARY KEY, owner_id varchar(64) NOT NULL DEFAULT 'demo-user', normalized_question varchar(2000) NOT NULL, display_question varchar(2000) NOT NULL, source_message_id uuid REFERENCES app.qa_messages(id), created_at timestamptz NOT NULL DEFAULT now(), UNIQUE(owner_id,normalized_question));
CREATE TABLE app.application_config (id boolean PRIMARY KEY DEFAULT true CHECK(id), greeting_enabled boolean NOT NULL DEFAULT true, greeting_text varchar(1000) NOT NULL, recommended_questions jsonb NOT NULL DEFAULT '[]', follow_up_enabled boolean NOT NULL DEFAULT true, frequent_questions_enabled boolean NOT NULL DEFAULT true, frequent_question_threshold integer NOT NULL DEFAULT 3, model_qa_enabled boolean NOT NULL DEFAULT true, tts_enabled boolean NOT NULL DEFAULT false, stt_enabled boolean NOT NULL DEFAULT false, default_analysis_year smallint NOT NULL DEFAULT 2026, version integer NOT NULL DEFAULT 1, updated_at timestamptz NOT NULL DEFAULT now());

CREATE INDEX contracts_dims_idx ON mart.contracts(business_unit_id,industry_id,product_line_id,signed_at);
CREATE INDEX revenue_date_idx ON mart.revenue_facts(recognized_at,contract_id);
CREATE INDEX payment_date_idx ON mart.payment_facts(paid_at,contract_id);
CREATE INDEX pipeline_risk_idx ON mart.project_pipeline(overall_risk,stage,business_unit_id);
CREATE INDEX session_owner_updated_idx ON app.qa_sessions(owner_id,pinned DESC,updated_at DESC) WHERE deleted_at IS NULL;
CREATE INDEX execution_created_idx ON app.qa_executions(created_at DESC, status);

CREATE VIEW mart.v_sales_performance AS
WITH revenue_monthly AS (
    SELECT contract_id, date_trunc('month', recognized_at)::date AS business_month, sum(recognized_amount)::numeric(18,2) AS revenue_amount
    FROM mart.revenue_facts GROUP BY contract_id, date_trunc('month', recognized_at)::date
), payment_monthly AS (
    SELECT contract_id, date_trunc('month', paid_at)::date AS business_month, sum(payment_amount)::numeric(18,2) AS payment_amount
    FROM mart.payment_facts GROUP BY contract_id, date_trunc('month', paid_at)::date
), months AS (
    SELECT contract_id, business_month FROM revenue_monthly UNION SELECT contract_id, business_month FROM payment_monthly
), totals AS (
    SELECT c.id AS contract_id, coalesce(sum(r.recognized_amount),0)::numeric(18,2) AS recognized_total FROM mart.contracts c LEFT JOIN mart.revenue_facts r ON r.contract_id=c.id GROUP BY c.id
), paid AS (
    SELECT c.id AS contract_id, coalesce(sum(p.payment_amount),0)::numeric(18,2) AS paid_total FROM mart.contracts c LEFT JOIN mart.payment_facts p ON p.contract_id=c.id GROUP BY c.id
)
SELECT c.id AS contract_id, c.contract_no, c.contract_name, c.signed_at, extract(year from m.business_month)::int AS year,
       m.business_month, bu.code AS business_unit_code, bu.name AS business_unit_name, bu.region,
       i.major_name AS industry_major_name, i.name AS industry_name, pl.code AS product_line_code, pl.name AS product_line_name,
       cu.name AS customer_name, cu.customer_level, cu.customer_category, cu.province,
       c.contract_amount_tax_included, c.contract_amount_tax_excluded,
       coalesce(rm.revenue_amount,0)::numeric(18,2) AS revenue_amount,
       coalesce(pm.payment_amount,0)::numeric(18,2) AS payment_amount,
       t.recognized_total, p.paid_total,
       greatest(c.contract_amount_tax_excluded-t.recognized_total,0)::numeric(18,2) AS unrecognized_amount,
       greatest(c.contract_amount_tax_included-p.paid_total,0)::numeric(18,2) AS unpaid_amount,
       greatest(t.recognized_total*(1+c.tax_rate)-p.paid_total,0)::numeric(18,2) AS receivable_amount,
       c.status, c.is_statistical, c.special_program
FROM months m JOIN mart.contracts c ON c.id=m.contract_id
JOIN mart.business_units bu ON bu.id=c.business_unit_id
LEFT JOIN mart.industries i ON i.id=c.industry_id
JOIN mart.product_lines pl ON pl.id=c.product_line_id
LEFT JOIN mart.customers cu ON cu.id=c.final_customer_id
LEFT JOIN revenue_monthly rm ON rm.contract_id=m.contract_id AND rm.business_month=m.business_month
LEFT JOIN payment_monthly pm ON pm.contract_id=m.contract_id AND pm.business_month=m.business_month
JOIN totals t ON t.contract_id=c.id JOIN paid p ON p.contract_id=c.id
WHERE c.is_statistical AND c.status <> 'cancelled';

CREATE VIEW mart.v_target_achievement AS
SELECT st.year, bu.code AS business_unit_code, bu.name AS business_unit_name, bu.region,
       st.commercial_target_amount, st.solution_target_amount,
       coalesce(sum(r.recognized_amount),0)::numeric(18,2) AS revenue_amount,
       coalesce(sum(r.recognized_amount) FILTER (WHERE pl.name='商业解决方案'),0)::numeric(18,2) AS solution_revenue_amount,
       round(coalesce(sum(r.recognized_amount),0)/nullif(st.commercial_target_amount,0)*100,1) AS achievement_rate,
       round(coalesce(sum(r.recognized_amount) FILTER (WHERE pl.name='商业解决方案'),0)/nullif(st.solution_target_amount,0)*100,1) AS solution_achievement_rate
FROM mart.sales_targets st JOIN mart.business_units bu ON bu.id=st.business_unit_id
LEFT JOIN mart.contracts c ON c.business_unit_id=st.business_unit_id AND c.is_statistical AND c.status <> 'cancelled'
LEFT JOIN mart.product_lines pl ON pl.id=c.product_line_id
LEFT JOIN mart.revenue_facts r ON r.contract_id=c.id AND extract(year from r.recognized_at)=st.year
GROUP BY st.year, bu.code, bu.name, bu.region, st.commercial_target_amount, st.solution_target_amount;

CREATE VIEW mart.v_pipeline_risk AS
SELECT p.id AS project_id, p.opportunity_no, p.project_name, bu.code AS business_unit_code, bu.name AS business_unit_name,
       i.name AS industry_name, pl.name AS product_line_name, p.stage, p.competition_risk, p.signing_risk,
       p.delivery_risk, p.overall_risk, p.expected_landing_date, p.amount_tax_excluded,
       p.production_scheduled, p.progress_note
FROM mart.project_pipeline p JOIN mart.business_units bu ON bu.id=p.business_unit_id
LEFT JOIN mart.industries i ON i.id=p.industry_id LEFT JOIN mart.product_lines pl ON pl.id=p.product_line_id;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='app_rw') THEN
        GRANT USAGE ON SCHEMA app, mart TO app_rw;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_rw;
        GRANT SELECT ON ALL TABLES IN SCHEMA mart TO app_rw;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='text2sql_ro') THEN
        GRANT USAGE ON SCHEMA mart TO text2sql_ro;
        REVOKE ALL ON SCHEMA app FROM text2sql_ro;
        GRANT SELECT ON mart.v_sales_performance, mart.v_target_achievement, mart.v_pipeline_risk TO text2sql_ro;
    END IF;
END $$;
"""


def upgrade() -> None:
    op.execute(DDL)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS app CASCADE; DROP SCHEMA IF EXISTS mart CASCADE;")
