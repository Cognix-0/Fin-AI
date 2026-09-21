# System Architecture

## 1. Architecture Goal

Build a scalable AI-powered enterprise finance management platform.

The architecture must allow future integration of:

- AI services
- OCR services
- Machine learning models
- Financial analytics
- Notification services
- Background workers
- Object storage
- Monitoring
- CI/CD
- Containerization
- Kubernetes

The initial implementation should therefore establish a clean foundation
without implementing all future features.

---

# 2. High-Level Architecture

The target architecture is:

User
  |
  v
Frontend
  |
  v
Backend API
  |
  +--------------------+
  |                    |
  v                    v
Authentication       Application Services
                         |
                         v
                     PostgreSQL

Future:

Application Services
  |
  +--> AI Service
  +--> OCR Service
  +--> Analytics Service
  +--> Notification Service
  +--> Background Workers

Infrastructure:

GitHub
   |
   v
CI/CD
   |
   v
Docker
   |
   v
Container Registry
   |
   v
Deployment Platform / Kubernetes

---

# 3. Frontend

Recommended technology:

- Next.js
- TypeScript
- Tailwind CSS
- React
- React Hook Form
- Zod

The frontend must be responsive.

Use reusable components.

Suggested structure:

src/
├── app/
│   ├── page.tsx
│   ├── login/
│   ├── register/
│   ├── forgot-password/
│   └── reset-password/
│
├── components/
│   ├── ui/
│   ├── auth/
│   └── layout/
│
├── lib/
│   ├── api/
│   ├── auth/
│   └── validation/
│
├── hooks/
├── types/
└── middleware.ts

---

# 4. Backend

Use a REST API architecture.

Recommended:

- FastAPI
- Python
- Pydantic
- SQLAlchemy
- PostgreSQL

Suggested structure:

backend/
├── app/
│   ├── main.py
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   └── middleware/
│
├── tests/
├── requirements.txt
└── Dockerfile

Keep business logic out of route handlers.

Use:

Router
  ↓
Service
  ↓
Repository
  ↓
Database

---

# 5. Database

Use PostgreSQL.

Initial entities:

User
Role
UserRole
RefreshToken
PasswordResetToken

Future entities:

Company
Department
Expense
ExpenseItem
Receipt
Approval
Budget
Category
FinancialTransaction
Notification
AIAnalysis
AuditLog

Do not implement all future entities during the authentication phase.

---

# 6. Authentication

Authentication must support:

- Registration
- Login
- Logout
- Password hashing
- Password reset
- Session/token management
- Protected routes
- Role information

Passwords must NEVER be stored as plaintext.

Use a secure password hashing algorithm.

Authentication should be designed so that it can later support:

- Email/password
- Google OAuth
- Microsoft OAuth
- Company SSO

Do not implement OAuth unless explicitly requested.

---

# 7. Authorization

Use role-based access control.

Roles:

EMPLOYEE
MANAGER
FINANCE_ADMIN
SYSTEM_ADMIN

Authorization should be implemented as reusable middleware/dependencies.

Example:

User
 |
 +--> Role
       |
       +--> Permission

Do not hardcode authorization logic throughout the application.

---

# 8. Initial Pages

Create:

/

Landing page

/login

Login page

/register

Registration page

/forgot-password

Forgot password page

/reset-password

Reset password page

/profile

Basic authenticated user profile

/dashboard

Protected placeholder dashboard.

The dashboard should only contain a simple authenticated-user
placeholder. Do not implement financial analytics yet.

---

# 9. Login Flow

Expected flow:

User
 ↓
Login page
 ↓
Validate input
 ↓
POST /auth/login
 ↓
Backend validates credentials
 ↓
Authentication token/session
 ↓
Return authenticated user
 ↓
Frontend stores authentication state
 ↓
Redirect to /dashboard

Invalid credentials:

Login page
 ↓
Display clear error
 ↓
Allow retry

---

# 10. Registration Flow

User
 ↓
Registration page
 ↓
Validate fields
 ↓
POST /auth/register
 ↓
Validate email uniqueness
 ↓
Hash password
 ↓
Create user
 ↓
Assign default EMPLOYEE role
 ↓
Login / redirect

Default new users must NOT become ADMIN users.

---

# 11. Security Requirements

Implement:

- Password hashing
- Input validation
- Authentication checks
- Authorization checks
- Secure cookies/token handling
- CORS configuration
- Environment variables
- No secrets committed to Git
- Error handling
- Rate limiting should be considered for future implementation

Never expose:

- Password hashes
- Authentication secrets
- Database credentials
- API keys

---

# 12. Environment Variables

Use environment variables.

Example:

DATABASE_URL=
JWT_SECRET=
JWT_EXPIRE_MINUTES=
NEXT_PUBLIC_API_URL=

Never hardcode credentials.

Provide:

.env.example

but never commit:

.env

---

# 13. API Structure

Initial endpoints:

POST /api/v1/auth/register

POST /api/v1/auth/login

POST /api/v1/auth/logout

POST /api/v1/auth/forgot-password

POST /api/v1/auth/reset-password

GET /api/v1/auth/me

GET /api/v1/users/me

Future:

POST /api/v1/expenses
GET /api/v1/expenses
PUT /api/v1/expenses/{id}
DELETE /api/v1/expenses/{id}

---

# 14. Error Handling

Use consistent API responses.

Success:

{
  "success": true,
  "data": {}
}

Error:

{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password"
  }
}

Do not expose internal exceptions to users.

---

# 15. Future AI Architecture

Do not implement now.

The future architecture should allow:

Frontend
   |
Backend API
   |
AI Service
   |
+-----------------------+
|                       |
OCR                  LLM
|                       |
+-----------+-----------+
            |
      Expense Data
            |
            v
       PostgreSQL

AI responsibilities:

- Receipt extraction
- Expense categorization
- Anomaly detection
- Financial insights
- Forecasting
- Natural-language financial queries

---

# 16. DevOps Architecture

The project must eventually support:

GitHub
   ↓
GitHub Actions
   ↓
Lint
   ↓
Unit Tests
   ↓
Integration Tests
   ↓
Security Scan
   ↓
Docker Build
   ↓
Container Registry
   ↓
Deployment

Future infrastructure:

Frontend Container
Backend Container
AI Service Container
PostgreSQL
Redis
Worker
Monitoring

Potential monitoring:

Prometheus
Grafana

---

# 17. Development Rule

Work incrementally.

PHASE 1:
Project foundation + authentication.

PHASE 2:
User profile + company/department structure.

PHASE 3:
Expense creation and receipt upload.

PHASE 4:
OCR + AI extraction.

PHASE 5:
Approval workflow.

PHASE 6:
Financial analytics.

PHASE 7:
AI insights + anomaly detection.

PHASE 8:
DevOps automation, monitoring and deployment.

Never implement future phases unless requested.