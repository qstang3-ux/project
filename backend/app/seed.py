import argparse
import random
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid5

from sqlalchemy import Engine, create_engine, text

from app.core.config import get_settings

SEED = 20260915
VERSION = "seed-20260915"
DATA_AS_OF = date(2026, 5, 31)
NAMESPACE = UUID("5ed1e50a-9e0b-4c69-98da-1a3e18ce2026")
UNITS = [
    "北京代表处",
    "上海代表处",
    "浙江代表处",
    "江苏代表处",
    "山东代表处",
    "广东代表处",
    "四川代表处",
    "湖北代表处",
    "湖南代表处",
    "福建代表处",
    "河南代表处",
    "河北代表处",
    "安徽代表处",
    "江西代表处",
    "陕西代表处",
    "辽宁代表处",
    "吉林代表处",
    "黑龙江代表处",
    "重庆代表处",
    "天津代表处",
    "云南代表处",
]
REGIONS = [
    "华北",
    "华东",
    "华东",
    "华东",
    "华北",
    "华南",
    "西南",
    "华中",
    "华中",
    "华南",
    "华中",
    "华北",
    "华东",
    "华东",
    "西北",
    "东北",
    "东北",
    "东北",
    "西南",
    "华北",
    "西南",
]
INDUSTRIES = ["金融", "互联网", "数字政府", "智能制造", "交通", "医疗", "教育", "能源"]
PRODUCTS = [("GC", "通用计算"), ("AI", "智能计算"), ("BS", "商业解决方案")]
TARGETS_2026_WAN = [
    7950,
    7070,
    6460,
    5560,
    4090,
    3900,
    3750,
    3600,
    3450,
    3300,
    3150,
    3000,
    2850,
    2700,
    2550,
    2400,
    2250,
    2100,
    1950,
    1800,
    1650,
]
SOLUTION_2026_WAN = [
    1200,
    980,
    860,
    720,
    650,
    620,
    590,
    560,
    530,
    500,
    470,
    440,
    410,
    380,
    350,
    320,
    290,
    260,
    230,
    200,
    170,
]
RATIOS_2026 = [
    Decimal("1.08"),
    Decimal("1.02"),
    Decimal("0.96"),
    Decimal("0.92"),
    Decimal("0.91"),
    Decimal("0.86"),
    Decimal("0.82"),
    Decimal("0.78"),
    Decimal("0.74"),
    Decimal("0.69"),
    Decimal("0.66"),
    Decimal("0.63"),
    Decimal("0.61"),
    Decimal("0.58"),
    Decimal("0.55"),
    Decimal("0.72"),
    Decimal("0.75"),
    Decimal("0.81"),
    Decimal("0.88"),
    Decimal("0.94"),
    Decimal("1.01"),
]


