from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

OUTPUT = "/home/user/real_estate_back/Frontend_Blueprint.pdf"

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=1.8*cm, rightMargin=1.8*cm,
    topMargin=2*cm, bottomMargin=2*cm
)

W = A4[0] - 3.6*cm  # usable width

ss = getSampleStyleSheet()

# ── Styles ──────────────────────────────────────────────────────────────────
def sty(name, parent="Normal", **kw):
    s = ParagraphStyle(name, parent=ss[parent], **kw)
    return s

TITLE   = sty("TITLE",   "Title",  fontSize=22, textColor=colors.HexColor("#1a1a2e"),
               spaceAfter=4, alignment=TA_CENTER)
SUB     = sty("SUB",     "Normal", fontSize=11, textColor=colors.HexColor("#555"),
               spaceAfter=14, alignment=TA_CENTER)
H1      = sty("H1",      "Heading1", fontSize=15, textColor=colors.HexColor("#1a1a2e"),
               spaceBefore=16, spaceAfter=6, borderPad=0)
H2      = sty("H2",      "Heading2", fontSize=12, textColor=colors.HexColor("#264653"),
               spaceBefore=12, spaceAfter=4)
H3      = sty("H3",      "Heading3", fontSize=10, textColor=colors.HexColor("#2a9d8f"),
               spaceBefore=8, spaceAfter=3)
BODY    = sty("BODY",    "Normal",  fontSize=9,  leading=14, spaceAfter=4)
CODE    = sty("CODE",    "Normal",  fontSize=8,  leading=12, fontName="Courier",
               backColor=colors.HexColor("#f4f4f4"), textColor=colors.HexColor("#c0392b"),
               leftIndent=8, rightIndent=8, spaceAfter=6, spaceBefore=4,
               borderColor=colors.HexColor("#ddd"), borderWidth=0.5, borderPad=4)
BULLET  = sty("BULLET",  "Normal",  fontSize=9,  leading=14, leftIndent=16,
               firstLineIndent=-10, spaceAfter=2)
BADGE   = sty("BADGE",   "Normal",  fontSize=8,  textColor=colors.HexColor("#e76f51"),
               fontName="Courier-Bold")

def hr(): return HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor("#cccccc"), spaceAfter=6, spaceBefore=6)

def h1(t): return Paragraph(t, H1)
def h2(t): return Paragraph(t, H2)
def h3(t): return Paragraph(t, H3)
def p(t):  return Paragraph(t, BODY)
def code(t): return Paragraph(t.replace(" ", "&nbsp;").replace("\n", "<br/>"), CODE)
def b(t):  return Paragraph(f"• &nbsp;{t}", BULLET)
def sp(n=6): return Spacer(1, n)

PRI = colors.HexColor("#264653")
ACC = colors.HexColor("#2a9d8f")
LGT = colors.HexColor("#e8f4f8")
RED = colors.HexColor("#e76f51")

def tbl(data, col_widths, header=True, stripe=True):
    style = [
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 8),
        ("GRID",        (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("TOPPADDING",  (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0,0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]
    if header:
        style += [
            ("BACKGROUND",  (0, 0), (-1, 0), PRI),
            ("TEXTCOLOR",   (0, 0), (-1, 0), colors.white),
            ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ]
    if stripe:
        for i in range(2, len(data), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), LGT))
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle(style))
    return t

# ── CONTENT ─────────────────────────────────────────────────────────────────
story = []

# Cover
story += [
    sp(30),
    Paragraph("Real Estate Builder CRM", TITLE),
    Paragraph("Frontend Developer Blueprint", SUB),
    Paragraph("Backend Integration Guide &nbsp;·&nbsp; API Reference &nbsp;·&nbsp; Screen Flow",
              sty("s2","Normal",fontSize=9,textColor=colors.HexColor("#888"),alignment=TA_CENTER)),
    sp(8),
    HRFlowable(width="60%", thickness=2, color=ACC, spaceAfter=6, spaceBefore=6),
    Paragraph("Version 1.0 &nbsp;·&nbsp; March 2026",
              sty("s3","Normal",fontSize=9,textColor=colors.HexColor("#aaa"),alignment=TA_CENTER)),
    sp(40),
]

