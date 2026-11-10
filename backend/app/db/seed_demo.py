"""
Demo data for local development: users for every role, monthly budgets and
twelve months of realistic expenses.

    python -m app.db.seed_demo            # refuses if expenses already exist
    python -m app.db.seed_demo --force    # add demo data anyway

All demo accounts use the password printed at the end. Never run in production.
"""
import asyncio
import random
import sys
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.init_db import seed_reference_data
from app.db.session import AsyncSessionLocal
from app.models.models import (
    Budget, Category, Department, Expense, ExpenseEvent, ExpenseStatus, Role, User, UserRole,
)
from app.services.dates import add_months, month_start
from app.services.receipt_storage import DEMO_PREFIX, ReceiptStorage

DEMO_PASSWORD = "Demo1234!"
SAMPLE_RECEIPT = f"{DEMO_PREFIX}sample-receipt.pdf"
SAMPLE_PDF = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 300 200]/Contents 4 0 R"
    b"/Resources<</Font<</F1<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>>>>>>>endobj\n"
    b"4 0 obj<</Length 52>>stream\nBT /F1 18 Tf 60 100 Td (Sample demo receipt) Tj ET\nendstream endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)

USERS = [
    # email, name, roles, department
    ("admin@finai.demo", "Sandaru Admin", ["SYSTEM_ADMIN", "FINANCE_ADMIN"], None),
    ("finance@finai.demo", "Nimali Fernando", ["FINANCE_ADMIN"], "Operations"),
    ("manager@finai.demo", "Ruwan Jayasuriya", ["MANAGER"], "Sales"),
    ("eng.manager@finai.demo", "Kasun Perera", ["MANAGER"], "Engineering"),
    ("priya@finai.demo", "Priya Nair", ["EMPLOYEE"], "Sales"),
    ("amal@finai.demo", "Amal Silva", ["EMPLOYEE"], "Marketing"),
    ("dinuka@finai.demo", "Dinuka Rajapaksa", ["EMPLOYEE"], "Engineering"),
]

BUDGETS = {"Engineering": 11000, "Sales": 8000, "Marketing": 7000, "Operations": 4000}

# category -> (merchants, min, max)
CATALOGUE = {
    "Travel": (["Delta Air Lines", "SriLankan Airlines", "Hilton Colombo", "Uber", "PickMe"], 25, 1400),
    "Software": (["AWS", "Figma", "Slack", "GitHub", "Atlassian", "Google Workspace"], 40, 5000),
    "Meals": (["Ministry of Crab", "Café Kumbuk", "Barefoot Café", "Upali's"], 15, 300),
    "Office": (["Staples", "IKEA", "Abans", "Singer"], 20, 900),
    "Marketing": (["Google Ads", "LinkedIn Ads", "Meta Ads", "Canva"], 100, 3500),
    "Utilities": (["Dialog Axiata", "SLT Mobitel", "CEB"], 60, 450),
}
DEPT_CATEGORIES = {
    "Engineering": ["Software", "Software", "Travel", "Meals", "Office"],
    "Sales": ["Travel", "Travel", "Meals", "Meals", "Office"],
    "Marketing": ["Marketing", "Marketing", "Software", "Meals", "Travel"],
    "Operations": ["Utilities", "Office", "Software", "Utilities", "Meals"],
}