def stable_id(kind: str, value: str | int) -> UUID:
    return uuid5(NAMESPACE, f"{kind}:{value}")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rows_for_seed() -> dict[str, list[dict[str, object]]]:
    rng = random.Random(SEED)
    now = datetime(2026, 9, 15, tzinfo=UTC)
    units = [
        {
            "id": stable_id("unit", i),
            "code": f"BU{i + 1:02d}",
            "name": name,
            "region": REGIONS[i],
            "created_at": now,
        }
        for i, name in enumerate(UNITS)
    ]
    industries = [
        {
            "id": stable_id("industry", i),
            "code": f"IND{i + 1:02d}",
            "major_name": name,
            "name": name,
            "created_at": now,
        }
        for i, name in enumerate(INDUSTRIES)
    ]
    products = [
        {"id": stable_id("product", code), "code": code, "name": name, "created_at": now}
        for code, name in PRODUCTS
    ]
    provinces = ["北京", "上海", "浙江", "江苏", "山东", "广东", "四川", "湖北", "湖南", "福建"]
    customers = [
        {
            "id": stable_id("customer", i),
            "name": f"演示客户{i + 1:02d}",
            "customer_level": ["战略", "重点", "普通"][i % 3],
            "customer_category": ["直客", "渠道/ISV"][i % 2],
            "province": provinces[i % len(provinces)],
            "created_at": now,
        }
        for i in range(60)
    ]
    targets: list[dict[str, object]] = []
    for i, unit in enumerate(units):
        for year in (2025, 2026):
            commercial_wan = (
                TARGETS_2026_WAN[i] if year == 2026 else int(TARGETS_2026_WAN[i] * 0.91)
            )
            solution_wan = SOLUTION_2026_WAN[i] if year == 2026 else int(SOLUTION_2026_WAN[i] * 0.9)
            targets.append(
                {
                    "id": stable_id("target", f"{i}-{year}"),
                    "business_unit_id": unit["id"],
                    "year": year,
                    "commercial_target_amount": Decimal(commercial_wan) * 10000,
                    "solution_target_amount": Decimal(solution_wan) * 10000,
                    "created_at": now,
                }
            )

    contracts: list[dict[str, object]] = []
    revenues: list[dict[str, object]] = []
    payments: list[dict[str, object]] = []
    for index in range(600):
        year = 2025 if index < 300 else 2026
        year_index = index if year == 2025 else index - 300
        unit_index = year_index % len(units)
        unit_contracts = 15 if unit_index < 6 else 14
        target = Decimal(TARGETS_2026_WAN[unit_index] * 10000)
        if year == 2025:
            target *= Decimal("0.91")
            ratio = Decimal("0.94") + Decimal(str((unit_index % 5) * 0.02))
        else:
            ratio = RATIOS_2026[unit_index]
        revenue_total = money(target * ratio / unit_contracts)
        excluded = money(revenue_total * Decimal(str(rng.uniform(1.08, 1.28))))
        tax_rate = Decimal("0.13")
        included = money(excluded * (Decimal(1) + tax_rate))
        contract_id = stable_id("contract", index)
        signed_month = (year_index % (12 if year == 2025 else 5)) + 1
        signed_day = min(5 + (year_index % 23), 28)
        product = products[index % 3]
        industry = industries[index % len(industries)]
        customer = customers[index % len(customers)]
        contracts.append(
            {
                "id": contract_id,
                "contract_no": f"HT-{year}-{year_index + 1:04d}",
                "opportunity_no": f"OP-{year}-{year_index + 1:04d}",
                "contract_name": f"{customer['name']}{product['name']}项目",
                "signed_at": date(year, signed_month, signed_day),
                "seller_name": "经管之星科技有限公司",
                "buyer_name": customer["name"],
                "final_customer_id": customer["id"],
                "business_unit_id": units[unit_index]["id"],
                "industry_id": industry["id"],
                "product_line_id": product["id"],
                "product_model": f"{product['code']}-{index % 5 + 1}00",
                "quantity": index % 20 + 1,
                "tax_rate": tax_rate,
                "contract_amount_tax_included": included,
                "contract_amount_tax_excluded": excluded,
                "status": "completed" if index % 4 == 0 else "active",
                "is_statistical": True,
                "special_program": "互联网专项" if index % 9 == 0 else None,
                "created_at": now,
            }
        )
        weights = [Decimal("0.28"), Decimal("0.34"), Decimal("0.38")]
        for part, weight in enumerate(weights):
            max_month = 12 if year == 2025 else 5
            month = ((signed_month - 1 + part) % max_month) + 1
            amount = (
                money(revenue_total * weight)
                if part < 2
                else money(
                    revenue_total
                    - money(revenue_total * weights[0])
                    - money(revenue_total * weights[1])
                )
            )
            revenues.append(
                {
                    "id": stable_id("revenue", f"{index}-{part}"),
                    "contract_id": contract_id,
                    "recognized_at": date(year, month, min(10 + part * 7, 28)),
                    "recognized_amount": amount,
                    "source_type": ["PO", "POD", "交付服务"][part],
                    "created_at": now,
                }
            )
        paid_total = money(included * Decimal(str(rng.uniform(0.45, 0.92))))
        first = money(paid_total * Decimal("0.45"))
        for part, amount in enumerate((first, money(paid_total - first))):
            max_month = 12 if year == 2025 else 5
            month = ((signed_month - 1 + part + 1) % max_month) + 1
            payments.append(
                {
                    "id": stable_id("payment", f"{index}-{part}"),
                    "contract_id": contract_id,
                    "paid_at": date(year, month, 20),
                    "payment_amount": amount,
                    "created_at": now,
                }
            )

    stages = ["商机", "方案", "投标", "商务", "签约", "交付"]
    pipeline: list[dict[str, object]] = []
    for i in range(180):
        risks = (
            ("高", "中", "低") if i < 24 else (("中", "低", "低") if i % 3 else ("低", "低", "低"))
        )
        overall = "高" if "高" in risks else ("中" if "中" in risks else "低")
        pipeline.append(
            {
                "id": stable_id("pipeline", i),
                "contract_id": contracts[i]["id"] if i < 90 else None,
                "opportunity_no": f"PPL-2026-{i + 1:04d}",
                "project_name": f"重点项目{i + 1:03d}",
                "business_unit_id": units[i % 21]["id"],
                "industry_id": industries[i % 8]["id"],
                "product_line_id": products[i % 3]["id"],
                "stage": stages[i % 6],
                "competition_risk": risks[0],
                "signing_risk": risks[1],
                "delivery_risk": risks[2],
                "overall_risk": overall,
                "expected_landing_date": date(2026, (i % 7) + 6, min((i % 25) + 1, 28)),
                "amount_tax_excluded": Decimal(800000 + (i % 40) * 125000),
                "production_scheduled": i % 4 != 0,
                "progress_note": "按计划推进" if overall != "高" else "需关注竞争与签约风险",
                "created_at": now,
            }
        )
    revenues[-1]["recognized_at"] = DATA_AS_OF
    return {
        "business_units": units,
        "industries": industries,
        "product_lines": products,
        "customers": customers,
        "sales_targets": targets,
        "contracts": contracts,
        "revenue_facts": revenues,
        "payment_facts": payments,
        "project_pipeline": pipeline,
    }