# ── SECTION 1: Overview ──────────────────────────────────────────────────────
story += [hr(), h1("1. Overview"), hr()]
story += [
    p("This document describes the complete frontend implementation plan for the Real Estate Builder CRM. "
      "The backend is a multi-tenant Django REST API. The frontend consists of <b>two separate applications</b>:"),
    sp(4),
    b("<b>Builder Admin Panel</b> — Full CRM for builders/admins (JWT authentication)"),
    b("<b>Broker Portal</b> — Simplified portal for channel partners (Broker Token authentication)"),
    sp(8),
]

apps = [
    ["App", "Users", "Auth Method", "Base URL", "Key Features"],
    ["Builder Admin Panel", "Builder Staff / Admins", "JWT Bearer Token", "localhost:8000", "CRM, Inventory, Bookings, Analytics"],
    ["Broker Portal", "Channel Partners", "Broker Token", "localhost:8000/api/brokers/portal/", "Submit Leads, View Commissions"],
]
story.append(tbl(apps, [3.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 4.5*cm]))
story.append(sp(10))

# ── SECTION 2: Authentication ────────────────────────────────────────────────
story += [hr(), h1("2. Authentication Flow"), hr()]

story += [h2("2.1 Builder Login")]
story += [
    p("Endpoint: <font name='Courier' color='#c0392b'>POST /auth/superadmin-login/</font> &nbsp;(no Authorization header needed)"),
    p("Request body:"),
    code('{ "email": "builder@example.com", "password": "yourpassword" }'),
    p("Success response (200):"),
    code('{\n  "success": true,\n  "access_token": "eyJhbGci...",\n  "redirect_url": "/admin/",\n  "user": {\n    "id": "uuid",\n    "email": "builder@example.com",\n    "tenant_id": "uuid",\n    "tenant_slug": "sunrise",\n    "permissions": { "crm": { "leads": { "view": "all", "create": true } } },\n    "enabled_modules": ["crm"]\n  }\n}'),
    p("Store in localStorage:"),
    code('localStorage.setItem("access_token", data.access_token)\nlocalStorage.setItem("tenant_id", data.user.tenant_id)\nlocalStorage.setItem("permissions", JSON.stringify(data.user.permissions))'),
]

story += [h2("2.2 Every Builder API Call")]
story += [
    p("Every authenticated request must include the Authorization header:"),
    code('headers: { "Authorization": "Bearer " + localStorage.getItem("access_token") }'),
    p("On <b>401 response</b> → clear localStorage → redirect to /login page."),
]

story += [h2("2.3 Broker Login (separate)")]
story += [
    p("Endpoint: <font name='Courier' color='#c0392b'>POST /api/brokers/portal/login/</font>"),
    code('{ "email": "broker@agency.com", "password": "pass" }\n→ Response: { "token": "broker-token-xyz" }'),
    p("Store broker token and send as: <font name='Courier' color='#c0392b'>Authorization: Token &lt;broker_token&gt;</font>"),
]

story += [h2("2.4 Axios Setup (Recommended)")]
story += [
    code('const api = axios.create({ baseURL: "http://localhost:8000" })\napi.interceptors.request.use(config => {\n  const token = localStorage.getItem("access_token")\n  if (token) config.headers["Authorization"] = `Bearer ${token}`\n  return config\n})\napi.interceptors.response.use(res => res, err => {\n  if (err.response?.status === 401) {\n    localStorage.clear()\n    window.location.href = "/login"\n  }\n  return Promise.reject(err)\n})'),
]

# ── SECTION 3: App Structure ──────────────────────────────────────────────────
story += [hr(), h1("3. App Navigation Structure"), hr()]

story += [p("Permission-based sidebar — show/hide items using <b>permissions</b> from login response."), sp(4)]

nav = [
    ["Route", "Menu Label", "Permission Key", "Primary API"],
    ["/dashboard", "Dashboard", "analytics", "GET /api/analytics/overview/"],
    ["/leads", "Leads", "leads", "GET /api/crm/leads/"],
    ["/inventory", "Inventory", "inventory", "GET /api/inventory/projects/"],
    ["/bookings", "Bookings", "bookings", "GET /api/bookings/"],
    ["/brokers", "Brokers", "brokers", "GET /api/brokers/brokers/"],
    ["/payments", "Payments", "payments", "GET /api/payments/"],
    ["/tasks", "Tasks", "tasks", "GET /api/tasks/"],
    ["/meetings", "Meetings", "meetings", "GET /api/meetings/"],
    ["/analytics", "Analytics", "analytics", "GET /api/analytics/overview/"],
    ["/settings", "Settings", "settings", "GET /api/tenant/settings/"],
    ["/integrations", "Integrations", "—", "GET /api/integrations/integrations/"],
]
story.append(tbl(nav, [3*cm, 2.5*cm, 3*cm, 6*cm]))
story.append(sp(8))

