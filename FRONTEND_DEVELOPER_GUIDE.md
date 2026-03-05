# Frontend Developer Guide — Real Estate Builder CRM
> Backend: Django REST Framework | Version: Phase 1–4 complete (WhatsApp: Phase 2, pending)

---

## ⚠️ Recent API Changes (March 2026)

### 1. Commission response now includes `lead_name`
`GET /api/brokers/commissions/` and `GET /api/brokers/brokers/{id}/commissions/` now return both `lead_id` **and** `lead_name` in every commission object.

**Before:**
```json
{ "lead_id": 5, ... }
```
**Now:**
```json
{ "lead_id": 5, "lead_name": "Rahul Sharma", ... }
```
No change needed on your POST/PATCH calls — `lead_name` is read-only and auto-resolved.

---

### 2. Mark-Milestone-Paid field names (important — do not use old names)

The correct request body for `POST /api/bookings/{id}/milestones/{mid}/mark-paid/` is:

```json
{
  "received_amount": 1000000,
  "received_date": "2026-04-08",
  "reference_no": "NEFT/20260408/123456",
  "notes": "Received via NEFT"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `received_amount` | decimal | **Yes** | Actual amount received |
| `received_date` | date `YYYY-MM-DD` | **Yes** | Date payment was received |
| `reference_no` | string | No | Bank/cheque/UTR reference number |
| `notes` | string | No | Any remarks |

> If `received_amount` < milestone `amount`, status becomes `PARTIALLY_PAID`. If equal or greater, status becomes `PAID`.

---

---

## Table of Contents
1. [Setup & Auth](#1-setup--auth)
2. [First Login Flow](#2-first-login-flow)
3. [API Base Structure](#3-api-base-structure)
4. [Module 1 — Inventory](#4-module-1--inventory)
5. [Module 2 — CRM / Leads](#5-module-2--crm--leads)
6. [Module 3 — Tasks & Meetings](#6-module-3--tasks--meetings)
7. [Module 4 — Bookings & Payments](#7-module-4--bookings--payments)
8. [Module 5 — Brokers / Channel Partners](#8-module-5--brokers--channel-partners)
9. [Module 6 — Analytics / Dashboard](#9-module-6--analytics--dashboard)
10. [Module 7 — Tenant Settings & White-label](#10-module-7--tenant-settings--white-label)
11. [Module 8 — Payments (ad-hoc)](#11-module-8--payments-ad-hoc)
12. [Broker Portal (Separate App)](#12-broker-portal-separate-app)
13. [PDF Generation Flow](#13-pdf-generation-flow)
14. [Common Patterns](#14-common-patterns)
15. [All Enums Reference](#15-all-enums-reference)
16. [Real-world Flows](#16-real-world-flows)
17. [What to Build (Migrations to Run)](#17-what-to-build-migrations-to-run)

---

## 1. Setup & Auth

### Headers — Required on every request
```js
{
  "Authorization": "Bearer <jwt_token>",   // from SuperAdmin login
  "X-Tenant-ID": "<tenant_uuid>",          // builder's tenant UUID
  "Content-Type": "application/json"
}
```

### Base URL
```
https://yourdomain.com
```

### API Docs (Swagger)
```
GET /api/docs/         → Swagger UI (interactive)
GET /api/redoc/        → ReDoc
GET /api/schema/       → OpenAPI JSON schema
```

### Admin Login (for testing)
```
POST /auth/token-login/
Body: { "token": "<admin_jwt>" }
```

### Health Check
```
GET /auth/health/   → { "status": "ok" }
```

---

## 2. First Login Flow

When a new builder (tenant) logs in for the first time:

```js
// Step 1: Check if pipeline stages exist
const stages = await GET('/api/crm/statuses/')
// { count: 0, results: [] }

// Step 2: If empty, auto-seed the 12 default RE pipeline stages
if (stages.count === 0) {
  await POST('/api/crm/statuses/initialize-defaults/')
  // Returns { created: true, stages: [...12 stages] }
}

