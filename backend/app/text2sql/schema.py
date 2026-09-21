from app.text2sql.types import SchemaContext

SCHEMA_DESCRIPTIONS = {
    "mart.v_sales_performance": (
        "合同月度经营表现视图。精确字段：contract_id uuid，contract_no text，"
        "contract_name text，signed_at date，year integer，business_month date（月初日期，"
        "必须用 DATE 范围比较，不能按整数月份比较），business_unit_code text，"
        "business_unit_name text，region text，industry_major_name text，industry_name text，"
        "product_line_code text，product_line_name text，customer_name text，customer_level text，"
        "customer_category text，province text，contract_amount_tax_included numeric，"
        "contract_amount_tax_excluded numeric，revenue_amount numeric，payment_amount numeric，"
        "recognized_total numeric，paid_total numeric，unrecognized_amount numeric，"
        "unpaid_amount numeric，receivable_amount numeric，status text，is_statistical boolean，"
        "special_program text。视图不包含 recognized_at、operating_unit_name 或 month 数字字段。"
    ),
    "mart.v_target_achievement": (
        "年度经营单元目标达成视图。精确字段：year integer，business_unit_code text，"
        "business_unit_name text，region text，commercial_target_amount numeric，"
        "solution_target_amount numeric，revenue_amount numeric，solution_revenue_amount numeric，"
        "achievement_rate numeric（已是百分数，例如 69.5 表示 69.5%），"
        "solution_achievement_rate numeric。视图不包含 operating_unit_name。"
    ),
    "mart.v_pipeline_risk": (
        "项目风险视图。精确字段：project_id uuid，opportunity_no text，project_name text，"
        "business_unit_code text，business_unit_name text，industry_name text，"
        "product_line_name text，stage text，competition_risk text，signing_risk text，"
        "delivery_risk text，overall_risk text，expected_landing_date date，"
        "amount_tax_excluded numeric，production_scheduled boolean，progress_note text。"
        "风险枚举是中文：低、中、高；高风险必须筛选 overall_risk='高'。"
    ),
}


class SchemaRetriever:
    def retrieve(self, question: str, allowed_objects: list[str]) -> SchemaContext:
        lowered = question.lower()
        ranked: list[str] = []
        if any(word in lowered for word in ("目标", "完成率", "达成", "商解")):
            ranked.append("mart.v_target_achievement")
        if any(word in lowered for word in ("风险", "项目阶段", "排产", "ppl")):
            ranked.append("mart.v_pipeline_risk")
        if any(
            word in lowered
            for word in ("收入", "回款", "合同", "客户", "行业", "产品线", "应收", "销售额")
        ):
            ranked.append("mart.v_sales_performance")
        ranked.extend(obj for obj in allowed_objects if obj not in ranked)
        selected = tuple(obj for obj in ranked if obj in allowed_objects)[:3]
        return SchemaContext(selected, {obj: SCHEMA_DESCRIPTIONS[obj] for obj in selected})