story += [p("<b>On app boot:</b> call <font name='Courier' color='#c0392b'>GET /api/tenant/settings/</font> to load brand colors, logo, company name for white-labeling.")]

# ── SECTION 4: Page by Page ───────────────────────────────────────────────────
story += [hr(), h1("4. Page-by-Page Implementation"), hr()]

# Dashboard
story += [h2("4.1 Dashboard — /dashboard")]
story += [
    p("Load on mount — all calls in parallel:"),
    b("<font name='Courier' color='#c0392b'>GET /api/analytics/overview/</font> — Total leads, new leads this week, pipeline value"),
    b("<font name='Courier' color='#c0392b'>GET /api/analytics/inventory/</font> — Available/Booked/Sold unit counts"),
    b("<font name='Courier' color='#c0392b'>GET /api/bookings/upcoming-payments/</font> — Upcoming milestone dues"),
    b("<font name='Courier' color='#c0392b'>GET /api/analytics/lead-sources/</font> — Lead source breakdown"),
    sp(4),
    p("Widgets: 4 stat cards (Leads / Bookings / Revenue / Conversion), Sales Funnel chart, Lead Source pie chart, Upcoming Payments table."),
]

# Leads
story += [h2("4.2 Leads — /leads")]
story += [
    p("<b>Default view: Kanban Board</b>"),
    b("Load columns: <font name='Courier' color='#c0392b'>GET /api/crm/statuses/</font>"),
    b("Load cards: <font name='Courier' color='#c0392b'>GET /api/crm/leads/</font>"),
    b("Drag card to column: <font name='Courier' color='#c0392b'>POST /api/crm/leads/{id}/move-to-status/</font>"),
    b("Reorder within column: <font name='Courier' color='#c0392b'>PATCH /api/crm/orders/{id}/</font>"),
    sp(4),
    p("<b>First-time setup:</b> If statuses list is empty → call <font name='Courier' color='#c0392b'>POST /api/crm/statuses/initialize-defaults/</font> once to seed 12 default pipeline stages."),
    sp(4),
    p("<b>Toolbar actions:</b>"),
]
toolbar = [
    ["Action", "Method + Endpoint"],
    ["+ Add Lead", "POST /api/crm/leads/"],
    ["Import CSV/Excel", "POST /api/crm/leads/import-bulk/  (multipart/form-data)"],
    ["Download Template", "GET /api/crm/leads/import-template/"],
    ["Export Leads", "GET /api/crm/leads/export/"],
    ["Bulk Delete", "POST /api/crm/leads/bulk-delete/  { lead_ids: [...] }"],
    ["Bulk Move Stage", "POST /api/crm/leads/bulk-update-status/"],
    ["Bulk Assign", "POST /api/crm/leads/bulk-assign/"],
]
story.append(tbl(toolbar, [5*cm, 9.5*cm]))
story.append(sp(6))

story += [
    p("<b>Lead Detail Drawer (click any lead card) — Tabs:</b>"),
]
lead_tabs = [
    ["Tab", "API Calls"],
    ["Overview", "GET /api/crm/leads/{id}/  — show all lead fields"],
    ["Activities", "GET /api/crm/activities/?lead={id}  |  POST /api/crm/leads/{id}/add-activity/"],
    ["Tasks", "GET /api/tasks/?lead={id}  |  POST /api/tasks/"],
    ["Meetings", "GET /api/meetings/?lead={id}  |  POST /api/meetings/"],
    ["Payments", "GET /api/payments/?lead={id}  |  POST /api/payments/"],
    ["Bookings", "GET /api/bookings/?lead={id}  |  POST /api/bookings/"],
]
story.append(tbl(lead_tabs, [3*cm, 11.5*cm]))
story.append(sp(8))

