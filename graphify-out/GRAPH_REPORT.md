# Graph Report - LibManage-project  (2026-10-31)

## Corpus Check
- 43 files · ~174,010 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 1, .db 1, .css 1)

## Summary
- 279 nodes · 697 edges · 12 communities (9 shown, 3 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 91 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Admin Portal & Permissions
- Application Setup & Authentication
- Circulation & Fine Engine
- Reader UI & Jinja Macros
- Librarian Dashboard & Modals
- Catalog API & Inventory
- Loan Slip Model & Seeding
- Reader Web Blueprints
- Loan Record & Status Model
- Design System & UI Tokens

## God Nodes (most connected - your core abstractions)
1. `LoanError` - 34 edges
2. `Book` - 27 edges
3. `User` - 26 edges
4. `Loan` - 26 edges
5. `admin_required()` - 25 edges
6. `LoanSlip` - 20 edges
7. `Category` - 18 edges
8. `Library Catalog Home and Search View` - 17 edges
9. `Borrowing Cart View` - 14 edges
10. `create_app()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Book Cover with CSS Fallback Macro` --implements--> `Fallback CSS Book Covers`  [INFERRED]
  frontend/templates/macros.html → DESIGN.md
- `Admin Layout Shell` --implements--> `Librarian Admin Portal Specification`  [INFERRED]
  frontend/templates/admin/_layout.html → DESIGN.md
- `Book Inventory Donut Chart` --implements--> `Librarian Admin Portal Specification`  [INFERRED]
  frontend/templates/admin/dashboard.html → DESIGN.md
- `Flask Framework Dependency` --references--> `System Architecture Specification`  [INFERRED]
  backend/requirements.txt → README.md
- `Desk Loan Checkout Page` --implements--> `Circulation Business Workflow`  [INFERRED]
  frontend/templates/admin/checkout.html → README.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Physical Return and Damage Compensation Workflow** — frontend_templates_admin_loans_return_modal, frontend_templates_admin_fines_view, readme_fine_and_damage_rules [INFERRED 0.95]
- **Book Title and Physical Copy Lifecycle Management** — frontend_templates_admin_books_view, frontend_templates_admin_book_copies_view, frontend_templates_admin_book_form_view [INFERRED 0.95]
- **Admin Portal Framework and Navigation Structure** — frontend_templates_admin__layout_admin_shell, frontend_templates_admin__layout_sidebar_nav, design_librarian_admin_portal [INFERRED 0.95]
- **Reader Book Discovery, Borrowing, and Circulation Lifecycle** — frontend_templates_index_view, frontend_templates_book_detail_view, frontend_templates_cart_view, frontend_templates_my_loans_view, frontend_templates_slip_detail_view [INFERRED 0.85]
- **Reader Account Onboarding and Authentication Flow** — frontend_templates_base_navbar, frontend_templates_login_view, frontend_templates_register_view [INFERRED 0.85]
- **Jinja Reusable UI Component and Micro-Interaction Kit** — frontend_templates_macros_cover, frontend_templates_macros_meter, frontend_templates_macros_status_badge, frontend_templates_macros_pager, frontend_templates_macros_empty [EXTRACTED 1.00]

## Communities (12 total, 3 thin omitted)

### Community 0 - "Admin Portal & Permissions"
Cohesion: 0.12
Nodes (30): admin_required(), book_copies(), book_delete(), book_edit(), _book_form(), book_new(), book_toggle(), books() (+22 more)

### Community 1 - "Application Setup & Authentication"
Cohesion: 0.08
Nodes (10): change_password(), login(), logout(), _safe_next(), Config, create_app(), set_sqlite_pragma(), CartItem (+2 more)

### Community 2 - "Circulation & Fine Engine"
Cohesion: 0.10
Nodes (19): FinePayment, active_loans(), add_to_cart(), approve(), cancel_request(), _cfg(), checkout_cart(), direct_checkout() (+11 more)

### Community 3 - "Reader UI & Jinja Macros"
Cohesion: 0.13
Nodes (38): Admin Reader Account Registration Form, Admin User Creation Form View, Admin Readers Directory Table, Admin Reader Search Toolbar, Admin Readers Management View, Flash Notifications Container, Application Footer Component, Public Web Application Base Layout (+30 more)

### Community 4 - "Librarian Dashboard & Modals"
Cohesion: 0.10
Nodes (32): Flask Framework Dependency, Flask-Login Authentication Dependency, Flask-SQLAlchemy ORM Dependency, Flask-WTF CSRF Protection Dependency, Admin Layout Shell, Admin Sidebar Navigation Menu, Physical Copy Barcode and Inventory Table, Book Copies Management Page (+24 more)

### Community 5 - "Catalog API & Inventory"
Cohesion: 0.11
Nodes (15): get_book(), list_books(), stats(), BookCopy, Category, dashboard_stats(), delete_book(), delete_category() (+7 more)

### Community 6 - "Loan Slip Model & Seeding"
Cohesion: 0.13
Nodes (5): LoanSlip, _get_or_create_user(), main(), _seed_categories(), _seed_loans()

### Community 7 - "Reader Web Blueprints"
Cohesion: 0.23
Nodes (15): book_detail(), borrow(), cancel(), cart(), cart_add(), cart_checkout(), cart_clear(), cart_remove() (+7 more)

### Community 9 - "Design System & UI Tokens"
Cohesion: 0.25
Nodes (7): Design Tokens Color Palette, Fallback CSS Book Covers, Glassmorphic Navbar Component Design, Librarian Admin Portal Specification, Design System Specification, Typography System Tokens, Book Inventory Donut Chart

## Knowledge Gaps
- **26 isolated node(s):** `Typography System Tokens`, `Glassmorphic Navbar Component Design`, `Flask Framework Dependency`, `Flask-SQLAlchemy ORM Dependency`, `Flask-Login Authentication Dependency` (+21 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 94 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Loan` connect `Loan Record & Status Model` to `Admin Portal & Permissions`, `Application Setup & Authentication`, `Circulation & Fine Engine`, `Catalog API & Inventory`, `Loan Slip Model & Seeding`, `Reader Web Blueprints`?**
  _High betweenness centrality (0.059) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `LoanError` (e.g. with `_book_form()` and `categories()`) actually correct?**
  _`LoanError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Typography System Tokens`, `Glassmorphic Navbar Component Design`, `Flask Framework Dependency` to the rest of the system?**
  _26 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Admin Portal & Permissions` be split into smaller, more focused modules?**
  _Cohesion score 0.11690821256038647 - nodes in this community are weakly interconnected._
- **Why does `User` connect `Admin Portal & Permissions` to `Application Setup & Authentication`, `Circulation & Fine Engine`, `Catalog API & Inventory`, `Loan Slip Model & Seeding`?**
  _High betweenness centrality (0.057) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Book` (e.g. with `book_copies()` and `book_delete()`) actually correct?**
  _`Book` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Should `Application Setup & Authentication` be split into smaller, more focused modules?**
  _Cohesion score 0.080338266384778 - nodes in this community are weakly interconnected._