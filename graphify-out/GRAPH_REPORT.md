# Graph Report - LibManage-project  (2026-11-01)

## Corpus Check
- 23 files · ~370,642 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 1, .db 1, .css 1)

## Summary
- 293 nodes · 735 edges · 11 communities (8 shown, 3 thin omitted)
- Extraction: 87% EXTRACTED · 13% INFERRED · 0% AMBIGUOUS · INFERRED: 99 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6f9969fb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Loan Circulation & 48h Auto-Cancel Flow
- Public Catalog & Search API
- Book Inventory & Physical Copies
- Admin Management & Physical Copy Editing
- Admin UI Templates & Profile Views
- System Architecture & Design Specs
- Loan Overdue & Fine Calculation
- Multi-Item Loan Slip Synchronization
- Architecture Overview & Delivery Diagrams

## God Nodes (most connected - your core abstractions)
1. `LoanError` - 34 edges
2. `Book` - 28 edges
3. `Loan` - 27 edges
4. `admin_required()` - 26 edges
5. `User` - 26 edges
6. `LoanSlip` - 20 edges
7. `Category` - 18 edges
8. `Library Catalog Home and Search View` - 17 edges
9. `BookCopy` - 14 edges
10. `Borrowing Cart View` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Reader Password Reset Modal` --references--> `user_reset_password()`  [EXTRACTED]
  frontend/templates/admin/user_detail.html → backend/app/blueprints/admin.py
- `Circulation Business Workflow` --references--> `sync_slip_status()`  [INFERRED]
  README.md → backend/app/services/loan_service.py
- `Circulation Business Workflow` --references--> `cancel_expired_pickups()`  [INFERRED]
  README.md → backend/app/services/loan_service.py
- `Edit Book Copy Status Modal` --references--> `book_copy_edit()`  [EXTRACTED]
  frontend/templates/admin/book_copies.html → backend/app/blueprints/admin.py
- `Reader Profile Detail Page` --references--> `user_detail()`  [EXTRACTED]
  frontend/templates/admin/user_detail.html → backend/app/blueprints/admin.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Jinja Reusable UI Component and Micro-Interaction Kit** — frontend_templates_macros_cover, frontend_templates_macros_meter, frontend_templates_macros_status_badge, frontend_templates_macros_pager, frontend_templates_macros_empty [EXTRACTED 1.00]
- **Reader Account Onboarding and Authentication Flow** — frontend_templates_base_navbar, frontend_templates_login_view, frontend_templates_register_view [INFERRED 0.85]
- **Reader Book Discovery, Borrowing, and Circulation Lifecycle** — frontend_templates_index_view, frontend_templates_book_detail_view, frontend_templates_cart_view, frontend_templates_my_loans_view, frontend_templates_slip_detail_view [INFERRED 0.85]
- **Admin Portal Framework and Navigation Structure** — frontend_templates_admin__layout_admin_shell, frontend_templates_admin__layout_sidebar_nav, design_librarian_admin_portal [INFERRED 0.95]
- **Book Title and Physical Copy Lifecycle Management** — frontend_templates_admin_books_view, frontend_templates_admin_book_copies_view, frontend_templates_admin_book_form_view [INFERRED 0.95]
- **Physical Return and Damage Compensation Workflow** — frontend_templates_admin_loans_return_modal, frontend_templates_admin_fines_view, readme_fine_and_damage_rules [INFERRED 0.95]
- **48h Pickup Expiration & Slip Synchronization Flow** — backend_app_services_loan_service_cancel_expired_pickups, backend_app_services_loan_service_sync_slip_status, backend_app_services_loan_service_handover, backend_app_models_loanslip [INFERRED 0.95]

## Communities (11 total, 3 thin omitted)

### Community 0 - "Loan Circulation & 48h Auto-Cancel Flow"
Cohesion: 0.08
Nodes (21): Borrow & Circulation Flow Sequence Diagram, admin_before_request(), Loan, active_loans(), add_to_cart(), approve(), cancel_expired_pickups(), cancel_request() (+13 more)

### Community 1 - "Public Catalog & Search API"
Cohesion: 0.08
Nodes (11): Database Entity-Relationship Architecture, change_password(), login(), logout(), _safe_next(), Config, create_app(), set_sqlite_pragma() (+3 more)

### Community 2 - "Book Inventory & Physical Copies"
Cohesion: 0.09
Nodes (9): BookCopy, FinePayment, LoanSlip, pay_fine(), _get_or_create_user(), main(), _seed_books(), _seed_categories() (+1 more)

### Community 3 - "Admin Management & Physical Copy Editing"
Cohesion: 0.10
Nodes (31): admin_required(), book_copies(), book_copy_edit(), book_delete(), book_edit(), book_new(), book_toggle(), books() (+23 more)

### Community 4 - "Admin UI Templates & Profile Views"
Cohesion: 0.13
Nodes (38): Admin Reader Account Registration Form, Admin User Creation Form View, Admin Readers Directory Table, Admin Reader Search Toolbar, Admin Readers Management View, Flash Notifications Container, Application Footer Component, Public Web Application Base Layout (+30 more)

### Community 5 - "System Architecture & Design Specs"
Cohesion: 0.07
Nodes (37): Flask Framework Dependency, Flask-Login Authentication Dependency, Flask-SQLAlchemy ORM Dependency, Flask-WTF CSRF Protection Dependency, Design Tokens Color Palette, Fallback CSS Book Covers, Glassmorphic Navbar Component Design, Librarian Admin Portal Specification (+29 more)

### Community 6 - "Loan Overdue & Fine Calculation"
Cohesion: 0.14
Nodes (17): _book_form(), categories(), category_edit(), get_book(), list_books(), stats(), Category, dashboard_stats() (+9 more)

### Community 7 - "Multi-Item Loan Slip Synchronization"
Cohesion: 0.23
Nodes (15): book_detail(), borrow(), cancel(), cart(), cart_add(), cart_checkout(), cart_clear(), cart_remove() (+7 more)

## Knowledge Gaps
- **28 isolated node(s):** `Borrow & Circulation Flow Sequence Diagram`, `Database Entity-Relationship Architecture`, `Physical Copy Barcode and Inventory Table`, `Admin Readers Directory Table`, `Admin Reader Search Toolbar` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 101 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **3 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Reader Profile Detail Page` connect `System Architecture & Design Specs` to `Admin Management & Physical Copy Editing`, `Admin UI Templates & Profile Views`?**
  _High betweenness centrality (0.241) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `LoanError` (e.g. with `_book_form()` and `categories()`) actually correct?**
  _`LoanError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Borrow & Circulation Flow Sequence Diagram`, `Database Entity-Relationship Architecture`, `Physical Copy Barcode and Inventory Table` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Loan Circulation & 48h Auto-Cancel Flow` be split into smaller, more focused modules?**
  _Cohesion score 0.08048103607770583 - nodes in this community are weakly interconnected._
- **Why does `user_detail()` connect `Admin Management & Physical Copy Editing` to `Loan Circulation & 48h Auto-Cancel Flow`, `System Architecture & Design Specs`?**
  _High betweenness centrality (0.239) - this node is a cross-community bridge._
- **Are the 17 inferred relationships involving `Book` (e.g. with `book_copies()` and `book_copy_edit()`) actually correct?**
  _`Book` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Should `Public Catalog & Search API` be split into smaller, more focused modules?**
  _Cohesion score 0.07729468599033816 - nodes in this community are weakly interconnected._