# Inventory
story += [h2("4.3 Inventory — /inventory")]
story += [
    p("<b>3-level hierarchy: Projects → Towers → Unit Grid</b>"),
    sp(4),
]
inv = [
    ["Level", "URL", "API", "Action"],
    ["Projects List", "/inventory", "GET /api/inventory/projects/", "View all projects, click to drill down"],
    ["Tower List", "/inventory/:projectId", "GET /api/inventory/towers/?project=ID", "View towers in project"],
    ["Unit Grid", "/inventory/:projectId/:towerId", "GET /api/inventory/towers/{id}/unit-grid/", "Floor × Unit visual grid"],
    ["Inventory Summary", "Widget in project", "GET /api/inventory/projects/{id}/inventory-summary/", "Count by status"],
]
story.append(tbl(inv, [3*cm, 3.5*cm, 5.5*cm, 3.5*cm]))
story.append(sp(4))
story += [
    p("<b>Unit Grid color coding:</b>"),
    b("Green = AVAILABLE"),
    b("Yellow = RESERVED"),
    b("Red = BOOKED / SOLD"),
    b("Grey = BLOCKED"),
    sp(4),
    p("<b>Unit click panel actions:</b>"),
    b("<font name='Courier' color='#c0392b'>POST /api/inventory/units/{id}/reserve/</font> — Reserve for a lead"),
    b("<font name='Courier' color='#c0392b'>POST /api/inventory/units/{id}/release/</font> — Release reservation"),
    b("<font name='Courier' color='#c0392b'>POST /api/inventory/units/price-calculator/</font> — Show total price with premiums"),
    b("<font name='Courier' color='#c0392b'>GET /api/inventory/units/suggest/</font> — Suggest units based on BHK/budget"),
]

# Bookings
story += [h2("4.4 Bookings — /bookings")]
story += [
    p("List view table with columns: Lead, Unit, Total Amount, Status badge, Booking Date."),
    b("Load: <font name='Courier' color='#c0392b'>GET /api/bookings/</font>"),
    b("Summary cards: <font name='Courier' color='#c0392b'>GET /api/bookings/summary/</font>"),
    b("Upcoming dues: <font name='Courier' color='#c0392b'>GET /api/bookings/upcoming-payments/</font>"),
    sp(4),
    p("<b>Booking status flow:</b> DRAFT → TOKEN_PAID → AGREEMENT_DONE → REGISTERED (or CANCELLED)"),
    sp(4),
    p("<b>Booking Detail page — Payment Milestones:</b>"),
    b("Load milestones: <font name='Courier' color='#c0392b'>GET /api/bookings/{id}/milestones/</font>"),
    b("Mark payment received: <font name='Courier' color='#c0392b'>POST /api/bookings/{id}/milestones/{milestoneId}/mark-paid/</font>"),
    b("Demand Letter PDF data: <font name='Courier' color='#c0392b'>GET /api/bookings/{id}/demand-letter-data/</font>"),
    b("Receipt PDF data: <font name='Courier' color='#c0392b'>GET /api/bookings/{id}/milestones/{milestoneId}/receipt-data/</font>"),
]

# Brokers
story += [h2("4.5 Brokers — /brokers (Builder View)")]
story += [
    p("<b>Tab 1: Broker List</b>"),
    b("<font name='Courier' color='#c0392b'>GET /api/brokers/brokers/</font> — Table: Name, Company, RERA, Rate, Status"),
    b("Approve broker: <font name='Courier' color='#c0392b'>PATCH /api/brokers/brokers/{id}/  { status: 'ACTIVE' }</font>"),
    b("Leaderboard: <font name='Courier' color='#c0392b'>GET /api/brokers/brokers/leaderboard/</font>"),
    sp(4),
    p("<b>Tab 2: Commissions</b>"),
    b("<font name='Courier' color='#c0392b'>GET /api/brokers/commissions/</font> — All pending/paid commissions"),
    b("Pay out: <font name='Courier' color='#c0392b'>POST /api/brokers/commissions/{id}/mark-paid/</font>"),
    sp(4),
    p("<b>Broker statuses:</b> PENDING (awaiting approval) → ACTIVE → INACTIVE / REJECTED"),
]

# Payments
story += [h2("4.6 Payments — /payments")]
story += [
    b("<font name='Courier' color='#c0392b'>GET /api/payments/</font> — Filter by type, status, date, lead"),
    b("Types: INVOICE, REFUND, ADVANCE, OTHER"),
    b("Statuses: PENDING, CLEARED, FAILED, CANCELLED"),
    b("Create: <font name='Courier' color='#c0392b'>POST /api/payments/</font>"),
]