// Step 3: Load tenant branding/settings
await GET('/api/tenant/settings/')
// Auto-creates default settings if none exist
```

**The `initialize-defaults` endpoint is idempotent** — calling it multiple times is safe. If stages already exist, it returns `{ created: false }` and does nothing.

---

## 3. API Base Structure

### Pagination
All list endpoints return:
```json
{
  "count": 100,
  "next": "https://domain.com/api/crm/leads/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

### Filtering
Most list endpoints support:
- `?field=value` — exact filter
- `?field__gte=value` — greater than or equal
- `?field__lte=value` — less than or equal
- `?field__icontains=value` — case-insensitive contains
- `?search=text` — full-text search across searchable fields
- `?ordering=-created_at` — sort (prefix `-` for descending)
- `?page=2&page_size=50` — pagination

### Error Format
```json
{ "error": "Human readable message" }
// or field-level:
{ "phone": ["This field is required."], "name": ["This field is required."] }
```

---

## 4. Module 1 — Inventory

### 4.1 Projects

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/inventory/projects/` | List all projects |
| POST | `/api/inventory/projects/` | Create project |
| GET | `/api/inventory/projects/{id}/` | Project detail |
| PATCH | `/api/inventory/projects/{id}/` | Update project |
| DELETE | `/api/inventory/projects/{id}/` | Delete project |
| GET | `/api/inventory/projects/{id}/inventory-summary/` | Unit counts by status |

**Create Project:**
```json
POST /api/inventory/projects/
{
  "name": "Sunrise Heights",
  "rera_number": "MH/01/2025/12345",
  "description": "Premium 2 & 3 BHK apartments",
  "location": "Wakad, Pune",
  "address": "Survey No. 123, Wakad",
  "city": "Pune",
  "state": "Maharashtra",
  "pincode": "411057",
  "google_maps_url": "https://maps.google.com/?q=...",
  "total_units": 240,
  "launch_date": "2025-01-15",
  "possession_date": "2028-06-30",
  "logo_url": "https://cdn.example.com/logo.png",
  "banner_url": "https://cdn.example.com/banner.jpg"
}
```

**Inventory Summary Response:**
```json
{
  "project_id": 1,
  "project_name": "Sunrise Heights",
  "total": 240,
  "available": 120,
  "reserved": 15,
  "booked": 80,
  "registered": 10,
  "sold": 15,
  "blocked": 0
}
```

---

### 4.2 Towers

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/inventory/towers/?project={id}` | List towers (filter by project) |
| POST | `/api/inventory/towers/` | Create tower |
| GET/PATCH/DELETE | `/api/inventory/towers/{id}/` | CRUD |
| GET | `/api/inventory/towers/{id}/unit-grid/` | **Floor × flat grid** |

**Create Tower:**
```json
POST /api/inventory/towers/
{
  "project": 1,
  "name": "Tower A",
  "total_floors": 20,
  "units_per_floor": 4,
  "description": "East-facing tower"
}
```

**Unit Grid Response** (use this to build the visual floor plan):
```json
{
  "tower_id": 1,
  "tower_name": "Tower A",
  "grid": [
    {
      "floor_number": 20,
      "units": [
        {
          "id": 45,
          "unit_number": "A-2001",
          "floor_number": 20,
          "bhk_type": "2BHK",
          "carpet_area": "850.00",
          "facing": "EAST",
          "total_price": "9500000.00",
          "status": "AVAILABLE",
          "reserved_for_lead_id": null
        }
      ]
    }
    // ... floors from top to bottom
  ]
}
```

**Status color coding for unit grid:**
```js
const STATUS_COLORS = {
  AVAILABLE:  '#22C55E',  // green
  RESERVED:   '#F59E0B',  // yellow
  BOOKED:     '#3B82F6',  // blue
  REGISTERED: '#8B5CF6',  // purple
  SOLD:       '#6B7280',  // grey
  BLOCKED:    '#EF4444',  // red
}
```

---

### 4.3 Units

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/inventory/units/` | List units |
| POST | `/api/inventory/units/` | Create unit |
| GET/PATCH/DELETE | `/api/inventory/units/{id}/` | CRUD |
| POST | `/api/inventory/units/{id}/reserve/` | Reserve for a lead |
| POST | `/api/inventory/units/{id}/release/` | Release reservation |
| POST | `/api/inventory/units/{id}/update-status/` | Admin force-update status |
| POST | `/api/inventory/units/price-calculator/` | Calculate total price |
| GET | `/api/inventory/units/suggest/?lead_id=5` | Suggest units for a lead |

**Filters:** `?tower=1&status=AVAILABLE&bhk_type=2BHK&floor_number__gte=5&base_price__lte=10000000`

**Create Unit:**
```json
POST /api/inventory/units/
{
  "tower": 1,
  "unit_number": "A-0501",
  "floor_number": 5,
  "bhk_type": "2BHK",
  "carpet_area": "850.50",
  "built_up_area": "1050.00",
  "super_built_up_area": "1200.00",
  "facing": "EAST",
  "base_price": "8500000",
  "floor_rise_premium": "50000",
  "facing_premium": "100000",
  "parking_charges": "200000",
  "other_charges": "50000"
}
```

**Reserve Unit:**
```json
POST /api/inventory/units/{id}/reserve/
{ "lead_id": 5 }
```

**Price Calculator:**
```json
POST /api/inventory/units/price-calculator/
{
  "base_price": "8500000",
  "floor_rise_premium": "50000",
  "facing_premium": "100000",
  "parking_charges": "200000",
  "other_charges": "50000"
}
// Response: { ..., "total_price": "8900000.00" }
```

**Suggest Units for Lead:**
```
GET /api/inventory/units/suggest/?lead_id=5&project_id=1
// Matches available units to lead's budget_min/max and bhk_preference
```

---

## 5. Module 2 — CRM / Leads

### 5.1 Pipeline Stages

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/crm/statuses/` | List all stages |
| POST | `/api/crm/statuses/` | Create a stage |
| GET/PATCH/DELETE | `/api/crm/statuses/{id}/` | CRUD |
| **POST** | **`/api/crm/statuses/initialize-defaults/`** | **Auto-seed 12 default RE stages** |

**Create Stage:**
```json
POST /api/crm/statuses/
{
  "name": "Token Paid",
  "order_index": 7,
  "color_hex": "#10B981",
  "is_won": false,
  "is_lost": false
}
```

**Default stages seeded (in order):**
1. Inquiry (#94A3B8)
2. Qualified (#60A5FA)
3. Site Visit Scheduled (#FBBF24)
4. Site Visit Done (#F97316)
5. Shortlisted Unit (#A78BFA)
6. Negotiation (#EC4899)
7. Token Paid (#10B981)
8. Agreement (#059669)
9. Registered (#047857)
10. Closed / Won ✅ (#16A34A) — `is_won: true`
11. Lost ❌ (#EF4444) — `is_lost: true`
12. Not Interested ❌ (#6B7280) — `is_lost: true`

---

### 5.2 Leads

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/crm/leads/` | List leads |
| POST | `/api/crm/leads/` | Create lead |
| GET/PATCH/DELETE | `/api/crm/leads/{id}/` | CRUD |
| GET | `/api/crm/leads/kanban/` | Kanban view grouped by stage |
| GET | `/api/crm/leads/export/` | Export CSV/Excel |
| POST | `/api/crm/leads/import-leads/` | Import from CSV/Excel |
| POST | `/api/crm/leads/bulk-delete/` | Bulk delete |
| POST | `/api/crm/leads/bulk-status-update/` | Move multiple leads |

**Filters:** `?status=5&priority=HIGH&re_source=WALK_IN&assigned_to=<uuid>&search=Rahul`

**Create / Update Lead — Full RE Fields:**
```json
POST /api/crm/leads/
{
  "name": "Rahul Sharma",
  "phone": "9876543210",
  "email": "rahul@gmail.com",
  "priority": "HIGH",
  "re_source": "WALK_IN",
  "budget_min": "8000000",
  "budget_max": "10000000",
  "bhk_preference": "2BHK",
  "preferred_localities": ["Wakad", "Baner"],
  "preferred_project_id": 1,
  "shortlisted_unit_id": 45,
  "broker_id": 3,
  "site_visit_date": "2026-03-10T10:00:00Z",
  "token_amount": "100000",
  "status": 2,
  "assigned_to": "uuid-of-agent",
  "next_follow_up_at": "2026-03-05T09:00:00Z",
  "notes": "Interested in east-facing units"
}
```

**Kanban Response:**
```json
{
  "statuses": [
    {
      "id": 1,
      "name": "Inquiry",
      "color_hex": "#94A3B8",
      "order_index": 1,
      "is_won": false,
      "is_lost": false,
      "lead_count": 12,
      "leads": [ ... ]
    }
  ]
}
```

**Bulk Status Update:**
```json
POST /api/crm/leads/bulk-status-update/
{ "lead_ids": [1, 2, 3], "status_id": 5 }
```

---

### 5.3 Activities

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/crm/activities/?lead={id}` | List activities for a lead |
| POST | `/api/crm/activities/` | Log an activity |
| GET/PATCH/DELETE | `/api/crm/activities/{id}/` | CRUD |

**Log Activity:**
```json
POST /api/crm/activities/
{
  "lead": 5,
  "type": "SITE_VISIT",
  "content": "Rahul visited Tower B, liked unit B-403",
  "happened_at": "2026-03-08T11:00:00Z"
}
```

---

### 5.4 Custom Field Configurations

```
GET /api/crm/field-configurations/         → list custom field definitions
GET /api/crm/field-configurations/field-schema/  → full schema for building dynamic form
```

---

## 6. Module 3 — Tasks & Meetings

### Tasks

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/tasks/?lead={id}` | List tasks |
| POST | `/api/tasks/` | Create task |
| GET/PATCH/DELETE | `/api/tasks/{id}/` | CRUD |

```json
POST /api/tasks/
{
  "lead": 5,
  "title": "Call Rahul for follow-up",
  "description": "Discuss unit B-403 pricing",
  "status": "TODO",
  "priority": "HIGH",
  "due_date": "2026-03-05T10:00:00Z",
  "assignee_user_id": "uuid-of-agent"
}
```

### Meetings

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/meetings/?lead={id}` | List meetings |
| POST | `/api/meetings/` | Schedule meeting |
| GET/PATCH/DELETE | `/api/meetings/{id}/` | CRUD |

```json
POST /api/meetings/
{
  "lead": 5,
  "title": "Site Visit - Rahul",
  "location": "Sunrise Heights, Wakad",
  "start_at": "2026-03-08T10:00:00Z",
  "end_at": "2026-03-08T12:00:00Z"
}
```

---

## 7. Module 4 — Bookings & Payments

### 7.1 Bookings

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/bookings/` | List bookings |
| POST | `/api/bookings/` | **Create booking + auto-generate payment schedule** |
| GET | `/api/bookings/{id}/` | Booking detail with all milestones |
| PATCH | `/api/bookings/{id}/` | Update booking |
| GET | `/api/bookings/{id}/milestones/` | List payment milestones |
| POST | `/api/bookings/{id}/milestones/{mid}/mark-paid/` | Record payment received |
| GET | `/api/bookings/summary/` | Revenue totals |
| GET | `/api/bookings/upcoming-payments/` | Payments due next 30 days |
| GET | `/api/bookings/{id}/demand-letter-data/` | Data for PDF demand letter |
| GET | `/api/bookings/{id}/milestones/{mid}/receipt-data/` | Data for PDF receipt |

**Create Booking (20:80 Plan — auto-generates 3 milestones):**
```json
POST /api/bookings/
{
  "lead": 5,
  "unit": 45,
  "booking_date": "2026-03-10",
  "token_amount": "1000000",
  "total_amount": "9000000",
  "payment_plan_type": "20_80",
  "remarks": "Negotiated at 90L, east-facing B-403"
}
```

**Create Booking (Custom Plan — you supply milestones):**
```json
POST /api/bookings/
{
  "lead": 5,
  "unit": 45,
  "booking_date": "2026-03-10",
  "token_amount": "500000",
  "total_amount": "9000000",
  "payment_plan_type": "CUSTOM",
  "milestones": [
    { "milestone_name": "Token",     "due_date": "2026-03-10", "amount": "500000",  "percentage": "5.56" },
    { "milestone_name": "Agreement", "due_date": "2026-04-10", "amount": "1000000", "percentage": "11.11" },
    { "milestone_name": "Possession","due_date": "2028-06-30", "amount": "7500000", "percentage": "83.33" }
  ]
}
```

> **Auto-triggers on create:**
> 1. Unit status → `BOOKED`
> 2. Payment milestones auto-created
> 3. If `lead.broker_id` is set → Commission record auto-created

**Mark Milestone Paid:**
```json
POST /api/bookings/{id}/milestones/{mid}/mark-paid/
{
  "received_amount": "1000000",
  "received_date": "2026-04-08",
  "reference_no": "NEFT/20260408/123456",
  "notes": "Received via NEFT"
}
```

**Booking Detail Response:**
```json
{
  "id": 1,
  "lead": 5, "lead_name": "Rahul Sharma", "lead_phone": "9876543210",
  "unit": 45, "unit_number": "B-403", "tower_name": "Tower B", "project_name": "Sunrise Heights",
  "booking_date": "2026-03-10",
  "token_amount": "1000000.00",
  "total_amount": "9000000.00",
  "payment_plan_type": "20_80",
  "status": "TOKEN_PAID",
  "total_collected": "1000000.00",
  "total_pending": "8000000.00",
  "milestones": [
    { "id": 1, "milestone_name": "Token Amount",           "due_date": "2026-03-10", "amount": "900000.00",  "percentage": "10.00", "status": "PAID", "received_amount": "1000000.00" },
    { "id": 2, "milestone_name": "Agreement / Booking",    "due_date": "2026-04-09", "amount": "900000.00",  "percentage": "10.00", "status": "PENDING" },
    { "id": 3, "milestone_name": "On Possession",          "due_date": "2028-06-30", "amount": "7200000.00", "percentage": "80.00", "status": "PENDING" }
  ]
}
```

---

### 7.2 Payment Plan Templates (Configurable)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/tenant/payment-plan-templates/` | List templates |
| POST | `/api/tenant/payment-plan-templates/` | Create template |
| GET/PATCH/DELETE | `/api/tenant/payment-plan-templates/{id}/` | CRUD |
| POST | `/api/tenant/payment-plan-templates/{id}/set-default/` | Mark as default |
| POST | `/api/tenant/payment-plan-templates/preview/` | Preview milestone amounts |

**Create Template:**
```json
POST /api/tenant/payment-plan-templates/
{
  "name": "My 30:70 Plan",
  "plan_type": "CUSTOM",
  "stages": [
    { "name": "Token",             "percentage": 10, "days_from_booking": 0 },
    { "name": "Agreement",         "percentage": 20, "days_from_booking": 30 },
    { "name": "On Possession",     "percentage": 70, "days_from_booking": 730 }
  ]
}
// Note: percentages MUST sum to 100
```

**Preview Milestones:**
```json
POST /api/tenant/payment-plan-templates/preview/
{
  "template_id": 1,
  "booking_date": "2026-03-10",
  "total_amount": "9000000"
}
// Returns calculated milestone dates and amounts
```

---

## 8. Module 5 — Brokers / Channel Partners

### Builder-side (JWT auth)

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/brokers/brokers/` | List all brokers |
| POST | `/api/brokers/brokers/` | Add broker |
| GET/PATCH/DELETE | `/api/brokers/brokers/{id}/` | CRUD |
| GET | `/api/brokers/brokers/leaderboard/` | Broker leaderboard |
| GET | `/api/brokers/brokers/{id}/leads/` | Leads by this broker |
| GET | `/api/brokers/brokers/{id}/commissions/` | Commissions for this broker |
| GET | `/api/brokers/commissions/` | All commissions (includes `lead_name`) |
| PATCH | `/api/brokers/commissions/{id}/` | Update commission |
| POST | `/api/brokers/commissions/{id}/mark-paid/` | Mark commission paid |

**Add Broker:**
```json
POST /api/brokers/brokers/
{
  "name": "Vinod Kadam",
  "phone": "9123456789",
  "email": "vinod@brokerage.com",
  "company_name": "Kadam Real Estate",
  "rera_number": "A51800012345",
  "commission_rate": "2.00",
  "city": "Pune",
  "status": "ACTIVE"
}
```

**Leaderboard Response:**
```json
{
  "count": 5,
  "results": [
    { "rank": 1, "broker_id": 3, "name": "Vinod Kadam", "bookings_count": 8, "total_commission": "144000.00", "leads_count": 25 },
    { "rank": 2, ... }
  ]
}
```

**Commission Response — `GET /api/brokers/commissions/`:**
```json
{
  "id": 1,
  "broker": 3,
  "broker_name": "Vinod Kadam",
  "broker_phone": "9123456789",
  "booking": 1,
  "booking_date": "2026-03-10",
  "unit_number": "B-403",
  "project_name": "Sunrise Heights",
  "lead_id": 5,
  "lead_name": "Rahul Sharma",
  "commission_rate": "2.00",
  "commission_amount": "180000.00",
  "status": "PENDING",
  "paid_date": null,
  "notes": null
}
```

> **Auto-commission:** When a booking is created and `lead.broker_id` is set, a `Commission` record is **automatically created** using the broker's `commission_rate`. No manual action needed.

---

## 9. Module 6 — Analytics / Dashboard

All endpoints are `GET`. No request body needed.

| URL | Description | Key Params |
|-----|-------------|------------|
| `/api/analytics/overview/` | Main dashboard summary card | — |
| `/api/analytics/inventory/` | Unit counts by status per project | `?project_id=` |
| `/api/analytics/sales-funnel/` | Leads at each stage + conversion | `?days=30` |
| `/api/analytics/revenue/` | Bookings value, collected, pending + monthly trend | `?project_id=&from_date=&to_date=` |
| `/api/analytics/agent-leaderboard/` | Site visits, bookings, conversion per agent | `?days=30&project_id=` |
| `/api/analytics/lead-sources/` | Lead source ROI | `?days=90` |

**Overview Response:**
```json
{
  "inventory": {
    "total": 240, "available": 120, "reserved": 15,
    "booked": 80, "registered": 10, "sold": 15
  },
  "leads": {
    "total": 450, "new_today": 5, "won": 45, "conversion_rate": 10.0
  },
  "revenue": {
    "total_bookings": 80, "total_value": 72000000,
    "collected": 14400000, "pending": 57600000
  },
  "activity": {
    "site_visits_last_7_days": 12,
    "payments_due_next_7_days": 8
  }
}
```

**Revenue Response (includes 6-month trend):**
```json
{
  "total_bookings": 80,
  "total_value": 72000000,
  "collected": 14400000,
  "pending": 57600000,
  "overdue": 2000000,
  "monthly_trend": [
    { "month": "Oct 2025", "bookings": 10, "value": 9000000 },
    { "month": "Nov 2025", "bookings": 12, "value": 10800000 },
    ...
  ]
}
```

**Agent Leaderboard Response:**
```json
{
  "period_days": 30,
  "count": 5,
  "results": [
    { "rank": 1, "user_id": "uuid", "leads_assigned": 30, "site_visits": 18, "bookings": 8, "conversion_rate": 26.7 }
  ]
}
```

**Lead Source ROI:**
```json
{
  "period_days": 90,
  "results": [
    { "source": "WALK_IN",   "leads": 80, "site_visits": 50, "bookings": 20, "visit_rate": 62.5, "booking_rate": 25.0 },
    { "source": "META_ADS",  "leads": 120, "site_visits": 40, "bookings": 12, "visit_rate": 33.3, "booking_rate": 10.0 },
    { "source": "BROKER",    "leads": 60, "site_visits": 30, "bookings": 15, "visit_rate": 50.0, "booking_rate": 25.0 }
  ]
}
```

---

## 10. Module 7 — Tenant Settings & White-label

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/tenant/settings/` | Get settings (auto-creates if missing) |
| PUT | `/api/tenant/settings/` | Update all settings |
| PATCH | `/api/tenant/settings/` | Partial update |

**Settings Response:**
```json
{
  "tenant_id": "uuid",
  "company_name": "Sunrise Developers",
  "tagline": "Building Your Dreams",
  "logo_url": "https://cdn.example.com/logo.png",
  "favicon_url": "https://cdn.example.com/favicon.ico",
  "primary_color": "#2563EB",
  "secondary_color": "#1E40AF",
  "accent_color": "#10B981",
  "subdomain": "sunrise",
  "custom_domain": "crm.sunrisedevelopers.com",
  "support_email": "support@sunrisedevelopers.com",
  "support_phone": "020-12345678",
  "address": "123 Business Park, Wakad",
  "city": "Pune", "state": "Maharashtra", "pincode": "411057",
  "gstin": "27AAAAA0000A1Z5",
  "pdf_header_text": "Sunrise Developers Pvt. Ltd.",
  "pdf_footer_text": "RERA No: MH/01/2025/12345 | This is a computer generated document",
  "signature_url": "https://cdn.example.com/signature.png"
}
```

**Use primary_color, logo_url, company_name for theming the entire frontend.**

---

## 11. Module 8 — Payments (ad-hoc)

For one-off payments not tied to a booking milestone (e.g., miscellaneous charges).

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/payments/?lead={id}` | List payments |
| POST | `/api/payments/` | Record payment |
| GET/PATCH/DELETE | `/api/payments/{id}/` | CRUD |

```json
POST /api/payments/
{
  "lead": 5,
  "type": "ADVANCE",
  "amount": "50000",
  "currency": "INR",
  "method": "NEFT",
  "reference_no": "TXN123456",
  "date": "2026-03-10T14:00:00Z",
  "status": "CLEARED"
}
```

---

## 12. Broker Portal (Separate App)

The broker portal is a **separate frontend** (or section) for Channel Partners.

**Auth is different:** Uses `BrokerToken` instead of `Bearer JWT`.

```js
// Broker portal request headers:
{
  "Authorization": "BrokerToken <token_from_login>"
}
```

### Broker Auth Flow

```
POST /api/brokers/portal/register/   → register (status = PENDING)
POST /api/brokers/portal/login/      → login → get token
POST /api/brokers/portal/logout/     → invalidate token
GET  /api/brokers/portal/me/         → own profile + stats
```

**Register:**
```json
POST /api/brokers/portal/register/
{
  "tenant_id": "builder-tenant-uuid",
  "name": "Vinod Kadam",
  "phone": "9123456789",
  "email": "vinod@broker.com",
  "password": "SecurePass123",
  "company_name": "Kadam Real Estate",
  "rera_number": "A51800012345",
  "city": "Pune"
}
// Response: { message: "Registration successful. Pending approval.", broker_id: 3 }
```

**Login:**
```json
POST /api/brokers/portal/login/
{
  "tenant_id": "builder-tenant-uuid",
  "phone": "9123456789",
  "password": "SecurePass123"
}
// Response: { token: "abc123...", broker_id: 3, name: "Vinod Kadam", expires_at: "..." }
```

**Broker Portal Endpoints (all need `Authorization: BrokerToken <token>`):**

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/brokers/portal/me/` | Own profile + stats |
| POST | `/api/brokers/portal/submit-lead/` | Submit new buyer lead |
| GET | `/api/brokers/portal/my-leads/` | All leads I submitted |
| GET | `/api/brokers/portal/my-commissions/` | My commission records |

**Submit Lead:**
```json
POST /api/brokers/portal/submit-lead/
{
  "name": "Ramesh Patil",
  "phone": "9999888877",
  "email": "ramesh@gmail.com",
  "budget_min": "7000000",
  "budget_max": "9000000",
  "bhk_preference": "2BHK",
  "preferred_project_id": 1,
  "notes": "Client saw hoarding on highway, interested in Tower A"
}
```

**Broker Me Response:**
```json
{
  "id": 3,
  "name": "Vinod Kadam",
  "phone": "9123456789",
  "company_name": "Kadam Real Estate",
  "commission_rate": "2.00",
  "status": "ACTIVE",
  "stats": {
    "leads_submitted": 15,
    "bookings": 5,
    "total_commission_earned": "900000.00",
    "commission_paid": "450000.00",
    "commission_pending": "450000.00"
  }
}
```

---

## 13. PDF Generation Flow

Backend returns **structured JSON data**. Frontend generates PDFs using **jspdf**.

### Demand Letter
```js
// Step 1: Get data
const data = await GET(`/api/bookings/${bookingId}/demand-letter-data/`)

// Step 2: Generate PDF using jspdf
// data contains:
// - data.buyer (name, phone, email, address)
// - data.unit (unit_number, bhk_type, carpet_area, floor_number)
// - data.project (name, rera_number, location, possession_date)
// - data.booking (total_amount, booking_date, payment_plan_type)
// - data.payment_schedule (array of milestones with due dates and amounts)
// - data.tower (name)
// Use tenant settings for header/footer text, logo, signature
```

### Payment Receipt
```js
// Step 1: Mark milestone as paid first
await POST(`/api/bookings/${bookingId}/milestones/${milestoneId}/mark-paid/`, { ... })

// Step 2: Get receipt data
const data = await GET(`/api/bookings/${bookingId}/milestones/${milestoneId}/receipt-data/`)

// Step 3: Generate PDF
// data contains:
// - data.receipt_number (e.g. "RCP-1-3")
// - data.buyer, data.unit, data.payment (amount received, date, reference no)
```

---

## 14. Common Patterns

### Axios Setup
```js
import axios from 'axios'

const api = axios.create({ baseURL: 'https://yourdomain.com/api' })

api.interceptors.request.use(config => {
  const token = localStorage.getItem('jwt_token')
  const tenantId = localStorage.getItem('tenant_id')
  config.headers['Authorization'] = `Bearer ${token}`
  config.headers['X-Tenant-ID'] = tenantId
  return config
})
```

### Broker Portal Axios Instance
```js
const brokerApi = axios.create({ baseURL: 'https://yourdomain.com/api' })

brokerApi.interceptors.request.use(config => {
  const token = localStorage.getItem('broker_token')
  config.headers['Authorization'] = `BrokerToken ${token}`
  return config
})
```

### Pagination Helper
```js
const fetchAll = async (url) => {
  let results = [], next = url
  while (next) {
    const { data } = await api.get(next)
    results.push(...data.results)
    next = data.next
  }
  return results
}
```

---

## 15. All Enums Reference

### Unit Status
| Value | Label | Color |
|-------|-------|-------|
| `AVAILABLE` | Available | #22C55E (green) |
| `RESERVED` | Reserved | #F59E0B (yellow) |
| `BOOKED` | Booked | #3B82F6 (blue) |
| `REGISTERED` | Registered | #8B5CF6 (purple) |
| `SOLD` | Sold | #6B7280 (grey) |
| `BLOCKED` | Blocked | #EF4444 (red) |

### BHK Types
`STUDIO` `1BHK` `1.5BHK` `2BHK` `2.5BHK` `3BHK` `4BHK` `PENTHOUSE` `VILLA` `PLOT` `COMMERCIAL`

### Facing
`NORTH` `SOUTH` `EAST` `WEST` `NORTH_EAST` `NORTH_WEST` `SOUTH_EAST` `SOUTH_WEST`

### Lead Source (re_source)
| Value | Label |
|-------|-------|
| `BROKER` | Broker / Channel Partner |
| `WEBSITE` | Website |
| `META_ADS` | Meta Ads |
| `GOOGLE_ADS` | Google Ads |
| `WALK_IN` | Walk In |
| `REFERRAL` | Referral |
| `WHATSAPP` | WhatsApp |
| `PHONE` | Phone Enquiry |
| `HOARDING` | Hoarding / Outdoor |
| `OTHER` | Other |

### Priority
`LOW` `MEDIUM` `HIGH`

### Activity Type
`CALL` `EMAIL` `MEETING` `NOTE` `SMS` `SITE_VISIT` `WHATSAPP` `OTHER`

### Booking Status
`DRAFT` → `TOKEN_PAID` → `AGREEMENT_DONE` → `REGISTERED` / `CANCELLED`

### Payment Milestone Status
`PENDING` `PAID` `PARTIALLY_PAID` `OVERDUE` `WAIVED`

### Payment Plan Type
`20_80` `CONSTRUCTION_LINKED` `CUSTOM`

### Task Status
`TODO` `IN_PROGRESS` `DONE` `CANCELLED`

### Broker Status
`PENDING` `ACTIVE` `INACTIVE` `REJECTED`

### Commission Status
`PENDING` `PAID` `CANCELLED`

### Payment Type (ad-hoc)
`INVOICE` `REFUND` `ADVANCE` `OTHER`

### Payment Status (ad-hoc)
`PENDING` `CLEARED` `FAILED` `CANCELLED`

---

## 16. Real-world Flows

### Flow 1 — New Lead to Booking

```
1. Lead comes in (website form / walk-in)
   POST /api/crm/leads/ { name, phone, re_source, budget_min, budget_max, bhk_preference }

2. Agent qualifies lead
   PATCH /api/crm/leads/{id}/ { status: <Qualified stage id>, budget_min, budget_max, bhk_preference }

3. CRM auto-suggests units
   GET /api/inventory/units/suggest/?lead_id=5

4. Agent shortlists a unit
   PATCH /api/crm/leads/{id}/ { shortlisted_unit_id: 45 }

5. Site visit scheduled
   PATCH /api/crm/leads/{id}/ { status: <Site Visit Scheduled id>, site_visit_date: "..." }
   POST /api/meetings/ { lead, title, start_at, end_at, location }

6. Site visit done — mark in activity
   POST /api/crm/activities/ { lead: 5, type: "SITE_VISIT", happened_at: "...", content: "Liked B-403" }
   PATCH /api/crm/leads/{id}/ { status: <Site Visit Done id> }

7. Unit reserved while negotiating
   POST /api/inventory/units/45/reserve/ { lead_id: 5 }
   PATCH /api/crm/leads/{id}/ { status: <Negotiation id> }

8. Deal closed — create booking
   POST /api/bookings/ { lead: 5, unit: 45, total_amount, payment_plan_type: "20_80", ... }
   // Auto: unit → BOOKED, milestones created, commission created if broker lead

9. Lead marked won
   PATCH /api/crm/leads/{id}/ { status: <Closed / Won id> }
```

### Flow 2 — Payment Collection

```
1. View upcoming payments
   GET /api/bookings/upcoming-payments/

2. Buyer makes payment — mark milestone paid
   POST /api/bookings/1/milestones/2/mark-paid/
   { received_amount, received_date, reference_no }

3. Generate receipt PDF
   GET /api/bookings/1/milestones/2/receipt-data/
   → use jspdf to generate PDF on frontend
```

### Flow 3 — Broker Submits a Lead

```
1. Broker logs into portal
   POST /api/brokers/portal/login/ { tenant_id, phone, password }
   → Save token as "BrokerToken"

2. Broker submits lead
   POST /api/brokers/portal/submit-lead/
   { name, phone, bhk_preference, budget_min, budget_max, preferred_project_id }
   // Lead appears in builder's CRM tagged with broker_id

3. Broker tracks their leads
   GET /api/brokers/portal/my-leads/

4. When lead books → commission auto-created
   GET /api/brokers/portal/my-commissions/
```

### Flow 4 — First-time Setup for New Builder

```
1. Auto-seed pipeline stages
   POST /api/crm/statuses/initialize-defaults/

2. Load/create branding settings
   GET /api/tenant/settings/
   PATCH /api/tenant/settings/ { company_name, logo_url, primary_color, ... }

3. Create first project
   POST /api/inventory/projects/ { name, rera_number, city, possession_date, ... }

4. Add towers
   POST /api/inventory/towers/ { project: 1, name: "Tower A", total_floors: 20, units_per_floor: 4 }

5. Add units (or bulk import)
   POST /api/inventory/units/ (repeat per unit)
```

---

## 17. What to Build (Migrations to Run)

### For DevOps / Backend Setup

When deploying, run these migrations in order:

```bash
# Full migration list (run once on a fresh DB)
python manage.py migrate common
python manage.py migrate crm
python manage.py migrate meetings
python manage.py migrate payments
python manage.py migrate tasks
python manage.py migrate integrations
python manage.py migrate inventory
python manage.py migrate bookings
python manage.py migrate brokers
python manage.py migrate tenant_settings

# Or simply:
python manage.py migrate
```

### New Tables Created (from this project)
| Table | App | Purpose |
|-------|-----|---------|
| `projects` | inventory | Real estate projects |
| `towers` | inventory | Towers/phases under projects |
| `units` | inventory | Individual flat/unit records |
| `bookings` | bookings | Formal unit bookings by buyers |
| `payment_milestones` | bookings | Payment installment schedule |
| `brokers` | brokers | Channel partner records |
| `commissions` | brokers | Per-booking commission records |
| `broker_sessions` | brokers | Broker portal login sessions |
| `tenant_settings` | tenant_settings | White-label branding per tenant |
| `payment_plan_templates` | tenant_settings | Configurable payment plans |

### Per-Tenant Seed (run once per new builder)
```bash
# Option A: API call (recommended)
POST /api/crm/statuses/initialize-defaults/

# Option B: Management command
python manage.py seed_re_pipeline --tenant_id <uuid>
```

---

*Last updated: March 2026 | Phase 1–4 implemented | Phase 2 (WhatsApp) pending*
