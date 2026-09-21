from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin


class BusinessUnit(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "business_units"
    __table_args__ = {"schema": "mart"}
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    region: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Industry(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "industries"
    __table_args__ = (UniqueConstraint("major_name", "name"), {"schema": "mart"})
    code: Mapped[str] = mapped_column(String(32), unique=True)
    major_name: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(100))


class ProductLine(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "product_lines"
    __table_args__ = {"schema": "mart"}
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Customer(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "customers"
    __table_args__ = {"schema": "mart"}
    name: Mapped[str] = mapped_column(String(200), unique=True)
    customer_level: Mapped[str | None] = mapped_column(String(30))
    customer_category: Mapped[str | None] = mapped_column(String(50))
    province: Mapped[str | None] = mapped_column(String(50))


class Contract(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "contracts"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="quantity_nonnegative"),
        CheckConstraint("tax_rate >= 0", name="tax_rate_nonnegative"),
        CheckConstraint("contract_amount_tax_included >= 0", name="tax_included_nonnegative"),
        CheckConstraint("contract_amount_tax_excluded >= 0", name="tax_excluded_nonnegative"),
        CheckConstraint("status IN ('active','cancelled','completed')", name="valid_status"),
        {"schema": "mart"},
    )
    contract_no: Mapped[str] = mapped_column(String(64), unique=True)
    opportunity_no: Mapped[str | None] = mapped_column(String(64))
    contract_name: Mapped[str] = mapped_column(String(200))
    signed_at: Mapped[date] = mapped_column(Date)
    seller_name: Mapped[str] = mapped_column(String(200))
    buyer_name: Mapped[str | None] = mapped_column(String(200))
    final_customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("mart.customers.id"))
    business_unit_id: Mapped[UUID] = mapped_column(ForeignKey("mart.business_units.id"))
    industry_id: Mapped[UUID | None] = mapped_column(ForeignKey("mart.industries.id"))
    product_line_id: Mapped[UUID] = mapped_column(ForeignKey("mart.product_lines.id"))
    product_model: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int | None] = mapped_column(Integer)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))
    contract_amount_tax_included: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    contract_amount_tax_excluded: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(30))
    is_statistical: Mapped[bool] = mapped_column(Boolean, default=True)
    special_program: Mapped[str | None] = mapped_column(String(100))


class RevenueFact(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "revenue_facts"
    __table_args__ = (
        CheckConstraint("recognized_amount >= 0", name="amount_nonnegative"),
        {"schema": "mart"},
    )
    contract_id: Mapped[UUID] = mapped_column(ForeignKey("mart.contracts.id"))
    recognized_at: Mapped[date] = mapped_column(Date)
    recognized_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    source_type: Mapped[str] = mapped_column(String(30))


class PaymentFact(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "payment_facts"
    __table_args__ = (
        CheckConstraint("payment_amount >= 0", name="amount_nonnegative"),
        {"schema": "mart"},
    )
    contract_id: Mapped[UUID] = mapped_column(ForeignKey("mart.contracts.id"))
    paid_at: Mapped[date] = mapped_column(Date)
    payment_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class SalesTarget(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "sales_targets"
    __table_args__ = (
        UniqueConstraint("business_unit_id", "year"),
        CheckConstraint("year BETWEEN 2000 AND 2100", name="valid_year"),
        {"schema": "mart"},
    )
    business_unit_id: Mapped[UUID] = mapped_column(ForeignKey("mart.business_units.id"))
    year: Mapped[int] = mapped_column(SmallInteger)
    commercial_target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    solution_target_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))


class ProjectPipeline(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "project_pipeline"
    __table_args__ = {"schema": "mart"}
    contract_id: Mapped[UUID | None] = mapped_column(ForeignKey("mart.contracts.id"))
    opportunity_no: Mapped[str] = mapped_column(String(64), unique=True)
    project_name: Mapped[str] = mapped_column(String(200))
    business_unit_id: Mapped[UUID] = mapped_column(ForeignKey("mart.business_units.id"))
    industry_id: Mapped[UUID | None] = mapped_column(ForeignKey("mart.industries.id"))
    product_line_id: Mapped[UUID | None] = mapped_column(ForeignKey("mart.product_lines.id"))
    stage: Mapped[str] = mapped_column(String(30))
    competition_risk: Mapped[str | None] = mapped_column(String(10))
    signing_risk: Mapped[str | None] = mapped_column(String(10))
    delivery_risk: Mapped[str | None] = mapped_column(String(10))
    overall_risk: Mapped[str | None] = mapped_column(String(10))
    expected_landing_date: Mapped[date | None] = mapped_column(Date)
    amount_tax_excluded: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    production_scheduled: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_note: Mapped[str | None] = mapped_column(Text)