# Tasks
story += [h2("4.7 Tasks — /tasks")]
story += [
    b("<font name='Courier' color='#c0392b'>GET /api/tasks/</font> — Kanban or list view"),
    b("Statuses: TODO → IN_PROGRESS → DONE / CANCELLED"),
    b("Priority: LOW, MEDIUM, HIGH"),
    b("Update via drag-drop: <font name='Courier' color='#c0392b'>PATCH /api/tasks/{id}/  { status: 'IN_PROGRESS' }</font>"),
]

# Meetings
story += [h2("4.8 Meetings — /meetings")]
story += [
    b("<font name='Courier' color='#c0392b'>GET /api/meetings/</font> — Calendar view + list view"),
    b("Fields: title, lead, start_at, end_at, location, notes"),
    b("Create: <font name='Courier' color='#c0392b'>POST /api/meetings/</font>"),
]

# Analytics
story += [h2("4.9 Analytics — /analytics")]
ana = [
    ["Tab", "API Endpoint", "Data Shown"],
    ["Overview", "GET /api/analytics/overview/", "Leads count, pipeline value, weekly trends"],
    ["Inventory", "GET /api/analytics/inventory/", "Available/Reserved/Booked/Sold by project"],
    ["Sales Funnel", "GET /api/analytics/sales-funnel/", "Stage-by-stage conversion rates"],
    ["Revenue", "GET /api/analytics/revenue/", "Collected vs pending payments"],
    ["Team", "GET /api/analytics/agent-leaderboard/", "Agent leaderboard by leads/bookings/revenue"],
    ["Lead Sources", "GET /api/analytics/lead-sources/", "Source ROI — which source converts best"],
]
story.append(tbl(ana, [3*cm, 5.5*cm, 6*cm]))
story.append(sp(8))

# Settings
story += [h2("4.10 Settings — /settings")]
settings_tabs = [
    ["Settings Tab", "API"],
    ["Branding (logo, colors, tagline)", "GET/PATCH /api/tenant/settings/"],
    ["Contact Info (email, phone, GSTIN)", "GET/PATCH /api/tenant/settings/"],
    ["PDF Config (header, footer, signature)", "GET/PATCH /api/tenant/settings/"],
    ["Payment Plan Templates", "GET/POST/PATCH/DELETE /api/tenant/payment-plan-templates/"],
    ["Pipeline Stages (CRM columns)", "GET/POST/PATCH/DELETE /api/crm/statuses/"],
    ["Field Configuration (custom fields)", "GET/POST/PATCH /api/crm/field-configurations/"],
]
story.append(tbl(settings_tabs, [6*cm, 8.5*cm]))
story.append(sp(8))

# Integrations
story += [h2("4.11 Integrations — /integrations")]
story += [
    p("Workflow builder (similar to Zapier). Steps to create a workflow:"),
]
integ_steps = [
    ["Step", "Action", "API"],
    ["1", "List available integrations", "GET /api/integrations/integrations/"],
    ["2", "Connect Google Sheets (OAuth)", "POST /api/integrations/connections/initiate_oauth/"],
    ["3", "Create workflow", "POST /api/integrations/workflows/"],
    ["4", "Set trigger (e.g. new row in sheet)", "POST /api/integrations/workflows/{id}/triggers/"],
    ["5", "Set action (e.g. create lead)", "POST /api/integrations/workflows/{id}/actions/"],
    ["6", "Map fields (sheet col → lead field)", "POST /api/integrations/workflows/{wfId}/actions/{aId}/mappings/"],
    ["7", "Activate workflow", "POST /api/integrations/workflows/{id}/toggle/"],
    ["8", "View execution logs", "GET /api/integrations/workflows/{id}/execution-logs/"],
]
story.append(tbl(integ_steps, [1*cm, 5*cm, 8.5*cm]))
story.append(sp(8))

