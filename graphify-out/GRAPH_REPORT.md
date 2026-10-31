# Graph Report - LibManage-project  (2026-10-31)

## Corpus Check
- 17 files · ~369,276 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 293 nodes · 633 edges · 11 communities (6 shown, 5 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 51 edges (avg confidence: 0.94)
- Token cost: 1,450 input · 980 output

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
2. `admin_required()` - 26 edges
3. `Library Catalog Home and Search View` - 17 edges
4. `User` - 15 edges
5. `Borrowing Cart View` - 14 edges
6. `Reader Loans and Borrowing History View` - 13 edges
7. `create_app()` - 12 edges
8. `Public Web Application Base Layout` - 12 edges
9. `Book` - 11 edges
10. `Loan` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Circulation Business Workflow` --references--> `sync_slip_status()`  [INFERRED]
  README.md → backend/app/services/loan_service.py
- `Circulation Business Workflow` --references--> `cancel_expired_pickups()`  [INFERRED]
  README.md → backend/app/services/loan_service.py
- `Book Cover with CSS Fallback Macro` --implements--> `Fallback CSS Book Covers`  [INFERRED]
  frontend/templates/macros.html → DESIGN.md
- `Edit Book Copy Status Modal` --references--> `book_copy_edit()`  [EXTRACTED]
  frontend/templates/admin/book_copies.html → backend/app/blueprints/admin.py
- `Book Copies Management Page` --references--> `book_copies()`  [EXTRACTED]
  frontend/templates/admin/book_copies.html → backend/app/blueprints/admin.py

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

## Communities (11 total, 5 thin omitted)

### Community 0 - "Loan Circulation & 48h Auto-Cancel Flow"
Cohesion: 0.06
Nodes (36): Borrow & Circulation Flow Sequence Diagram, admin_before_request(), book_detail(), borrow(), cancel(), cart(), cart_add(), cart_checkout() (+28 more)

### Community 1 - "Public Catalog & Search API"
Cohesion: 0.06
Nodes (15): Database Entity-Relationship Architecture, get_book(), list_books(), stats(), change_password(), login(), logout(), register() (+7 more)

### Community 2 - "Book Inventory & Physical Copies"
Cohesion: 0.07
Nodes (20): Book, BookCopy, Category, User, dashboard_stats(), delete_book(), delete_category(), public_stats() (+12 more)

### Community 3 - "Admin Management & Physical Copy Editing"
Cohesion: 0.12
Nodes (34): admin_required(), book_copies(), book_copy_edit(), book_delete(), book_edit(), _book_form(), book_new(), book_toggle() (+26 more)

### Community 4 - "Admin UI Templates & Profile Views"
Cohesion: 0.13
Nodes (38): Admin Reader Account Registration Form, Admin User Creation Form View, Admin Readers Directory Table, Admin Reader Search Toolbar, Admin Readers Management View, Flash Notifications Container, Application Footer Component, Public Web Application Base Layout (+30 more)

### Community 5 - "System Architecture & Design Specs"
Cohesion: 0.08
Nodes (34): Flask Framework Dependency, Flask-Login Authentication Dependency, Flask-SQLAlchemy ORM Dependency, Flask-WTF CSRF Protection Dependency, Design Tokens Color Palette, Fallback CSS Book Covers, Glassmorphic Navbar Component Design, Librarian Admin Portal Specification (+26 more)

## Knowledge Gaps
- **28 isolated node(s):** `Admin Readers Directory Table`, `Admin Reader Search Toolbar`, `Flash Notifications Container`, `Related Category Books Recommendation Section`, `Cart Submission and Checkout Form` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 102 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Reader Profile Detail Page` connect `Admin Management & Physical Copy Editing` to `Admin UI Templates & Profile Views`, `System Architecture & Design Specs`?**
  _High betweenness centrality (0.222) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `LoanError` (e.g. with `_book_form()` and `categories()`) actually correct?**
  _`LoanError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Admin Readers Directory Table`, `Admin Reader Search Toolbar`, `Flash Notifications Container` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Loan Circulation & 48h Auto-Cancel Flow` be split into smaller, more focused modules?**
  _Cohesion score 0.059227921734531994 - nodes in this community are weakly interconnected._
- **Why does `Admin Readers Management View` connect `Admin UI Templates & Profile Views` to `Admin Management & Physical Copy Editing`, `System Architecture & Design Specs`?**
  _High betweenness centrality (0.194) - this node is a cross-community bridge._
- **Are the 5 inferred relationships involving `User` (e.g. with `login()` and `register()`) actually correct?**
  _`User` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Should `Public Catalog & Search API` be split into smaller, more focused modules?**
  _Cohesion score 0.06274509803921569 - nodes in this community are weakly interconnected._