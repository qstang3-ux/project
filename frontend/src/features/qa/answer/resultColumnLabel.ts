import type { ResultColumn } from '../../../api/types';

const resultColumnLabels: Readonly<Record<string, string>> = {
  year: '年度',
  business_month: '月份',
  business_unit_code: '经营单元编码',
  business_unit_name: '经营单元',
  region: '区域',
  product_line_code: '产品线编码',
  product_line_name: '产品线',
  industry_major_name: '行业大类',
  industry_name: '行业',
  contract_no: '合同编号',
  contract_name: '合同名称',
  customer_name: '客户名称',
  customer_level: '客户级别',
  customer_category: '客户类型',
  province: '省份',
  opportunity_no: '商机编号',
  project_name: '项目名称',
  stage: '项目阶段',
  overall_risk: '综合风险',
  expected_landing_date: '预计落地日期',
  revenue_amount: '收入额',
  prior_year_revenue: '上年同期收入',
  yoy_change_amount: '同比增量',
  yoy_growth_rate: '同比增长率',
  payment_amount: '回款额',
  receivable_amount: '应收金额',
  unpaid_amount: '未回款金额',
  commercial_target_amount: '商业目标',
  solution_target_amount: '商解目标',
  solution_revenue_amount: '商解收入额',
  achievement_rate: '目标完成率',
  solution_achievement_rate: '商解完成率',
  contract_amount_tax_included: '含税合同额',
  contract_amount_tax_excluded: '不含税合同额',
};

export function getResultColumnLabel(column: ResultColumn) {
  const label = column.label.trim();
  if (label && label !== column.key) return label;
  return resultColumnLabels[column.key.trim().toLowerCase()] ?? (label || column.key);
}
