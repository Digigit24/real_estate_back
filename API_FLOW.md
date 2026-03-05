# Real Estate CRM — API Flow Documentation

> **For:** Backend team & Frontend developers
> **Purpose:** Understand how APIs connect and the correct order to call them

---

## Authentication

Every API (except Broker Portal) requires a **JWT token** in the header:
```
Authorization: Bearer <token>
```

Login via: `POST /auth/token-login/`  → returns `access` + `refresh` tokens.

---

## Core Flow: Lead → Booking → Payment

This is the main business flow:

```
Lead Created
    ↓
Lead moves through Pipeline Stages (Statuses)
    ↓
Lead is assigned a Unit (Inventory)
    ↓
Booking is created (Lead + Unit combined)
    ↓
Payment Milestones auto-generated
    ↓
Milestones marked as Paid → Payments recorded
    ↓
Demand Letter / Receipt PDFs generated
```

---

## Module-by-Module API Flow

---

### 1. Tenant Settings (do this FIRST)
**Base:** `GET/PUT /api/tenant/settings/`

Setup company info, logo, payment plans. This data is used in PDF generation.

---

### 2. Inventory Setup (one-time setup)

```
POST /api/inventory/projects/       → Create a Project (e.g. "Green Valley")
    ↓
POST /api/inventory/towers/         → Create Tower under project (tower_id links to project)
    ↓
POST /api/inventory/units/          → Create Units under tower (unit_id links to tower)
```

**Key fields:**
- Unit has `status`: `available | booked | sold`
- Unit status auto-changes to `booked` when a Booking is created

---

### 3. CRM — Lead Pipeline

**Setup pipeline stages first:**
```
GET  /api/crm/statuses/             → List all pipeline stages
POST /api/crm/statuses/             → Create stage (e.g. New, Interested, Site Visit, Booked)
```

**Lead lifecycle:**
```
POST /api/crm/leads/                → Create a lead (name, phone, source, budget, etc.)
    ↓
PATCH /api/crm/leads/{id}/          → Update lead (move to next status stage)
    ↓
POST /api/crm/activities/           → Log activity on lead (call, meeting, note)
    ↓
GET  /api/crm/leads/{id}/           → View lead detail with full history
```

---

### 4. Meetings & Tasks (linked to Lead)

```
POST /api/meetings/                 → Schedule a site visit or meeting (linked to lead_id)
POST /api/tasks/                    → Create a follow-up task (linked to lead_id)
GET  /api/meetings/?lead={id}       → See all meetings for a lead
GET  /api/tasks/?lead={id}          → See all tasks for a lead
```

---

### 5. Bookings (the conversion step)

> A booking is created when a Lead decides to buy a Unit.

```
POST /api/bookings/
    → Required: lead_id, unit_id, booking_date, total_amount, payment_plan_type
    → payment_plan_type: "20_80" | "construction_linked" | "custom"
    ↓
Auto happens on backend:
    - Unit status → "booked"
    - Payment milestones auto-generated based on plan type
    - If lead has a broker → Commission auto-created
```

**After booking is created:**
```
GET  /api/bookings/{id}/                        → Full booking detail
GET  /api/bookings/{id}/milestones/             → List payment milestones with due dates
GET  /api/bookings/summary/                     → Summary stats
GET  /api/bookings/upcoming-payments/           → Upcoming due milestones
```

---

### 6. Payments — Mark Milestones as Paid

```
POST /api/bookings/{id}/milestones/{milestone_id}/mark-paid/
    → Body: {
        "received_amount": 500000,       ← required: actual amount received
        "received_date": "2025-03-01",   ← required: date payment was received
        "reference_no": "NEFT/123456",   ← optional: bank/cheque reference
        "notes": "Received via NEFT"     ← optional: any remarks
      }
    ↓
Milestone status → "PAID" (or "PARTIALLY_PAID" if received_amount < milestone amount)
```

---

### 7. PDF Data APIs (for document generation)

Frontend generates PDFs using these data endpoints:

```
GET /api/bookings/{id}/demand-letter-data/
    → Returns: builder info, buyer info, unit info, payment schedule
    → Use to render a Demand Letter PDF

GET /api/bookings/{id}/milestones/{milestone_id}/receipt-data/
    → Returns: receipt number, paid amount, buyer, unit, date
    → Use to render a Payment Receipt PDF
```

> Builder/company info in these PDFs comes from Tenant Settings.

---

### 8. Brokers

**Builder side (JWT auth):**
```
GET  /api/brokers/brokers/          → List brokers
POST /api/brokers/brokers/          → Add a broker (set commission_rate %)
GET  /api/brokers/commissions/      → View all commissions
```

**Broker Portal (BrokerToken — separate from JWT):**
```
POST /api/brokers/portal/register/      → Broker self-registers
POST /api/brokers/portal/login/         → Returns BrokerToken
GET  /api/brokers/portal/me/            → Broker profile
POST /api/brokers/portal/submit-lead/   → Broker submits a new lead
GET  /api/brokers/portal/my-leads/      → Broker sees their submitted leads
GET  /api/brokers/portal/my-commissions/ → Broker sees their earnings
```

---

### 9. Analytics (read-only dashboards)

```
GET /api/analytics/overview/            → Total leads, bookings, revenue KPIs
GET /api/analytics/inventory/           → Unit availability stats
GET /api/analytics/sales-funnel/        → Lead conversion funnel
GET /api/analytics/revenue/             → Revenue over time
GET /api/analytics/agent-leaderboard/   → Top performing agents
GET /api/analytics/lead-sources/        → ROI by lead source
```

---

## Full Frontend Call Order (First Time Setup)

```
1.  POST /auth/token-login/                                       → get JWT
2.  GET/PUT /api/tenant/settings/                                 → setup company info
3.  POST /api/inventory/projects/                                 → add project
4.  POST /api/inventory/towers/                                   → add towers
5.  POST /api/inventory/units/                                    → add units
6.  POST /api/crm/statuses/                                       → setup pipeline stages
7.  POST /api/crm/leads/                                          → start adding leads
8.  POST /api/meetings/ or /api/tasks/                            → follow up on leads
9.  POST /api/bookings/                                           → convert lead to booking
10. POST /api/bookings/{id}/milestones/{mid}/mark-paid/           → record payment
11. GET  /api/bookings/{id}/demand-letter-data/                   → generate demand letter PDF
12. GET  /api/bookings/{id}/milestones/{mid}/receipt-data/        → generate receipt PDF
```

---

## Error Reference

| Status | Meaning |
|--------|---------|
| `400` | Wrong request body — check field names |
| `401` | Missing or expired JWT token |
| `403` | No permission for this resource |
| `404` | Wrong ID — record doesn't exist |
| `409` | Conflict — e.g. Unit already booked |

---

## Swagger (Interactive Docs)
Full API with try-it-out: `http://your-server/api/docs/`
Download OpenAPI schema: `GET /api/schema/`
