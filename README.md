# High-Throughput Distributed Flash-Sale Engine

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg?style=flat&logo=Redis&logoColor=white)](https://redis.io)
[![RabbitMQ](https://img.shields.io/badge/RabbitMQ-3.13+-FF6600.svg?style=flat&logo=RabbitMQ&logoColor=white)](https://www.rabbitmq.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg?style=flat&logo=PostgreSQL&logoColor=white)](https://www.postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat&logo=Docker&logoColor=white)](https://www.docker.com)

A distributed, event-driven flash-sale inventory reservation engine engineered to eliminate race conditions, prevent inventory overselling, and handle high-concurrency checkout spikes with sub-5ms in-memory latency.

---

## Architecture Overview

[ React 18 + TS Client ]
│ (HTTP POST / WebSocket)
▼
[ FastAPI Async Gateway ]
│
┌───┴────────────────────────────┬────────────────────────────┐
▼                                ▼                            ▼
[ Redis Cluster ]            [ RabbitMQ Queue ]           [ PostgreSQL 16 ]

Atomic Lua Decrement       - order_processing_queue   - ACID Transaction Ledger

Idempotency Cache          - Asynchronous Persistence   - Indexed Relational Store

Pub/Sub Live Stream               │
▼
[ Async Worker Consumer ]

---

## Key System Design Highlights

* **Atomic Stock Decrements (Redis Lua):** Offloaded inventory checks and decrement locks from the persistent database to atomic in-memory Lua scripts executed directly on Redis. This eliminates race conditions without slow row-level locking.
* **Asynchronous Order Ingestion:** Decoupled reservation requests from database disk writes via RabbitMQ message queues. The API responds immediately with order reservation status, preventing request timeouts during traffic spikes.
* **Idempotency Protection:** Implemented distributed idempotency checking using client-supplied `X-Idempotency-Key` headers stored in Redis to guarantee exactly-once order placement under network retries.
* **Real-Time Event Streaming:** Persisted order confirmations trigger Redis Pub/Sub events that stream directly to connected React clients via WebSockets.
* **Validated Concurrency (Zero Overselling):** Benchmarked under high concurrency using Locust (200 concurrent users, ~8,700 requests in 15 seconds) verifying exactly 100 successful purchases with zero stock overselling.

---

## Concurrency Benchmark Results

Simulated load test output executing 200 concurrent virtual users over a 15-second surge against an inventory of 100 items:

```text
Total Requests Sent:    8,781
Successful Checkouts:   100 (100% of available stock)
Rejected (409 Conflict): 8,630 (Stock exhausted protection)
Database Order Ledger:  Exactly 100 CONFIRMED records (0 oversold)

distributed-flash-sale/
├── backend/
│   ├── app/
│   │   ├── api/            # REST and WebSocket endpoints
│   │   ├── core/           # Database, Redis, and RabbitMQ clients
│   │   ├── models/         # SQLAlchemy 2.0 async schemas
│   │   ├── services/       # Inventory business logic & Lua scripts
│   │   └── workers/        # RabbitMQ background order persistence worker
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React 18 + Vite + TypeScript dashboard
├── docker-compose.yml      # Local multi-service container orchestration
├── locustfile.py           # Concurrency stress benchmark suite
└── README.md

Local Setup & Execution
1. Prerequisites
Docker Desktop

Node.js (LTS)

Python 3.11+

2. Launch Infrastructure via Docker Compose

docker compose up --build -d

3. Initialize Product Inventory
Seed 100 test units into Redis:

Bash
curl -X POST http://localhost:8000/api/v1/products/init \
  -H "Content-Type: application/json" \
  -d '{"product_id": "prod_phone_123", "stock": 100}'

4. Run the React Client
Bash
cd frontend
npm install
npm run dev
Open http://localhost:5173 to test live reservations.

5. Run the Concurrency Load Test
From the project root:

Bash
locust -f locustfile.py --headless -u 200 -r 50 -t 15s --host http://localhost:8000
6. Verify Database Integrity
Bash
docker exec -it flashsale_postgres psql -U postgres -d flashsale_db -c "SELECT status, count(*) FROM orders GROUP BY status;"

---

