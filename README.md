# VIKMO DealerDesk — AI/ML Intern Track

> **Selected Track:** `AI / ML Intern` (Track value: `aiml`)  
> **Submission Repository:** Public GitHub Repository  
> **5-Minute Video Walkthrough:** [https://youtu.be/placeholder-vikmo-dealerdesk-demo](https://youtu.be/placeholder-vikmo-dealerdesk-demo) *(Demo recording link placeholder)*  

---

## 1. Problem Statement & Solution

A Bengaluru distributor of motorcycle and car parts supplies 25 dealers across South India from a catalogue of 600 products. Managing operations through spreadsheets and phone calls led to four critical failures:
1. **Overselling stock:** Concurrent orders promise the last units to multiple dealers, and manual GST calculations create discrepancy in paise.
2. **Stale prices:** Supplier catalogue changes are copied by hand, causing prices to lag.
3. **Repetitive dealer inquiries:** Staff spend hours answering questions like *"Do you have brake pads for a Duke 390?"* or *"What is my stock?"*.
4. **Guesswork in reordering:** Reordering fails to account for promotion spikes, supplier lead times, and moving festival dates (Diwali).

**DealerDesk** solves all four issues with:
- A PostgreSQL-backed ordering backend with row-level locking, exact 18% GST calculation, and atomic status transitions.
- An automated supplier synchronisation pipeline handling cursor pagination, HTTP 429 `Retry-After`, and bounded 5xx retries.
- A grounded GenAI Dealer Assistant executing real backend tool calls (`search_parts`, `check_stock`, `create_draft_order`) with prompt-injection defences.
- An explainable, leakage-free ML demand forecast for 40 SKUs across 4 weeks with a deterministic safety-stock reorder engine.
- A modern, responsive B2B Dealer Portal interface.

---

## 2. Features Implemented

### Required Features (AI / ML Track)
- [x] **Backend Core (§4, §5, §6, §7.1):** Products, inventory, dealers, and draft order CRUD with strict contract error envelopes.
- [x] **GenAI Dealer Assistant (§9):** Multi-turn conversational agent with real tool calling, live database grounding, session isolation, and untrusted description security boundaries.
- [x] **ML Demand Forecasting (§10.1):** 4-week future forecast for 40 SKUs committed at [`ml/forecast.csv`](file:///c:/Users/SRS/Downloads/VIKMO%20DealerDesk%20Assignment/ml/forecast.csv) (160 rows).
- [x] **Reorder Suggestions API (§10.2):** Exact safety-stock formula `safety_stock = ceil(1.65 × σ × √L)` and live inventory lookup.
- [x] **Automated Tests:** 22 passing unit/integration tests with 100% pass rate.
- [x] **DECISIONS.md:** Complete, rigorous answers to all 8 evaluation questions with exact line-number citations.

### Bonus Features Implemented
- [x] **Order Engine Lifecycle (§7.2–§7.5):** Status flow `DRAFT → CONFIRMED → DISPATCHED → DELIVERED`, PostgreSQL row-locking stock deduction, atomic cancellation stock restore, unique `ORD-YYYYMMDD-NNNN` sequence, and `Idempotency-Key` conflict handling.
- [x] **Supplier Synchronisation (§8):** Full feed synchronization with exponential backoff, rate limit handling, duplicate SKU resolution by latest `updated_at`, invalid item filtering, and zero mutation of warehouse stock.
- [x] **Dealer Portal Frontend:** Polished, responsive B2B web application at `http://localhost:8000/`.

---

## 3. Technology Stack

- **Backend:** Python 3.11+, Django 5.2, Django REST Framework 3.18
- **Database:** PostgreSQL (with `psycopg` v3 and `dj-database-url`)
- **Machine Learning:** `scikit-learn` (`HistGradientBoostingRegressor`), `pandas`, `numpy`
- **GenAI Orchestration:** Multi-provider tool-calling architecture supporting Google Gemini (`gemini-1.5-flash`), OpenAI (`gpt-4o-mini`), Groq (`llama-3.1-8b-instant`), and deterministic grounded fallback
- **Testing:** `pytest`, `pytest-django`, `requests`
- **Frontend:** Responsive B2B single-page interface (served at `/`)

---

## 4. Project Directory Structure

```
VIKMO DealerDesk Assignment/
├── API_CONTRACT.md              # Authoritative API contract (Preserved)
├── DECISIONS.md                 # 8 AI/ML engineering decision answers
├── README.md                    # Project documentation
├── .env.example                 # Example environment variables
├── manage.py                    # Root Django management entrypoint
├── requirements.txt             # Linux-compatible dependencies
├── smoke_test.py                # Official company verification suite
├── VIKMO_DealerDesk_Assignment.pdf # Assignment brief (Preserved)
├── core/                        # Health check, exceptions, pagination, portal
│   ├── exceptions.py            # Standard contract error responses
│   ├── pagination.py            # Standard page-number pagination
│   └── templates/portal.html    # Dealer portal web application
├── products/                    # Product catalogue & Inventory models & APIs
│   ├── models.py                # Product and Inventory (OneToOne)
│   ├── serializers.py           # Product validation and stock serializer
│   ├── views.py                 # GET/POST/PATCH products, PUT inventory
│   └── urls.py
├── dealers/                     # Dealer management app
│   ├── models.py                # Dealer entity with credit limit
│   ├── serializers.py
│   └── views.py
├── orders/                      # Financial order engine & business services
│   ├── models.py                # Order, OrderItem, DailyOrderSequence, IdempotencyRecord
│   ├── services.py              # Financial calculations, row locking, transitions
│   └── views.py                 # Order endpoints
├── assistant/                   # GenAI Dealer Assistant
│   ├── models.py                # Conversation history persistence
│   ├── tools.py                 # search_parts, check_stock, create_draft_order
│   ├── services.py              # Tool-calling loop, prompt injection guard
│   └── views.py                 # POST /api/assistant/chat/
├── forecasting/                 # Forecasting & reorder suggestions APIs
│   ├── services.py              # Lead time demand, sigma, safety stock math
│   └── views.py                 # GET /api/forecast/{sku}/, GET /api/reorder-suggestions/
├── supplier/                    # Supplier catalogue synchronization
│   ├── services.py              # Paginated feed fetch, retries, atomic DB update
│   └── views.py                 # POST /api/sync/supplier/
├── ml/                          # Forecasting artifacts & pipeline
│   ├── forecast.csv             # Exactly 160 SKU-week predictions
│   └── train_and_forecast.py    # Leakage-free training & forecast script
├── data/                        # Company datasets (Preserved unchanged)
├── supplier_mock/               # Supplier mock server (Preserved)
├── starter/                     # Original starter backup (Preserved)
└── tests/                       # 22 automated test suites
```

---

## 5. Prerequisites & Quickstart Setup

### Prerequisites
- Python 3.11 or newer
- PostgreSQL instance running on port 5432 (or a hosted PostgreSQL URL, e.g., Neon / Supabase)

### 1. Installation
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure `DATABASE_URL` points to your PostgreSQL database:
```env
DATABASE_URL=postgres://postgres:postgres@localhost:5432/dealerdesk
SUPPLIER_API_URL=http://127.0.0.1:8099
SUPPLIER_API_KEY=dev-supplier-key
DJANGO_SECRET_KEY=dev-secret-key-vikmo-dealerdesk-2026

# Optional: Add your LLM provider key if testing external cloud models
GEMINI_API_KEY=
OPENAI_API_KEY=
GROQ_API_KEY=
```

### 3. Migrations & Seeding
```bash
python manage.py migrate --noinput
python manage.py seed_data
python manage.py seed_data   # Safe to run twice: 100% idempotent
```

### 4. Start Application
```bash
python manage.py runserver 0.0.0.0:8000 --noreload
```

- **Health check:** `curl http://localhost:8000/api/health/` → `{"status": "ok"}`
- **Dealer Portal UI:** Open `http://localhost:8000/` in your browser.

---

## 6. Verification & Automated Testing

### Running the Official Smoke Test
In a separate terminal, start the supplier mock if testing supplier sync:
```bash
python supplier_mock/mock_supplier.py
```

Run the smoke test for the **AI / ML Intern track**:
```bash
python smoke_test.py --base-url http://localhost:8000 --track aiml
```
*Result:* **`10/10 checks passed.`**

Run the smoke test checking all parts (including order engine & supplier sync):
```bash
python smoke_test.py --base-url http://localhost:8000 --all
```
*Result:* **`12/12 checks passed.`**

### Running the Pytest Suite
```bash
python -m pytest -v
```
*Result:* **`22 passed in 15.16s`** across all unit and integration test suites.

---

## 7. Machine Learning & Forecasting Architecture

### Historical Validation vs Baselines
Validation was conducted on a holdout split of the last 4 historical weeks (`2026-08-31` to `2026-09-21`), ensuring zero future data leakage:

| Model / Approach | MAE | RMSE | WAPE (%) |
|---|---|---|---|
| Baseline 1: Last Observed Value | 11.72 | 19.58 | 34.41% |
| Baseline 2: 4-Week Moving Average | 8.76 | 15.01 | 25.71% |
| Baseline 3: Same Week Last Year (Lag 52) | 12.27 | 19.72 | 36.01% |
| **DealerDesk Ensemble Model** | **6.49** | **9.37** | **19.04%** |

### Key Modelling Innovations
1. **Diwali Festival Curve:** Diwali shifts each year (2024-11-01, 2025-10-21, 2026-11-08). Demand surges start 5 weeks prior. The model aligns demand to festival proximity (`weeks_to_diwali`) rather than calendar months.
2. **Promotions Uplift:** Promotional weeks in historical data generate ~2.2x demand lift. The model incorporates known future planned promotions from `data/promo_calendar.csv`.
3. **Cold-Start Handling:** New SKUs with only 6 weeks of data (`BRK-1105`, `CHN-1006`) fall back to non-promo exponential moving averages with global shrinkage.

### Reorder Formula Implementation
In [`forecasting/services.py`](file:///c:/Users/SRS/Downloads/VIKMO%20DealerDesk%20Assignment/forecasting/services.py):
- `L` = Supplier lead time in weeks from `data/lead_times.csv`
- `lead_time_demand` = $\sum_{w=1}^{L} \text{forecast\_units}_w$
- `sigma` = Sample standard deviation ($ddof=1$) of weekly units sold over the last 12 historical weeks
- $\text{safety\_stock} = \lceil 1.65 \times \sigma \times \sqrt{L} \rceil$
- $\text{reorder\_point} = \text{lead\_time\_demand} + \text{safety\_stock}$
- $\text{reorder\_qty} = \max(0, \lceil \text{reorder\_point} - \text{current\_stock} \rceil)$

---

## 8. GenAI Dealer Assistant Design

- **Tool Execution:** Real backend functions connected to PostgreSQL:
  1. `search_parts`: Queries catalogue by query, vehicle, and category.
  2. `check_stock`: Queries live available inventory and current price.
  3. `create_draft_order`: Validates input and creates a DRAFT order.
- **Grounding:** Price, stock, and order totals are never generated from LLM hallucination. Values are extracted directly from database tool responses.
- **Security & Least Privilege:** System prompt and tool definition isolate catalogue text as data, forbidding confirmation or cancellation of orders through the chat interface.

---

## 9. Assumptions & Known Limitations

- **Database Engine:** Requires PostgreSQL. Concurrency tests and atomic row locking (`select_for_update()`) rely on PostgreSQL semantics.
- **Single Currency:** All financial figures are in INR (₹) with 2 decimal places.
- **Tax Policy:** 18% GST rounded `ROUND_HALF_UP` per line item.

For comprehensive technical answers, see [**`DECISIONS.md`**](file:///c:/Users/SRS/Downloads/VIKMO%20DealerDesk%20Assignment/DECISIONS.md).
