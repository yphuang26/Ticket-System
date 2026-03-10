# High-Concurrency Ticketing System

這是一個基於 FastAPI + Redis + PostgreSQL 的高併發搶票系統。

## 技術亮點

### Race Condition 解決方案

利用 Redis Lua Script 實現原子化扣庫存，防止超賣。

### 非同步持久化

使用 Redis List 作為緩衝，解耦 API 請求與資料庫寫入，提升系統吞吐量。

### 監控功能

整合 Prometheus & Grafana，實現 RPS 與 API 延遲的即時監控。

### 自動化維運(CI/CD)

透過 GitHub Actions 實作自動化部署到 AWS EC2。

## 壓力測試結果

## 快速開始

- `git clone`
- `docker compose up`
- `docker compose run --rm k6 run /code/scripts/test_buy.js`