# ── SECTION 5: Broker Portal ──────────────────────────────────────────────────
story += [hr(), h1("5. Broker Portal (Separate App)"), hr()]
story += [
    p("Simple 4-page portal. Uses <b>Broker Token</b> (not JWT). Send as: <font name='Courier' color='#c0392b'>Authorization: Token &lt;broker_token&gt;</font>"),
    sp(4),
]
broker_pages = [
    ["Page / Route", "API", "Notes"],
    ["Register  /broker/register", "POST /api/brokers/portal/register/", "No auth needed. Status = PENDING until builder approves."],
    ["Login  /broker/login", "POST /api/brokers/portal/login/", "No auth needed. Returns { token } — store this."],
    ["Dashboard  /broker/dashboard", "GET /api/brokers/portal/my-leads/  +  my-commissions/", "Show submitted leads & commission summary."],
    ["Submit Lead  /broker/submit-lead", "POST /api/brokers/portal/submit-lead/", "Broker Token required."],
    ["Profile  /broker/profile", "GET /api/brokers/portal/me/", "View own profile details."],
]
story.append(tbl(broker_pages, [4*cm, 5.5*cm, 5*cm]))
story.append(sp(4))
story += [
    p("<b>Important:</b> Builder must approve broker (PENDING → ACTIVE) before they can submit leads."),
]

# ── SECTION 6: All Endpoints Reference ───────────────────────────────────────
story += [hr(), h1("6. Complete API Endpoint Reference"), hr()]

def endpoint_table(title, rows):
    story.append(h3(title))
    headers = [["Method", "Endpoint", "Description"]]
    data = headers + rows
    story.append(tbl(data, [1.8*cm, 7.5*cm, 5.2*cm]))
    story.append(sp(6))

endpoint_table("Authentication (no auth header needed)", [
    ["POST", "/auth/superadmin-login/", "Builder login with email + password"],
    ["POST", "/auth/token-login/", "Login with existing JWT token"],
    ["GET",  "/auth/health/", "Health check"],
    ["POST", "/api/brokers/portal/register/", "Broker self-registration"],
    ["POST", "/api/brokers/portal/login/", "Broker login"],
])

endpoint_table("CRM — Leads  (prefix: /api/crm/)", [
    ["GET",   "leads/", "List all leads (filter by status, source, date)"],
    ["POST",  "leads/", "Create new lead"],
    ["GET",   "leads/{id}/", "Get single lead details"],
    ["PATCH", "leads/{id}/", "Update lead fields"],
    ["DELETE","leads/{id}/", "Delete lead"],
    ["POST",  "leads/{id}/add-activity/", "Add call/note/email/site-visit activity"],
    ["POST",  "leads/{id}/move-to-status/", "Move to different pipeline stage"],
    ["POST",  "leads/bulk-delete/", "Delete multiple leads"],
    ["POST",  "leads/bulk-update-status/", "Move multiple leads to a stage"],
    ["POST",  "leads/bulk-assign/", "Assign multiple leads to a user"],
    ["GET",   "leads/import-template/", "Download CSV/Excel import template"],
    ["POST",  "leads/import-bulk/", "Import leads from CSV/Excel file"],
    ["GET",   "leads/export/", "Export leads to CSV/Excel"],
])

endpoint_table("CRM — Statuses & Activities  (prefix: /api/crm/)", [
    ["GET",  "statuses/", "List pipeline stages (Kanban columns)"],
    ["POST", "statuses/", "Create new stage"],
    ["PATCH","statuses/{id}/", "Rename / reorder stage"],
    ["DELETE","statuses/{id}/", "Delete stage"],
    ["POST", "statuses/initialize-defaults/", "Seed 12 default RE pipeline stages"],
    ["GET",  "activities/", "List all activities"],
    ["POST", "activities/", "Create activity"],
    ["PATCH","activities/{id}/", "Update activity"],
    ["GET",  "field-configurations/", "List dynamic field config"],
    ["POST", "field-configurations/", "Add custom field"],
    ["PATCH","field-configurations/{id}/", "Update field config"],
])

endpoint_table("Inventory  (prefix: /api/inventory/)", [
    ["GET",  "projects/", "List projects"],
    ["POST", "projects/", "Create project"],
    ["PATCH","projects/{id}/", "Update project"],
    ["GET",  "projects/{id}/inventory-summary/", "Stats: available/booked/sold counts"],
    ["GET",  "towers/", "List towers"],
    ["POST", "towers/", "Create tower"],
    ["GET",  "towers/{id}/unit-grid/", "2D grid of all units in tower"],
    ["GET",  "units/", "List units (filter by status, BHK, floor)"],
    ["POST", "units/", "Create unit"],
    ["PATCH","units/{id}/", "Update unit details"],
    ["POST", "units/{id}/reserve/", "Reserve unit for a lead"],
    ["POST", "units/{id}/release/", "Release reservation"],
    ["POST", "units/{id}/update-status/", "Manually set unit status"],
    ["POST", "units/price-calculator/", "Calculate total price with premiums"],
    ["GET",  "units/suggest/", "Suggest units based on BHK/budget criteria"],
])

