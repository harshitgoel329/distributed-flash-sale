```markdown
# ⚡ Distributed Flash-Sale Engine
> High-throughput, event-driven inventory reservation engine built to handle extreme concurrency spikes with zero overselling, sub-5ms atomic stock decrements, and decoupled asynchronous persistence.

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Redis-7.0+-DC382D?style=for-the-badge&logo=redis&logoColor=white" />
  <img src="https://img.shields.io/badge/RabbitMQ-3.13+-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-16+-336791?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" />
</p>

---

## 📌 Problem Statement

During high-profile flash sales (e.g., Black Friday or limited product drops), traditional transactional architectures fall prey to two fatal failure modes:
1. **Database Bottlenecks & Deadlocks:** Executing `UPDATE items SET stock = stock - 1 WHERE id = ? AND stock > 0` directly on relational tables results in heavy disk I/O, table/row lock contention, and cascading timeout failures.
2. **Race Conditions & Overselling:** Under thousands of concurrent requests, asynchronous checks create critical race conditions where the system confirms more orders than available inventory.

This engine solves these issues by shifting the synchronization layer into **single-threaded, atomic in-memory scripts (Redis Lua)**, buffering write pressure using **AMQP message queues (RabbitMQ)**, and streaming live fulfillment updates over **WebSockets**.

---

## 🏛️ System Architecture

```text
                                  +-----------------------+
                                  |   React 18 + TS UI    |
                                  |  (Live Dashboard)     |
                                  +-----------+-----------+
                                        ▲     │
                         WebSocket Feed │     │ HTTP POST /reserve
                      (Order Confirmed) │     │ (X-Idempotency-Key)
                                        │     ▼
                                  +-----+-----+-----------+
                                  |   FastAPI Gateway     |
                                  |   (Stateless REST)    |
                                  +-----+-----------+-----+
                                        │           │
                     1. Atomic Lua Script           │ 2. Publish Order Event
                        (Check & Decr)              │    (Persistent Delivery)
                                        ▼           ▼
                           +------------+--+     +--+------------+
                           |  Redis Cache  |     |  RabbitMQ     |
                           |  - Stock Keys |     |  - Task Queue |
                           |  - Pub/Sub WS |     +-------+-------+
                           +---------------+             │
                                                         │ 3. Consume
                                                         ▼
                                                 +-------+-------+
                                                 | Worker Engine |
                                                 | (Async Python)|
                                                 +-------+-------+
                                                         │
                                           4. ACID Batch │ 5. Trigger Redis Pub/Sub
                                              Commit     │    (For WebSockets)
                                                         ▼
                                                 +-------+-------+
                                                 | PostgreSQL 16 |
                                                 | Order Ledger  |
                                                 +---------------+

```

---

## ⚙️ Engineering Highlights & Design Patterns

### 1. In-Memory Atomic Reservation (`Redis + Lua`)

To eliminate race conditions without touching PostgreSQL during the initial request spike, stock validation and decrement operations are bundled into an atomic Lua script:

* The Lua script executes as a single transaction on Redis's single-threaded event loop.
* Stock is decremented only if `current_stock >= requested_quantity`.
* Zero locking overhead, sub-millisecond execution time, and a 100% guarantee against negative inventory counts.

### 2. Decoupled Asynchronous Persistence (`RabbitMQ`)

* Successful reservations push an order payload to a durable `order_processing_queue`.
* FastAPI immediately returns `HTTP 200/202 (RESERVED)` to the client without waiting for disk writes.
* Dedicated background workers asynchronously consume messages with backpressure control (`prefetch_count=10`) and write confirmed orders to PostgreSQL.

### 3. Distributed Idempotency Protection

* Every checkout attempt requires a client-generated UUID in the `X-Idempotency-Key` header.
* Redis caches the response of each unique idempotency key with an expiration window, ensuring duplicate client submissions or retried network requests never result in duplicate orders.

### 4. Real-Time Event Pipeline (`Redis Pub/Sub -> WebSocket`)

* Once a worker successfully commits an order to PostgreSQL, it publishes a notification to a Redis Pub/Sub channel.
* The WebSocket gateway intercepts this event and pushes the live status transition directly to the user's browser without polling.

---

## 📊 Concurrency Load Benchmark (Locust)

The system was evaluated under an aggressive load test simulating **200 concurrent users** issuing thousands of simultaneous checkout attempts against an inventory of **100 units**.

```text
========================================================================================
Type     Name                   # reqs      # fails |    Avg   Min   Max   Med |  req/s
--------|----------------------|-------|------------|-------|-----|-----|-----|---------
POST     /api/v1/orders/reserve   8,781   8,681(98%) |    171    13   712   160 |  617.12
========================================================================================
* 409 Conflict Responses:  8,630 (Handled stock exhaustion safely)
* Successful Ingestion:    100 (100% inventory claimed)
* Database Verification:   SELECT count(*) FROM orders WHERE status='CONFIRMED'; => 100
* Overselling Rate:        0.00% (Strict zero-oversell invariant maintained)
========================================================================================

```

---

## 📁 Repository Structure

```text
distributed-flash-sale/
├── backend/
│   ├── app/
│   │   ├── api/             # REST routing & WebSocket connections
│   │   ├── core/            # Database engine, Redis clients, RabbitMQ channels
│   │   ├── models/          # SQLAlchemy schemas (Orders, Status Enums)
│   │   ├── services/        # Atomic Lua scripts & stock reservation services
│   │   ├── workers/         # Background RabbitMQ queue consumers
│   │   └── main.py          # FastAPI application entrypoint
│   ├── Dockerfile           # Multi-stage Python build
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Real-time dashboard with WebSocket subscription
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml       # Complete multi-container orchestration
├── locustfile.py            # High-concurrency stress test suite
└── README.md

```

---

## 🚀 Getting Started

### Prerequisites

* [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running.
* [Node.js (LTS)](https://nodejs.org) and [Python 3.11+](https://www.python.org).

### 1. Clone & Start Infrastructure

```bash
git clone [https://github.com/harshitgoel329/distributed-flash-sale.git](https://github.com/harshitgoel329/distributed-flash-sale.git)
cd distributed-flash-sale

# Spin up Postgres, Redis, RabbitMQ, FastAPI API, and Workers
docker compose up --build -d

```

### 2. Initialize Product Inventory

Seed 100 items into the Redis in-memory cache:

```bash
curl -X POST http://localhost:8000/api/v1/products/init \
  -H "Content-Type: application/json" \
  -d '{"product_id": "prod_phone_123", "stock": 100}'

```

### 3. Start the Frontend Dashboard

```bash
cd frontend
npm install
npm run dev

```

Open **[http://localhost:5173](http://localhost:5173)** to access the live dashboard.

### 4. Run Concurrency Benchmark

Open a separate terminal in the root directory:

```bash
pip install locust
locust -f locustfile.py --headless -u 200 -r 50 -t 15s --host http://localhost:8000

```

### 5. Verify PostgreSQL Data Integrity

```bash
docker exec -it flashsale_postgres psql -U postgres -d flashsale_db -c "SELECT status, count(*) FROM orders GROUP BY status;"

```

---

## 📜 License

This project is open-source and available under the [MIT License](https://www.google.com/search?q=LICENSE).

```

```