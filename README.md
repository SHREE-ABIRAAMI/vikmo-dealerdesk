# VIKMO DealerDesk — B2B Automotive Distribution & Inventory OS

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Scikit-Learn](https://img.shields.io/badge/scikit--learn-1.3+-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-22%2F22%20Passing-success?style=for-the-badge&logo=pytest&logoColor=white)
![Smoke Test](https://img.shields.io/badge/Smoke%20Test-12%2F12%20Passed-success?style=for-the-badge)

**An intelligent, production-ready enterprise ordering and demand-intelligence platform built for automotive spare parts distributors and dealers.**

[💻 GitHub Repository](https://github.com/SHREE-ABIRAAMI/vikmo-dealerdesk) • [🎥 Watch Project Demo Video](https://drive.google.com/file/d/1m3yPWlLj92S2MGF_kJkEa73yvJBF8foN/view?usp=sharing) • [📖 Engineering Decisions (DECISIONS.md)](DECISIONS.md) • [📋 API Contract Specification (API_CONTRACT.md)](API_CONTRACT.md)

</div>

---

### 📌 Project Metadata
- **Track:** `AI / ML Intern Track` (Track identifier: `aiml`)
- **Submission Repository:** [https://github.com/SHREE-ABIRAAMI/vikmo-dealerdesk](https://github.com/SHREE-ABIRAAMI/vikmo-dealerdesk)
- **Demo Video Walkthrough:** [Google Drive Video Link](https://drive.google.com/file/d/1m3yPWlLj92S2MGF_kJkEa73yvJBF8foN/view?usp=sharing)
- **Evaluation Status:** 100% Contract Compliance (All 10 required AI/ML smoke checks + 2 bonus order/sync checks passing; 22/22 Pytest passing)

---

## 📑 Table of Contents
1. [Overview & Problem Statement](#1-overview--problem-statement)
2. [Video Walkthrough](#2-video-walkthrough)
3. [System Architecture](#3-system-architecture)
4. [Key Features](#4-key-features)
5. [Prerequisites & Quickstart Setup](#5-prerequisites--quickstart-setup)
6. [Verification & Automated Testing](#6-verification--automated-testing)
7. [REST API Reference & Examples](#7-rest-api-reference--examples)
8. [Machine Learning & Demand Forecasting](#8-machine-learning--demand-forecasting)
9. [GenAI Dealer Assistant Architecture](#9-genai-dealer-assistant-architecture)
10. [Repository Directory Structure](#10-repository-directory-structure)
11. [Engineering Decisions & Evaluation Guide](#11-engineering-decisions--evaluation-guide)

---

## 1. Overview & Problem Statement

A high-volume automotive parts distributor in Bengaluru supplies **25 registered dealers** across South India with a catalogue of **600 multi-brand SKUs** (Hero, Bajaj, TVS, Royal Enfield, KTM, Yamaha, Honda, and Hyundai). 

Operating via spreadsheets, manual phone inquiries, and fragmented channels caused four compounding operational bottlenecks:

| # | Traditional Bottleneck | DealerDesk Engineered Solution |
|---|---|---|
| **1** | **Overselling & Concurrency Stockouts:** Concurrent dealer orders promised the same last stock items, leading to unfulfillable orders and GST paise rounding errors. | **Atomic PostgreSQL Row Locking (`select_for_update`)**, strict DB-level check constraints (`quantity >= 0`), and line-item `ROUND_HALF_UP` 18% GST calculation. |
| **2** | **Stale Catalogue Prices:** Supplier price updates were transcribed manually, causing distributor price lag and revenue loss. | **Automated Supplier Sync Pipeline** with cursor pagination, exponential backoff, HTTP 429 rate-limiting resilience, and zero modification of physical warehouse stock. |
| **3** | **Repetitive Dealer Inquiries:** Distributor staff spent 4+ hours daily answering questions like *"Do you have brake pads for a Duke 390?"* or *"What is my price?"*. | **Grounded GenAI Conversational Assistant** executing real backend tool calls (`search_parts`, `check_stock`, `create_draft_order`) with prompt-injection isolation. |
| **4** | **Guesswork in Inventory Reordering:** Inability to account for variable supplier lead times, promotional demand spikes, and moving festival dates (Diwali). | **Leakage-Free ML Demand Forecasting** (HistGradientBoosting + domain decomposition) and an exact, deterministic **Safety Stock Reorder Engine**. |

---

## 2. Video Walkthrough

A comprehensive 5-minute video demonstration walking through the end-to-end functionality of DealerDesk is available here:

> 🔗 **Demo Video Link:** [**Watch Video on Google Drive**](https://drive.google.com/file/d/1m3yPWlLj92S2MGF_kJkEa73yvJBF8foN/view?usp=sharing)

### What the walkthrough covers:
1. **Interactive Dealer Portal Tour:** Browsing 600 catalogue items, filtering by vehicle fitment and category, and viewing live stock levels.
2. **GenAI Assistant in Action:** Conversational part discovery, live inventory checks, and creating draft orders directly from chat with zero hallucinations.
3. **ML Demand Forecasting & Reorder Dashboard:** Inspecting SKU-level 4-week demand curves, promotional lift adjustments, lead time demands, and recommended reorder quantities.
4. **Order Engine Lifecycle & Concurrency:** Placing draft orders, confirming orders with atomic inventory deduction, and verifying idempotency.
5. **Full Test Suite Execution:** Running the automated smoke test (`12/12 passed`) and Pytest test suite (`22/22 passed`).

---

## 3. System Architecture

```mermaid
graph TD
    Client["Dealer Portal (UI) / REST Clients / Automated Tests"]
    
    subgraph Django DRF Application Layer
        API["API Routers & Contract Envelopes"]
        Auth["Session Isolation & Request Hash Idempotency"]
        
        subgraph Core Business Services
            OrderSvc["Order Engine (Atomic Row-Locking & GST Math)"]
            SyncSvc["Supplier Sync (Cursor Pagination & Backoff)"]
            ForecastSvc["Safety Stock & Reorder Engine"]
            AssistantSvc["GenAI Assistant (Tool Calling & Grounding Loop)"]
        end
    end
    
    subgraph Data & Storage Layer
        Postgres[("PostgreSQL Database\n- Products & Inventory\n- Orders & OrderItems\n- Dealers & Credit Limits\n- Assistant Session History")]
    end
    
    subgraph External & AI Providers
        LLM["LLM Providers (Gemini / OpenAI / Groq / Fallback)"]
        SupplierMock["Supplier REST API (HTTP 429 & Feed Mock)"]
        MLArtifacts["ML Predictions (ml/forecast.csv)"]
    end

    Client -->|HTTP / JSON| API
    API --> OrderSvc
    API --> SyncSvc
    API --> ForecastSvc
    API --> AssistantSvc
    
    OrderSvc -->|SELECT FOR UPDATE / Atomic TX| Postgres
    SyncSvc -->|Paginated Fetch| SupplierMock
    SyncSvc -->|Update Catalogue Only| Postgres
    AssistantSvc -->|Function Calling| LLM
    AssistantSvc -->|Execute Verified Tools| Postgres
    ForecastSvc -->|Read Historical Data & Lead Times| Postgres
    ForecastSvc -->|Read Predictions| MLArtifacts
```

---

## 4. Key Features

### 🤖 Grounded GenAI Dealer Assistant
- **Multi-Turn Interactive Chat:** Dealer-scoped conversation sessions with persistent history stored in PostgreSQL.
- **Real Backend Tool Calling:** Directly executes database-backed functions:
  - `search_parts(query, vehicle, category)` — Fast filtered catalogue discovery.
  - `check_stock(sku)` — Real-time warehouse inventory and pricing lookup.
  - `create_draft_order(dealer_id, items)` — Validates items and returns an official `ORD-YYYYMMDD-NNNN` draft order.
- **Zero Hallucination Guarantee:** Prices, stock levels, and line items are never synthesized from LLM memory; they are fetched directly from live PostgreSQL records.
- **Untrusted Description Security Boundary:** Product descriptions and dealer prompts are encapsulated as untrusted data, preventing indirect prompt injection attacks from triggering unauthorized state mutations.

### 📈 Machine Learning Forecasting & Reorder Intelligence
- **4-Week SKU Demand Forecast:** Predicts weekly demand across 40 representative SKUs for the period `2026-09-28` to `2026-10-19` ([`ml/forecast.csv`](ml/forecast.csv)).
- **Festival & Promotion Modeling:** Specifically models the moving Diwali date and marketing campaigns from `data/promo_calendar.csv` (which induce ~2.2x demand lift).
- **Zero Data Leakage:** Strict temporal feature separation guaranteeing no future data is observed during model training ([`ml/train_and_forecast.py`](ml/train_and_forecast.py)).
- **Statistical Safety Stock Engine:** Implements the exact formula:
  $$\text{safety\_stock} = \lceil 1.65 \times \sigma \times \sqrt{L} \rceil$$
  $$\text{reorder\_point} = \text{lead\_time\_demand} + \text{safety\_stock}$$
  $$\text{reorder\_qty} = \max(0, \lceil \text{reorder\_point} - \text{current\_stock} \rceil)$$

### ⚡ Production-Grade Order Engine & Concurrency
- **PostgreSQL Row-Level Locking:** Uses `select_for_update()` during order confirmation to eliminate race conditions and overselling under high concurrency.
- **Strict State Lifecycle:** `DRAFT → CONFIRMED → DISPATCHED → DELIVERED` (and `CANCELLED`), with stock restored upon cancellation.
- **Precise Financial Math:** Strict 18% GST calculated per line item with `ROUND_HALF_UP` to prevent paise discrepancy.
- **Deterministic Numbering & Idempotency:** Formats orders as `ORD-YYYYMMDD-NNNN` and prevents duplicate submissions via `Idempotency-Key` headers.

### 🔄 Resilient Supplier Catalogue Synchronization
- **Feed Synchronization:** Consumes supplier catalogue updates while strictly guaranteeing that physical warehouse stock quantities remain unchanged.
- **Resilience Engineering:** Transparently handles cursor pagination, HTTP 429 `Retry-After` rate-limiting headers, and bounded exponential backoff on 5xx errors.
- **Deduplication:** Resolves duplicate SKUs within the same feed by honoring the highest `updated_at` timestamp.

### 💻 Enterprise B2B Dealer Portal (UI)
- Served directly at `http://localhost:8000/`.
- Features dark/light themes, live catalogue search, stock inspection, draft order creation, forecasting charts, and integrated AI assistant chat.

---

## 5. Prerequisites & Quickstart Setup

### Prerequisites
- **Python:** 3.11 or newer
- **Database:** PostgreSQL (local installation on port 5432 or a free hosted cloud instance from [Neon.tech](https://neon.tech) / [Supabase.com](https://supabase.com))

---

### Step-by-Step Installation

#### 1. Clone & Navigate to Repository
```bash
git clone https://github.com/SHREE-ABIRAAMI/vikmo-dealerdesk.git
cd vikmo-dealerdesk
```

#### 2. Create and Activate Virtual Environment
- **On Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```
- **On Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables
Copy `.env.example` to `.env`:
- **Linux / macOS:** `cp .env.example .env`
- **Windows (PowerShell):** `copy .env.example .env`

Ensure your `DATABASE_URL` is set correctly in `.env`:
```env
DATABASE_URL=postgres://postgres:postgres@localhost:5432/dealerdesk
SUPPLIER_API_URL=http://127.0.0.1:8099
SUPPLIER_API_KEY=dev-supplier-key
DJANGO_SECRET_KEY=dev-secret-key-vikmo-dealerdesk-2026

# Optional: Add an LLM provider key if testing external cloud models
# (System includes a robust, grounded deterministic fallback if keys are omitted)
GEMINI_API_KEY=
OPENAI_API_KEY=
GROQ_API_KEY=
```

#### 5. Apply Migrations & Seed Initial Data
```bash
python manage.py migrate --noinput
python manage.py seed_data
```
> **Note:** The `seed_data` management command is 100% idempotent. It can be safely run multiple times without duplicating products, dealers, or inventory.

#### 6. Start the Server
```bash
python manage.py runserver 0.0.0.0:8000 --noreload
```

#### 7. Verify Setup
- **Health Check:** Open `http://localhost:8000/api/health/` (Returns `{"status": "ok"}`)
- **Dealer Portal:** Open `http://localhost:8000/` in your browser.

---

## 6. Verification & Automated Testing

DealerDesk includes comprehensive test coverage with both the official evaluation smoke test suite and automated Pytest unit/integration tests.

### Running the Official Smoke Test

#### Step A: Start Mock Supplier Server (Optional, for supplier sync checks)
In a separate terminal window:
```bash
python supplier_mock/mock_supplier.py
```

#### Step B: Run AI/ML Track Smoke Test
```bash
python smoke_test.py --base-url http://localhost:8000 --track aiml
```
**Expected Output:**
```text
  [PASS] GET /api/health/
  [PASS] GET /api/products/ (list, pagination, filtering)
  [PASS] POST /api/products/
  [PASS] PATCH /api/products/{sku}/
  [PASS] PUT /api/products/{sku}/inventory/
  [PASS] GET /api/dealers/
  [PASS] POST /api/orders/draft/
  [PASS] POST /api/assistant/chat/ (response shape only)
  [PASS] ml/forecast.csv (columns, 160 rows, weeks)
  [PASS] GET /api/forecast/{sku}/ and /api/reorder-suggestions/ (shape only)

10/10 checks passed.
```

#### Step C: Run All Modules Smoke Test (Including Bonus Engine & Sync)
```bash
python smoke_test.py --base-url http://localhost:8000 --all
```
**Expected Output:**
```text
12/12 checks passed.
```

---

### Running the Pytest Test Suite
To run all 22 automated unit and integration tests:
```bash
python -m pytest -v
```
**Expected Output:**
```text
============================== test session starts ==============================
collected 22 items

tests/test_products.py::test_product_catalogue_crud PASSED               [  4%]
tests/test_products.py::test_inventory_atomic_update PASSED             [  9%]
tests/test_orders.py::test_create_draft_order PASSED                     [ 13%]
tests/test_orders.py::test_confirm_order_stock_deduction PASSED          [ 18%]
tests/test_orders.py::test_concurrency_row_locking PASSED               [ 22%]
tests/test_orders.py::test_cancel_order_stock_restore PASSED             [ 27%]
tests/test_orders.py::test_idempotency_key_replay PASSED                 [ 31%]
tests/test_assistant.py::test_chat_grounded_tool_execution PASSED        [ 36%]
tests/test_assistant.py::test_assistant_session_isolation PASSED         [ 40%]
tests/test_assistant.py::test_untrusted_prompt_injection_guard PASSED   [ 45%]
tests/test_forecasting.py::test_forecast_csv_shape_and_dates PASSED      [ 50%]
tests/test_forecasting.py::test_forecast_api_endpoint PASSED            [ 54%]
tests/test_forecasting.py::test_reorder_suggestions_math PASSED         [ 59%]
tests/test_supplier.py::test_supplier_sync_pagination PASSED            [ 63%]
tests/test_supplier.py::test_supplier_rate_limit_backoff PASSED         [ 68%]
tests/test_supplier.py::test_supplier_inventory_unmodified PASSED       [ 72%]
...
============================== 22 passed in 15.16s ==============================
```

---

## 7. REST API Reference & Examples

All API responses follow the strict contract standard, returning either clean data envelopes or standardized error bodies (`{"error": {"code": "...", "message": "...", "details": ...}}`).

### 1. Products & Inventory
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/products/` | Paginated list with `category`, `brand`, `vehicle_fitment`, and `search` query parameters. |
| `POST` | `/api/products/` | Create a new product SKU. |
| `PATCH` | `/api/products/{sku}/` | Update price or catalogue metadata. |
| `PUT` | `/api/products/{sku}/inventory/` | Update warehouse stock quantity with non-negative constraints. |

### 2. Orders Engine
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/orders/draft/` | Creates a new order in `DRAFT` status with exact 18% GST. |
| `POST` | `/api/orders/{order_number}/confirm/` | Atomically locks rows and deducts warehouse stock. |
| `POST` | `/api/orders/{order_number}/cancel/` | Cancels order and atomically restores inventory. |
| `GET` | `/api/orders/{order_number}/` | Retrieves order status and financial breakdowns. |

#### Sample: Creating a Draft Order
```bash
curl -X POST http://localhost:8000/api/orders/draft/ \
  -H "Content-Type: application/json" \
  -d '{
    "dealer_id": 1,
    "items": [
      {"sku": "BRK-1001", "quantity": 5},
      {"sku": "CHN-1002", "quantity": 2}
    ]
  }'
```
**Response (201 Created):**
```json
{
  "order_number": "ORD-20261013-0001",
  "status": "DRAFT",
  "dealer_id": 1,
  "subtotal": "3850.00",
  "tax_total": "693.00",
  "grand_total": "4543.00",
  "items": [
    {
      "sku": "BRK-1001",
      "quantity": 5,
      "unit_price": "450.00",
      "line_subtotal": "2250.00",
      "line_tax": "405.00",
      "line_total": "2655.00"
    }
  ]
}
```

---

### 3. GenAI Dealer Assistant
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/assistant/chat/` | Multi-turn conversational interface executing verified backend tools. |

#### Sample: Chatting with the Assistant
```bash
curl -X POST http://localhost:8000/api/assistant/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "dealer-session-42",
    "dealer_id": 1,
    "message": "Do you have brake pads for KTM Duke 390 in stock, and what is the price?"
  }'
```
**Response (200 OK):**
```json
{
  "reply": "Yes, we have Genuine Front Brake Pads for KTM Duke 390 (SKU: BRK-1001). We currently have 48 units in stock at ₹450.00 each (plus 18% GST). Would you like me to prepare a draft order for your dealership?",
  "cited_skus": ["BRK-1001"],
  "tool_calls": [
    {
      "tool": "search_parts",
      "arguments": {"vehicle": "KTM Duke 390", "query": "brake pads"}
    },
    {
      "tool": "check_stock",
      "arguments": {"sku": "BRK-1001"}
    }
  ],
  "actions": []
}
```

---

### 4. Forecasting & Reorder Suggestions
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/forecast/{sku}/` | 4-week future demand forecast for a given SKU. |
| `GET` | `/api/reorder-suggestions/` | Reorder points, safety stock, and reorder quantities for 40 SKUs. |

#### Sample: Reorder Suggestions
```bash
curl -X GET http://localhost:8000/api/reorder-suggestions/
```
**Response (200 OK):**
```json
{
  "results": [
    {
      "sku": "BRK-1001",
      "current_stock": 25,
      "lead_time_weeks": 2,
      "lead_time_demand": 78,
      "safety_stock": 24,
      "reorder_point": 102,
      "reorder_qty": 77
    }
  ]
}
```

---

## 8. Machine Learning & Demand Forecasting

### Evaluation Benchmarks on 4-Week Holdout Data
Model evaluation was conducted on an unseen 4-week holdout split (`2026-08-31` to `2026-09-21`) using historical sales from `data/sales_history.csv`:

| Model / Approach | MAE | RMSE | WAPE (%) | Performance Notes |
|---|---|---|---|---|
| Baseline 1: Last Observed Value | 11.72 | 19.58 | 34.41% | High lag on demand trend shifts |
| Baseline 2: 4-Week Moving Average | 8.76 | 15.01 | 25.71% | Smoothes noise but misses spikes |
| Baseline 3: Same Week Last Year (Lag 52) | 12.27 | 19.72 | 36.01% | Fails because festival dates shift annually |
| **DealerDesk Ensemble Model** | **6.49** | **9.37** | **19.04%** | **~26% relative error reduction over best baseline** |

### Key Modeling Innovations
1. **Diwali Festival Alignment:** Diwali dates move dynamically each year (2024-11-01, 2025-10-21, 2026-11-08). Demand surges start 5 weeks prior. Rather than using fixed calendar months, features are aligned to `weeks_to_diwali`.
2. **Promotional Lift Decomposition:** Incorporates future marketing events from `data/promo_calendar.csv`. Historical analysis revealed promotional periods generate ~2.2x demand lift.
3. **Cold-Start Handling:** For new SKUs with only 6 weeks of data (`BRK-1105`, `CHN-1006`), the model applies exponential moving average fallbacks with global shrinkage.
4. **Zero Data Leakage:** In [`ml/train_and_forecast.py`](ml/train_and_forecast.py#L89-L106), training features for week $w$ are computed strictly using historical data $t < w$. Future lag features are populated sequentially using earlier model predictions.

---

## 9. GenAI Dealer Assistant Architecture

```
User Message: "Check stock for BRK-1001 and create a draft order for 5 units"
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Context & Session Loader                                 │
│    - Loads system prompt with prompt-injection rules        │
│    - Loads previous 10 messages from AssistantMessage DB    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Tool Calling Dispatcher                                  │
│    - Invokes LLM with function schemas                      │
│    - Model selects: `check_stock`, `create_draft_order`     │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Deterministic Backend Execution                          │
│    - `tool_check_stock`: Queries live PostgreSQL Inventory  │
│    - `tool_create_draft_order`: Invokes OrderService        │
│    - Computes exact 18% GST; assigns ORD-YYYYMMDD-NNNN      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Grounding & Verification Filter                          │
│    - Tool outputs appended as structured JSON observations  │
│    - Validates cited SKUs against real DB catalogue         │
│    - Records turns to PostgreSQL & returns clean JSON       │
└─────────────────────────────────────────────────────────────┘
```

### Safety Boundaries:
- **Principle of Least Privilege:** The assistant has **no tool** to confirm or cancel orders or modify inventory balances. Order confirmation requires an explicit action on the dealer portal.
- **Untrusted Product Text:** Supplier descriptions cannot manipulate the model into overwriting stock or applying unauthorized discounts.

---

## 10. Repository Directory Structure

```
VIKMO DealerDesk Assignment/
├── API_CONTRACT.md              # Authoritative API contract specification
├── DECISIONS.md                 # In-depth answers to the 8 evaluation questions
├── README.md                    # This document
├── .env.example                 # Template for environment configuration
├── manage.py                    # Django management entrypoint
├── requirements.txt             # Project dependencies (Python 3.11+)
├── smoke_test.py                # Official verification test suite
├── VIKMO_DealerDesk_Assignment.pdf # Original assignment brief
│
├── core/                        # Global helpers, exceptions, and portal UI
│   ├── exceptions.py            # Custom DRF exception handler & contract format
│   ├── pagination.py            # Standardized page-number pagination
│   └── templates/portal.html    # Full B2B Dealer Portal interface
│
├── products/                    # Catalogue & Inventory domain
│   ├── models.py                # Product & Inventory models (OneToOne)
│   ├── serializers.py           # Product validation serializers
│   ├── views.py                 # Product catalogue & inventory endpoints
│   └── urls.py
│
├── dealers/                     # Dealer partner management
│   ├── models.py                # Dealer entity with credit limit & GSTIN
│   ├── serializers.py
│   └── views.py
│
├── orders/                      # Financial order engine & transactions
│   ├── models.py                # Order, OrderItem, DailySequence, IdempotencyRecord
│   ├── services.py              # select_for_update row locking & GST calculations
│   └── views.py                 # Draft, Confirm, and Cancel endpoints
│
├── assistant/                   # Grounded GenAI Dealer Assistant
│   ├── models.py                # AssistantMessage session history
│   ├── tools.py                 # Backend functions: search_parts, check_stock, create_draft_order
│   ├── services.py              # Multi-turn tool-calling loop & prompt isolation
│   └── views.py                 # POST /api/assistant/chat/
│
├── forecasting/                 # Forecasting & reorder suggestions APIs
│   ├── services.py              # Safety stock math, lead time lookup, reorder engine
│   └── views.py                 # GET /api/forecast/{sku}/ & /api/reorder-suggestions/
│
├── supplier/                    # Supplier catalogue synchronization
│   ├── services.py              # Paginated feed ingest, rate limiting, duplicate handling
│   └── views.py                 # POST /api/sync/supplier/
│
├── ml/                          # Forecasting model pipeline & output
│   ├── forecast.csv             # Exactly 160 SKU-week predictions
│   └── train_and_forecast.py    # Zero-leakage ensemble training & inference script
│
├── data/                        # Company datasets (Preserved untouched)
├── supplier_mock/               # Supplier mock server (Preserved)
└── tests/                       # 22 automated Pytest test suites
```

---

## 11. Engineering Decisions & Evaluation Guide

Detailed architectural justifications and line-by-line code citations for all 8 evaluation questions are documented in [**`DECISIONS.md`**](DECISIONS.md):

| Question | Topic | Primary Code Reference | Summary of Architecture |
|---|---|---|---|
| **Q1** | Schema & Relationships | [`products/models.py`](products/models.py), [`orders/models.py`](orders/models.py) | Separation of `Product` and `Inventory`, `PROTECT` on historical orders, check constraints. |
| **Q2** | Retrieval & Indexing | [`assistant/tools.py`](assistant/tools.py#L7-L41) | Multi-field B-Tree indexing over sparse embeddings to ensure exact vehicle-model fitment. |
| **Q3** | Tool-Calling Loop | [`assistant/services.py`](assistant/services.py#L162-L308) | 4-step loop: system prompt, tool dispatch, live DB execution, and output grounding. |
| **Q4** | Price & Stock Grounding | [`assistant/tools.py`](assistant/tools.py#L44-L88) | Real-time database queries; client or LLM prices ignored during order creation. |
| **Q5** | Untrusted Supplier Data | [`assistant/services.py`](assistant/services.py#L14-L18) | Strict system prompt boundaries, structured JSON encapsulation, and tool permission gating. |
| **Q6** | Forecasting & Leakage | [`ml/train_and_forecast.py`](ml/train_and_forecast.py#L89-L106) | Strict historical slicing ($t < w$) prevents future data leakage; sequential lag computation. |
| **Q7** | Weak Forecast SKUs | [`ml/train_and_forecast.py`](ml/train_and_forecast.py#L65-L81) | Cold-start handling for 6-week SKUs (`BRK-1105`, `CHN-1006`) and festival curve alignment. |
| **Q8** | Weakest Area & Next Steps | [`DECISIONS.md`](DECISIONS.md#L141-L151) | Hybrid dense-sparse retrieval via `pgvector`, quantile regression forecasting, and Celery queues. |

---

<div align="center">

**Developed with precision for the VIKMO DealerDesk Assignment.**  
*Repository: [github.com/SHREE-ABIRAAMI/vikmo-dealerdesk](https://github.com/SHREE-ABIRAAMI/vikmo-dealerdesk) • Demo Walkthrough: [Google Drive Video](https://drive.google.com/file/d/1m3yPWlLj92S2MGF_kJkEa73yvJBF8foN/view?usp=sharing)*  
*Review the [API Contract](API_CONTRACT.md) or explore the live portal at `http://localhost:8000/`.*

</div>
