# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A high-concurrency ticket purchasing system built with FastAPI, Redis, PostgreSQL, Nginx, Prometheus, and Grafana. The core design solves the overselling problem using atomic Redis Lua scripts with async order persistence via a background worker.

## Commands

### Start / Stop Services

```bash
docker compose up -d          # Start all services
docker compose down           # Stop all services
docker compose logs -f web    # Tail logs for a specific service
```

### Run Load Tests (k6)

```bash
# Rate limiting test (through Nginx on port 80)
docker compose run --rm k6 run /code/scripts/k6/test_nginx_rate_limit.js

# Backend capacity test (direct to FastAPI on port 8000)
docker compose run --rm k6 run /code/scripts/k6/test_backend_capacity.js

# Ramp-to-breakpoint test
docker compose run --rm k6 run /code/scripts/k6/test_backend_ramp_to_breakpoint.js

# Oversell prevention test
docker compose run --rm k6 run /code/scripts/k6/test_oversell.js

# With Prometheus remote write for live metrics
docker compose run --rm \
  -e K6_PROMETHEUS_RW_SERVER_URL=http://prometheus:9090/api/v1/write \
  k6 run -o experimental-prometheus-rw /code/scripts/k6/test_backend_capacity.js
```

### API (manual testing)

```bash
curl -X POST "http://localhost:8000/buy" -H "Content-Type: application/json" -d '{"user_id": "user_1"}'
curl "http://localhost:8000/stock"
curl -X POST "http://localhost:8000/admin/reset?stock=100"
```

## Architecture

### Services (docker-compose.yml)

| Service | Port | Role |
|---|---|---|
| nginx | 80 | Reverse proxy, rate limiting (10 r/s per IP, burst=20, returns 429) |
| web | 8000 | FastAPI app — ticket purchase API + static UI |
| worker | — | Background process — drains Redis order queue into PostgreSQL |
| redis | 6379 | Atomic operations (Lua script) + order queue |
| db | 5432 | PostgreSQL — persistent order storage |
| prometheus | 9090 | Metrics scraping (FastAPI at 5s intervals) |
| grafana | 3000 | Dashboards |
| k6 | — | On-demand load testing |

### Request Flow

```
Client → Nginx (rate limit) → FastAPI → Redis Lua script (atomic decrement)
                                              ↓ (success)
                                        Redis order_queue (LPUSH)
                                              ↓
                                        Worker (BRPOP) → PostgreSQL
```

### Key Design Decisions

- **Oversell prevention**: `app/scripts/buy_ticket.lua` — a single Redis Lua script atomically checks `ticket_stock > 0` and decrements it. This runs as a single transaction with no race conditions.
- **Async persistence**: The API pushes a JSON order to the `order_queue` Redis list and returns immediately. The worker (`app/worker.py`) pulls from the queue and writes to PostgreSQL, decoupling API latency from DB write latency.
- **Redis data structures**: `ticket_stock` (string counter), `order_queue` (list used as a queue with LPUSH/BRPOP).

### App Code Layout

- `app/main.py` — FastAPI routes: `POST /buy`, `GET /stock`, `POST /admin/reset`, `GET /`
- `app/worker.py` — infinite loop consuming `order_queue` from Redis and persisting to DB
- `app/models.py` — SQLAlchemy `Order` model
- `app/database.py` — DB engine and session factory
- `app/logger.py` — JSON-structured logger
- `app/scripts/buy_ticket.lua` — Redis Lua script loaded at startup via `SCRIPT LOAD`
- `app/static/` — Frontend HTML/JS/CSS served by FastAPI

### CI/CD

`.github/workflows/deploy.yml` deploys manually (`workflow_dispatch`) to an AWS EC2 instance via SSH — it pulls from GitHub and runs `docker compose up -d --build`.