endpoint_table("Bookings  (prefix: /api/bookings/)", [
    ["GET",  "", "List all bookings"],
    ["POST", "", "Create booking (links lead + unit + payment plan)"],
    ["GET",  "{id}/", "Booking details"],
    ["PATCH","Bookings/{id}/", "Update booking status"],
    ["GET",  "{id}/milestones/", "Get payment milestones"],
    ["POST", "{id}/milestones/{mid}/mark-paid/", "Mark milestone as received"],
    ["GET",  "{id}/demand-letter-data/", "Data for demand letter PDF"],
    ["GET",  "{id}/milestones/{mid}/receipt-data/", "Data for receipt PDF"],
    ["GET",  "summary/", "Count of bookings by status"],
    ["GET",  "upcoming-payments/", "Milestones due in next 30 days"],
])

endpoint_table("Brokers — Builder Side  (prefix: /api/brokers/)", [
    ["GET",  "brokers/", "List all brokers"],
    ["POST", "brokers/", "Add broker manually"],
    ["PATCH","brokers/{id}/", "Update broker (approve: status=ACTIVE)"],
    ["GET",  "brokers/leaderboard/", "Broker leaderboard by performance"],
    ["GET",  "brokers/{id}/leads/", "All leads submitted by broker"],
    ["GET",  "brokers/{id}/commissions/", "All commissions for broker"],
    ["GET",  "commissions/", "All commissions across all brokers"],
    ["POST", "commissions/", "Create commission manually"],
    ["POST", "commissions/{id}/mark-paid/", "Pay out commission"],
])

endpoint_table("Payments, Tasks, Meetings  (separate prefixes)", [
    ["GET/POST", "/api/payments/", "Payment ledger (INVOICE/REFUND/ADVANCE)"],
    ["PATCH",    "/api/payments/{id}/", "Update payment status"],
    ["GET/POST", "/api/tasks/", "Task management (TODO/IN_PROGRESS/DONE)"],
    ["PATCH",    "/api/tasks/{id}/", "Update task (status, assignee)"],
    ["GET/POST", "/api/meetings/", "Meeting scheduling"],
    ["PATCH",    "/api/meetings/{id}/", "Update meeting details"],
])

endpoint_table("Analytics  (prefix: /api/analytics/)", [
    ["GET", "overview/", "Dashboard KPIs: leads, bookings, revenue, conversion"],
    ["GET", "inventory/", "Unit availability breakdown by project"],
    ["GET", "sales-funnel/", "Stage conversion rates"],
    ["GET", "revenue/", "Payment collection vs outstanding"],
    ["GET", "agent-leaderboard/", "Team performance ranking"],
    ["GET", "lead-sources/", "ROI by lead source"],
])

endpoint_table("Tenant Settings  (prefix: /api/tenant/)", [
    ["GET",   "settings/", "Get brand config (colors, logo, company name)"],
    ["PATCH", "settings/", "Update branding / contact / PDF config"],
    ["GET",   "payment-plan-templates/", "List payment plan templates"],
    ["POST",  "payment-plan-templates/", "Create new template (20:80, CLP, Custom)"],
    ["PATCH", "payment-plan-templates/{id}/", "Update template"],
    ["DELETE","payment-plan-templates/{id}/", "Delete template"],
])

endpoint_table("Integrations  (prefix: /api/integrations/)", [
    ["GET",  "integrations/", "List available integration types"],
    ["GET",  "connections/", "List active connections"],
    ["POST", "connections/initiate_oauth/", "Start OAuth flow (Google Sheets)"],
    ["POST", "connections/{id}/disconnect/", "Disconnect integration"],
    ["GET",  "connections/{id}/spreadsheets/", "List Google Sheets files"],
    ["GET",  "workflows/", "List automation workflows"],
    ["POST", "workflows/", "Create workflow"],
    ["POST", "workflows/{id}/toggle/", "Activate / pause workflow"],
    ["POST", "workflows/{id}/test/", "Manually trigger workflow"],
    ["GET",  "workflows/{id}/execution-logs/", "Paginated execution history"],
    ["POST", "workflows/{id}/triggers/", "Set workflow trigger"],
    ["POST", "workflows/{id}/actions/", "Add workflow action"],
    ["POST", "workflows/{wid}/actions/{aid}/mappings/", "Map source → destination fields"],
])