async def seed(force: bool = False) -> None:
    if settings.is_production:
        sys.exit("Refusing to seed demo data in production.")

    rng = random.Random(42)
    async with AsyncSessionLocal() as session:
        await seed_reference_data(session)

        if not force and (await session.execute(select(func.count(Expense.id)))).scalar_one():
            sys.exit("Expenses already exist — re-run with --force to add demo data anyway.")

        depts = {d.name: d for d in (await session.execute(select(Department))).scalars()}
        cats = {c.name: c for c in (await session.execute(select(Category))).scalars()}
        roles = {r.name: r for r in (await session.execute(select(Role))).scalars()}

        # Shared sample receipt (never deleted — see ReceiptStorage.delete)
        sample = ReceiptStorage().root / SAMPLE_RECEIPT
        sample.parent.mkdir(parents=True, exist_ok=True)
        sample.write_bytes(SAMPLE_PDF)

        # ── Users ─────────────────────────────────────────────────────────────
        pw_hash = hash_password(DEMO_PASSWORD)
        users: dict[str, User] = {}
        for email, name, role_names, dept in USERS:
            user = (await session.execute(select(User).where(User.email == email))).unique().scalar_one_or_none()
            if not user:
                user = User(email=email, full_name=name, password_hash=pw_hash,
                            department_id=depts[dept].id if dept else None)
                session.add(user)
                await session.flush()
                for r in role_names:
                    session.add(UserRole(user_id=user.id, role_id=roles[r].id))
            users[email] = user
        await session.flush()

        # ── Budgets: last 12 months + current ────────────────────────────────
        today = date.today()
        for i in range(-11, 1):
            m = add_months(today, i)
            for dept, limit in BUDGETS.items():
                exists = (await session.execute(
                    select(Budget.id).where(Budget.department_id == depts[dept].id, Budget.month == m)
                )).scalar_one_or_none()
                if not exists:
                    session.add(Budget(department_id=depts[dept].id, month=m, amount_limit=Decimal(limit)))

        # ── Expenses ──────────────────────────────────────────────────────────
        submitters = [u for e, u in users.items() if not e.startswith("admin")]
        reviewers = {
            "Sales": users["manager@finai.demo"],
            "Engineering": users["eng.manager@finai.demo"],
        }
        finance = users["finance@finai.demo"]
        now = datetime.now(timezone.utc)
        start = month_start(add_months(today, -11))
        day = start
        count = 0
        while day <= today:
            for _ in range(rng.choice([0, 1, 1, 2, 2, 3])):
                submitter = rng.choice(submitters)
                dept_name = next(d for d, dep in depts.items() if dep.id == submitter.department_id) \
                    if submitter.department_id else "Operations"
                cat_name = rng.choice(DEPT_CATEGORIES[dept_name])
                merchants, lo, hi = CATALOGUE[cat_name]
                amount = Decimal(str(round(rng.uniform(lo, hi) * rng.choice([0.4, 0.7, 1, 1]), 2)))
                age = (today - day).days

                # Older expenses are settled; recent ones are a mix
                if age > 14:
                    status = rng.choices(
                        [ExpenseStatus.APPROVED, ExpenseStatus.REJECTED], weights=[92, 8])[0]
                else:
                    status = rng.choices(
                        [ExpenseStatus.PENDING, ExpenseStatus.APPROVED, ExpenseStatus.DRAFT, ExpenseStatus.REJECTED],
                        weights=[45, 35, 12, 8])[0]

                submitted_at = min(
                    datetime.combine(day, time(9), tzinfo=timezone.utc) + timedelta(hours=rng.randint(0, 48)),
                    now - timedelta(minutes=5),
                )
                reviewer = reviewers.get(dept_name, finance)
                if reviewer.id == submitter.id:
                    reviewer = finance if finance.id != submitter.id else users["admin@finai.demo"]
                e = Expense(
                    merchant=rng.choice(merchants),
                    amount=amount,
                    expense_date=day,
                    category_id=cats[cat_name].id,
                    department_id=depts[dept_name].id,
                    submitted_by_id=submitter.id,
                    status=status,
                    submitted_at=None if status == ExpenseStatus.DRAFT else submitted_at,
                    notes=None,
                )
                # Most expenses have a receipt; demo rows share one sample PDF
                if rng.random() < 0.85 and status != ExpenseStatus.DRAFT:
                    e.receipt_path = SAMPLE_RECEIPT
                    e.receipt_filename = f"{e.merchant.lower().replace(' ', '-')}-receipt.pdf"
                    e.receipt_content_type = "application/pdf"
                    e.receipt_size = len(SAMPLE_PDF)
                if status in (ExpenseStatus.APPROVED, ExpenseStatus.REJECTED):
                    e.reviewed_by_id = reviewer.id
                    e.reviewed_at = min(submitted_at + timedelta(days=rng.randint(1, 4)), now)
                    if status == ExpenseStatus.REJECTED:
                        e.rejection_reason = rng.choice([
                            "Missing itemised receipt", "Not a business expense", "Exceeds per-diem policy",
                        ])
                session.add(e)
                await session.flush()
                session.add(ExpenseEvent(expense_id=e.id, actor_id=submitter.id,
                                         action="created" if status == ExpenseStatus.DRAFT else "submitted",
                                         to_status="draft" if status == ExpenseStatus.DRAFT else "pending",
                                         created_at=submitted_at))
                if e.reviewed_by_id:
                    session.add(ExpenseEvent(expense_id=e.id, actor_id=e.reviewed_by_id,
                                             action=status.value, from_status="pending", to_status=status.value,
                                             comment=e.rejection_reason, created_at=e.reviewed_at))
                count += 1
            day += timedelta(days=1)

        await session.commit()

    print(f"Seeded {len(USERS)} users, {len(BUDGETS) * 12} budgets and {count} expenses.")
    print(f"Sign in with any of these (password: {DEMO_PASSWORD}):")
    for email, name, role_names, dept in USERS:
        print(f"  {email:<26} {', '.join(role_names):<28} {dept or '-'}")


if __name__ == "__main__":
    asyncio.run(seed(force="--force" in sys.argv))
