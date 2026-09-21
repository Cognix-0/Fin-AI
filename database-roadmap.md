# Database Roadmap — AI-Powered Company Finance Management System

## 1. Objective

Design a secure, normalized PostgreSQL database that can support:

- Users
- Roles
- Companies
- Departments
- Expenses
- Receipts
- Approvals
- Budgets
- Financial analytics
- AI analysis
- Notifications
- Audit logs

The database should support future multi-tenant operation.

## 2. Recommended Database

PostgreSQL.

Use:

- UUID primary keys
- Foreign keys
- Appropriate indexes
- Constraints
- Transactions
- Database migrations with Alembic

Do not rely only on application validation for important data integrity rules.

## 3. Phase 1 — Authentication Tables

Start with:

```text
users
roles
user_roles
password_reset_tokens
sessions / refresh_tokens
```

### users

Suggested fields:

```text
id
email
password_hash
full_name
is_active
created_at
updated_at
```

Requirements:

- Unique email
- Normalized email handling
- Never store plaintext passwords
- Timestamps

### roles

```text
id
name
description
```

Initial roles:

```text
EMPLOYEE
MANAGER
FINANCE_ADMIN
SYSTEM_ADMIN
```

### user_roles

```text
user_id
role_id
```

Use foreign keys and uniqueness constraints.

## 4. Phase 2 — Organization

Future tables:

```text
companies
departments
company_memberships
```

A company should own its financial data.

Example relationship:

```text
Company
  |
  +-- Departments
  |
  +-- Users
  |
  +-- Expenses
  |
  +-- Budgets
```

Design tenant ownership explicitly before implementing company-wide analytics.

## 5. Phase 3 — Expense Domain

Future tables:

```text
expenses
expense_items
expense_categories
receipts
```

Example:

```text
User
 |
 +--> Expense
        |
        +--> Receipt
        |
        +--> Expense Items
        |
        +--> Category
```

Important expense fields may include:

```text
id
company_id
department_id
user_id
category_id
amount
currency
merchant_name
expense_date
description
status
created_at
updated_at
```

## 6. Phase 4 — Approval Domain

Future:

```text
expense_approvals
```

Track:

- Expense
- Reviewer
- Action
- Comment
- Timestamp

Possible state:

```text
SUBMITTED
    ↓
UNDER_REVIEW
    ↓
APPROVED
```

or:

```text
UNDER_REVIEW
    ↓
REJECTED
```

Do not delete approval history when an expense changes status.

## 7. Phase 5 — Receipt Storage Metadata

Do not store large receipt images directly in normal relational rows.

Store files in object storage and keep metadata in PostgreSQL.

Example:

```text
receipts
--------
id
expense_id
storage_key
file_name
mime_type
file_size
uploaded_by
created_at
```

The database stores the reference; object storage stores the actual file.

## 8. Phase 6 — AI Analysis

Future:

```text
ai_extractions
ai_analysis_results
```

Store:

- Source document
- Extraction result
- Model/provider
- Model version
- Confidence where applicable
- Processing status
- Created timestamp

AI results should not silently overwrite the original user-submitted financial data.

## 9. Phase 7 — Budgets

Future:

```text
budgets
budget_allocations
```

Support:

- Company budgets
- Department budgets
- Category budgets
- Time periods

Example:

```text
Budget
  ↓
Department
  ↓
Category
  ↓
Period
  ↓
Amount
```

## 10. Phase 8 — Notifications

Future:

```text
notifications
notification_preferences
```

Support:

- Approval notifications
- Budget alerts
- Anomaly alerts
- System notifications

## 11. Phase 9 — Audit Logs

Future:

```text
audit_logs
```

Record:

```text
id
actor_user_id
company_id
action
entity_type
entity_id
old_values
new_values
ip_address
user_agent
created_at
```

Avoid storing unnecessary sensitive information.

## 12. Data Integrity

Use:

- NOT NULL where appropriate
- UNIQUE constraints
- CHECK constraints
- Foreign keys
- ON DELETE behavior deliberately selected
- Transactions for multi-step financial operations

Examples:

```text
amount > 0
currency is valid
email is unique
role references existing role
expense references existing company
```

## 13. Indexing Strategy

Index fields frequently used for:

- Authentication
- Company filtering
- User filtering
- Date filtering
- Expense status
- Expense category
- Approval queries

Examples:

```text
users(email)

expenses(company_id, expense_date)

expenses(company_id, status)

expenses(user_id, created_at)
```

Do not add indexes blindly. Validate query patterns first.

## 14. Migrations

Use Alembic.

Rules:

- Every schema change gets a migration
- Never manually modify production schema
- Test migrations on a clean database
- Test upgrade
- Test downgrade where appropriate
- Keep migrations in Git

## 15. Backup and Recovery

Production planning should include:

- Automated backups
- Point-in-time recovery where supported
- Backup retention policy
- Restore testing

A backup that has never been restored should not be assumed reliable.

## 16. Database Security

- Least-privilege database users
- No database password in source code
- TLS for production database connections
- Restricted network access
- Separate development/test/production credentials
- Sensitive fields minimized
- Audit access to sensitive financial data

## 17. Database Testing

Test:

- Constraints
- Foreign keys
- Unique email
- Role relationships
- Tenant isolation
- Expense lifecycle
- Approval history
- Migration correctness

## 18. Database Quality Gate

Before moving to the next phase:

- Schema is normalized appropriately
- Foreign keys are correct
- Constraints work
- Migrations work from an empty database
- Authentication queries are indexed
- Tenant boundaries are defined
- Backup strategy is documented
- Test data is separated from production data
