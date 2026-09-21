# 数据字典 v1.0

## mart.business_units

| 字段 | 类型 | 含义 |
|---|---|---|
| id | uuid | 主键 |
| code | varchar(32) | 稳定编码，唯一 |
| name | varchar(100) | 经营单元名称 |
| region | varchar(50) | 所属区域 |
| active | boolean | 是否有效 |

## mart.industries

| 字段 | 类型 | 含义 |
|---|---|---|
| id | uuid | 主键 |
| code | varchar(32) | 行业编码 |
| major_name | varchar(100) | 行业大类 |
| name | varchar(100) | 行业名称 |

## mart.product_lines

| 字段 | 类型 | 含义 |
|---|---|---|
| id | uuid | 主键 |
| code | varchar(32) | 产品线编码 |
| name | varchar(100) | 通用计算/智能计算/商业解决方案 |

## mart.customers

| 字段 | 类型 | 含义 |
|---|---|---|
| id | uuid | 主键 |
| name | varchar(200) | 客户全称 |
| customer_level | varchar(30) | 客户级别 |
| customer_category | varchar(50) | 客户分类 |
| province | varchar(50) | 所在省份 |

## mart.contracts

| 字段 | 类型 | 含义 |
|---|---|---|
| id | uuid | 主键 |
| contract_no | varchar(64) | 合同编号，唯一 |
| opportunity_no | varchar(64) | 商机/预销售编号 |
| contract_name | varchar(200) | 合同名称 |
| signed_at | date | 签订日期 |
| seller_name | varchar(200) | 卖方/签约主体 |
| buyer_name | varchar(200) | 买方 |
| final_customer_id | uuid | 最终客户 |
| business_unit_id | uuid | 业绩经营单元 |
| industry_id | uuid | 行业 |
| product_line_id | uuid | 产品线 |
| product_model | varchar(100) | 产品型号 |
| quantity | integer | 台套数 |
| tax_rate | numeric(6,4) | 税率，如0.13 |
| contract_amount_tax_included | numeric(18,2) | 含税金额（元） |
| contract_amount_tax_excluded | numeric(18,2) | 不含税金额（元） |
| status | varchar(30) | active/cancelled/completed |
| is_statistical | boolean | 是否纳入统计 |
| special_program | varchar(100) | 专项标签 |

## mart.revenue_facts / mart.payment_facts

| 表 | 字段 | 含义 |
|---|---|---|
| revenue_facts | contract_id | 合同 |
| revenue_facts | recognized_at | 收入确认日期 |
| revenue_facts | recognized_amount | 不含税收入（元） |
| revenue_facts | source_type | PO/发货/POD/交付服务 |
| payment_facts | contract_id | 合同 |
| payment_facts | paid_at | 回款日期 |
| payment_facts | payment_amount | 回款金额（元） |

## mart.sales_targets

| 字段 | 类型 | 含义 |
|---|---|---|
| business_unit_id | uuid | 经营单元 |
| year | smallint | 年度 |
| commercial_target_amount | numeric(18,2) | 商业目标（元） |
| solution_target_amount | numeric(18,2) | 商解目标（元） |

## mart.project_pipeline

| 字段 | 类型 | 含义 |
|---|---|---|
| contract_id | uuid | 可空；已签约时关联合同 |
| opportunity_no | varchar(64) | 商机编号 |
| project_name | varchar(200) | 项目名称 |
| stage | varchar(30) | 商机/方案/投标/商务/签约/交付 |
| competition_risk | varchar(10) | 低/中/高 |
| signing_risk | varchar(10) | 低/中/高 |
| delivery_risk | varchar(10) | 低/中/高 |
| overall_risk | varchar(10) | 三类风险最高值 |
| expected_landing_date | date | 预计落地日期 |
| amount_tax_excluded | numeric(18,2) | 预计不含税金额 |
| production_scheduled | boolean | 是否排产 |
| progress_note | text | 进展及风险说明 |

## app 核心表

| 表 | 关键字段 |
|---|---|
| qa_sessions | id,title,pinned,parent_session_id,updated_at,deleted_at |
| qa_messages | id,session_id,role,content,source_message_id,created_at |
| qa_executions | id,user_message_id,status,intent,normalized_question,missing_slots,clarification_round,clarification_json,context_message_ids,context_provenance,model_config_id,generate_chart,lease_owner,lease_expires_at,heartbeat_at,run_attempt,event_sequence_floor,sql_text,row_count,duration_ms,error_code,regenerated_from_execution_id |
| qa_execution_effects | execution_id,effect_key,node_name,attempt,status,payload_json,error_code,owner_id,started_at,completed_at,updated_at |
| qa_execution_events | execution_id,sequence,kind,status,summary,data_json,dedupe_key,created_at |
| idempotency_records | idempotency_key,operation,resource_id,request_fingerprint,session_id,user_message_id,execution_id,created_at |
| qa_execution_steps | execution_id,step_type,status,summary,started_at,completed_at |
| qa_answer_versions | assistant_message_id,execution_id,version_no,is_current |
| qa_feedback | assistant_message_id,execution_id,reason,description,status,resolution_note,version |
| favorite_questions | normalized_question,display_question |
| model_configs | name,provider,base_url,model_name,encrypted_api_key,active,timeout_seconds |
| application_config | greeting_text,recommended_questions,能力开关,常问阈值,version |
| data_sources | name,description,enabled,is_default,data_as_of,allowed_objects |

## 枚举

- 产品线：通用计算、智能计算、商业解决方案。
- 风险：低风险、中风险、高风险。
- 反馈原因：sql_error、result_error、metric_error、answer_error、other。
- 反馈状态：pending、processing、resolved、ignored。
- 执行状态：queued、running、awaiting_input、completed、failed、cancelled、rejected。
- 执行事件：execution.started、clarification.required、schema.selected、sql.generated、sql.validated、
  query.completed、answer.completed、execution.completed、execution.failed、execution.cancelled。