def seed(engine: Engine, seed_value: int = SEED) -> bool:
    if seed_value != SEED:
        raise ValueError(f"Only documented seed {SEED} is supported")
    rows = rows_for_seed()
    with engine.begin() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM app.seed_versions WHERE version=:version"), {"version": VERSION}
        )
        if exists:
            return False
        order = [
            "business_units",
            "industries",
            "product_lines",
            "customers",
            "sales_targets",
            "contracts",
            "revenue_facts",
            "payment_facts",
            "project_pipeline",
        ]
        for table_name in order:
            data = rows[table_name]
            columns = list(data[0])
            statement = text(
                f"INSERT INTO mart.{table_name} ({','.join(columns)}) VALUES ({','.join(':' + c for c in columns)})"
            )
            conn.execute(statement, data)
        now = datetime(2026, 9, 15, tzinfo=UTC)
        conn.execute(
            text(
                "INSERT INTO app.data_sources(id,name,description,\"group\",enabled,is_default,data_as_of,allowed_objects,created_at,updated_at) VALUES(:id,'经营分析数据','固定演示经营数据','ledger',true,true,:as_of,CAST(:objects AS jsonb),:now,:now)"
            ),
            {
                "id": stable_id("data-source", "default"),
                "as_of": DATA_AS_OF,
                "objects": '["mart.v_sales_performance","mart.v_target_achievement","mart.v_pipeline_risk"]',
                "now": now,
            },
        )
        conn.execute(
            text(
                "INSERT INTO app.application_config(id,greeting_text,recommended_questions,updated_at) VALUES(true,'你好，我是经管之星，请输入经营分析问题。',CAST(:questions AS jsonb),:now)"
            ),
            {
                "questions": '["2026年商业目标最高的5个经营单元","北京代表处2026年1到5月收入趋势","目前有多少高风险项目"]',
                "now": now,
            },
        )
        conn.execute(
            text("INSERT INTO app.seed_versions(version,seed) VALUES(:version,:seed)"),
            {"version": VERSION, "seed": SEED},
        )
    verify(engine)
    return True


def verify(engine: Engine) -> None:
    expected = {
        "business_units": 21,
        "industries": 8,
        "product_lines": 3,
        "customers": 60,
        "sales_targets": 42,
        "contracts": 600,
        "revenue_facts": 1800,
        "payment_facts": 1200,
        "project_pipeline": 180,
    }
    with engine.connect() as conn:
        for table_name, count in expected.items():
            actual = conn.scalar(text(f"SELECT count(*) FROM mart.{table_name}"))
            if actual != count:
                raise RuntimeError(
                    f"Seed verification failed: {table_name}={actual}, expected {count}"
                )
        anchor_rows = conn.execute(
            text(
                "SELECT business_unit_name, commercial_target_amount/10000 FROM mart.v_target_achievement WHERE year=2026 ORDER BY commercial_target_amount DESC LIMIT 5"
            )
        ).all()
        anchors = [(str(row[0]), Decimal(row[1])) for row in anchor_rows]
        expected_anchors = [
            ("北京代表处", Decimal("7950")),
            ("上海代表处", Decimal("7070")),
            ("浙江代表处", Decimal("6460")),
            ("江苏代表处", Decimal("5560")),
            ("山东代表处", Decimal("4090")),
        ]
        if anchors != expected_anchors:
            raise RuntimeError(f"Seed anchor verification failed: {anchors!r}")
        latest = conn.scalar(text("SELECT max(recognized_at) FROM mart.revenue_facts"))
        if latest != DATA_AS_OF:
            raise RuntimeError(f"Data cutoff verification failed: {latest}")
        low = conn.scalar(
            text(
                "SELECT count(*) FROM mart.v_target_achievement WHERE year=2026 AND achievement_rate < 70"
            )
        )
        high = conn.scalar(
            text(
                "SELECT count(*) FROM mart.v_target_achievement WHERE year=2026 AND achievement_rate > 90"
            )
        )
        if (low or 0) < 5 or (high or 0) < 3:
            raise RuntimeError(f"Achievement distribution invalid: low={low}, high={high}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    engine = create_engine(settings.migration_database_url or settings.database_url)
    if args.verify:
        verify(engine)
    else:
        seed(engine, args.seed or SEED)


if __name__ == "__main__":
    main()