# ── SECTION 7: Rules & Notes ──────────────────────────────────────────────────
story += [hr(), h1("7. Key Rules & Notes for Frontend"), hr()]

rules = [
    ["Rule", "Detail"],
    ["Login endpoint", "POST /auth/superadmin-login/  (NOT /api/auth/login/ — that doesn't exist)"],
    ["Auth header (builder)", "Authorization: Bearer <jwt_token>"],
    ["Auth header (broker portal)", "Authorization: Token <broker_token>"],
    ["On 401 response", "Clear localStorage, redirect to /login"],
    ["Tenant isolation", "Backend handles via JWT — frontend does NOT filter by tenant_id"],
    ["First login", "Check GET /api/crm/statuses/ — if empty, call POST /api/crm/statuses/initialize-defaults/"],
    ["White-labeling", "Call GET /api/tenant/settings/ on app boot for logo, colors, company name"],
    ["Permissions", "Read permissions from login response to show/hide sidebar items and action buttons"],
    ["Broker approval", "Builder must set broker status=ACTIVE before broker can submit leads"],
    ["PDF generation", "Backend returns JSON data — frontend renders it into PDF (use jsPDF or similar)"],
    ["File uploads", "Use multipart/form-data for CSV import and attachment uploads"],
]
story.append(tbl(rules, [4.5*cm, 10*cm]))
story.append(sp(8))

# ── SECTION 8: Complete Flow ──────────────────────────────────────────────────
story += [hr(), h1("8. End-to-End Lead Lifecycle Flow"), hr()]
flow = [
    ["Step", "Action", "API Call"],
    ["1", "Lead comes in (manual / import / broker / integration)", "POST /api/crm/leads/"],
    ["2", "Lead appears in INQUIRY column on Kanban", "GET /api/crm/leads/  +  GET /api/crm/statuses/"],
    ["3", "Assign to sales agent", "PATCH /api/crm/leads/{id}/  { assigned_to: user_id }"],
    ["4", "Log first call activity", "POST /api/crm/leads/{id}/add-activity/  { type: 'CALL' }"],
    ["5", "Schedule site visit meeting", "POST /api/meetings/"],
    ["6", "Move lead to SITE_VISIT stage", "POST /api/crm/leads/{id}/move-to-status/"],
    ["7", "Create follow-up task", "POST /api/tasks/  { lead, title, due_date, priority }"],
    ["8", "Suggest suitable unit", "GET /api/inventory/units/suggest/?bhk=3BHK&budget=8500000"],
    ["9", "Reserve unit for lead", "POST /api/inventory/units/{id}/reserve/"],
    ["10", "Calculate total price", "POST /api/inventory/units/price-calculator/"],
    ["11", "Create booking", "POST /api/bookings/  { lead, unit, payment_plan_type }"],
    ["12", "Payment milestones auto-generated", "GET /api/bookings/{id}/milestones/"],
    ["13", "Send demand letter", "GET /api/bookings/{id}/demand-letter-data/  → render PDF"],
    ["14", "Mark token payment received", "POST /api/bookings/{id}/milestones/{id}/mark-paid/"],
    ["15", "If broker referred — commission created", "GET /api/brokers/commissions/"],
    ["16", "Pay out broker commission", "POST /api/brokers/commissions/{id}/mark-paid/"],
    ["17", "Lead moves to BOOKED/REGISTERED", "PATCH /api/crm/leads/{id}/  { stage: 'REGISTERED' }"],
]
story.append(tbl(flow, [1*cm, 6*cm, 7.5*cm]))
story.append(sp(10))

# Footer note
story += [
    hr(),
    Paragraph("Generated by Claude Code — Backend: Django REST API — Frontend: React/Next.js recommended",
              sty("foot","Normal",fontSize=7,textColor=colors.HexColor("#aaa"),alignment=TA_CENTER)),
]

doc.build(story)
print(f"PDF created: {OUTPUT}")
