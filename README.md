## High-Concurrency Ticketing System

一個用來**模擬高併發搶票系統**的專案，針對以下主題做改善：

- **高併發下不超賣**
- **API 與 DB 解耦的事件流架構**
- **完整 observability（監控 + 壓測）**

技術棧：**FastAPI + Redis + PostgreSQL + Prometheus + Grafana + k6 + GitHub Actions (CI/CD)**

## 系統架構圖

![系統架構圖](system-architecture.png)

## 系統設計與技術亮點

- **Race Condition 解決方案（防止超賣）**
  - 使用 **Redis Lua Script** 原子化執行扣庫存（DECR）與推入訂單佇列（LPUSH）
  - 所有搶票請求經過 Lua 腳本，確保**不會出現負庫存、重複賣票，或庫存扣了但訂單未入佇列的中間狀態**

- **非同步持久化（提升吞吐量）**
  - API 收到成功搶票請求後，只負責把訂單寫入 Redis `order_queue`
  - **背景 worker** 從 queue 取出訂單，再寫入 PostgreSQL，達成 **API 先回應，資料庫由背景非同步寫入**的解耦
  - 寫入失敗時自動 retry 最多 3 次（exponential backoff），仍失敗則移至 `order_queue_failed` dead letter queue 保留，不遺失訂單

- **監控與可觀測性 (Observability)**
  - 透過 `prometheus_fastapi_instrumentator` 自動導出 FastAPI 指標
  - Prometheus 抓取指標，Grafana 可視化 **RPS、延遲、錯誤率**
  - 支援 k6 壓測結果以 **Prometheus Remote Write** 方式輸出

- **自動化部署 (CI/CD)**
  - 使用 **GitHub Actions** 將專案自動部署到 **AWS EC2**
  - 整合 Docker / docker-compose，方便一鍵啟動全套服務

## 專案架構概覽

- **`app/main.py`**：FastAPI 服務
  - `POST /buy`：搶票 API（呼叫 Redis Lua script 扣庫存 + 推入 `order_queue`）
  - `GET /stock`：查詢當前剩餘票數
- **`app/worker.py`**：背景 worker
  - 從 `order_queue` 消費訂單並寫入 PostgreSQL；含 retry 機制與 dead letter queue（`order_queue_failed`）監控告警
- **`scripts/k6/buy_flow.js`**：共用的 `/buy` 請求流程（供下列入口腳本 `import`）
- **`scripts/k6/test_nginx_rate_limit.js`**：經 **Nginx** 壓測，驗證 `limit_req` / 429
- **`scripts/k6/test_backend_capacity.js`**：直連 **web:8000**，測後端吞吐（不經 Nginx 限流）
- **`scripts/k6/test_backend_ramp_to_breakpoint.js`**：分階段提高 VU，觀察從近乎全成功到開始出錯（可選失敗率達標自動中止）
- **`scripts/k6/test_oversell.js`**：10,000 VU 同時搶 100 張票，teardown 驗證剩餘庫存恰好為 0，確認無超賣也無 race condition
- **`scripts/run_k6_and_plot.sh`**：一鍵執行壓測 + 自動生成結果圖（詳見下方）
- **`scripts/plot_k6_result.py`**：讀取 `k6_summary.json` 並生成視覺化圖表，在 Docker 內執行
- **`docker-compose.yml`**：一鍵啟動 web / worker / Redis / PostgreSQL / Prometheus / Grafana / k6 / plotter 服務

## 快速開始 (Local)

### 1. 啟動所有服務

```bash
git clone <your-repo-url>
cd Ticket-System
docker compose up -d
```

啟動後你將擁有：

- 頁面票數顯示：`http://localhost`
- Prometheus：`http://localhost:9090`
- Grafana：`http://localhost:3000`

### 2. 執行壓力測試 (k6)

使用 `run_k6_and_plot.sh` 一鍵執行壓測並自動生成結果圖：

```bash
bash scripts/run_k6_and_plot.sh nginx       # Nginx 限流驗證
bash scripts/run_k6_and_plot.sh backend     # 後端瞬間暴衝極限
bash scripts/run_k6_and_plot.sh breakpoint  # 逐步加壓找拐點
bash scripts/run_k6_and_plot.sh oversell    # 防超賣驗證
```

執行完後，對應的結果圖（`k6_nginx_result.png` 等）會出現在專案根目錄。

若只需執行壓測不需要畫圖：

```bash
docker compose run --rm k6 run /code/scripts/k6/test_nginx_rate_limit.js
docker compose run --rm k6 run /code/scripts/k6/test_backend_capacity.js
docker compose run --rm k6 run /code/scripts/k6/test_backend_ramp_to_breakpoint.js
docker compose run --rm k6 run /code/scripts/k6/test_oversell.js
```

`buy_flow.js` 預設對每個 `POST /buy` 使用 **60s HTTP 逾時**（可接受延遲 SLA）；超過即視為請求失敗。若要改門檻：

```bash
docker compose run --rm -e BUY_HTTP_TIMEOUT=45s k6 run /code/scripts/k6/test_backend_ramp_to_breakpoint.js
```

### 3. 將 k6 結果寫入 Prometheus，並用 Grafana 顯示

本專案的 `prometheus` 已在 `docker-compose.yml` 啟用 `--web.enable-remote-write-receiver`，可直接接收 k6 metrics。

先確保監控服務已啟動：

```bash
docker compose up -d prometheus grafana
```

再用 Prometheus Remote Write 模式執行 k6：

```bash
docker compose run --rm \
  -e K6_PROMETHEUS_RW_SERVER_URL=http://prometheus:9090/api/v1/write \
  k6 run -o experimental-prometheus-rw /code/scripts/k6/test_nginx_rate_limit.js
```

（測後端極限時可改為 `test_backend_capacity.js`。）

接著在 Grafana 設定 Prometheus Data Source（URL: `http://prometheus:9090`），即可建立 dashboard。

若在 Grafana 找不到 `rate_limited_responses`、`http_reqs`、`http_req_failed`，改查 `k6_` 前綴名稱（k6 remote write 匯入 Prometheus 時常見）。

建議先加這幾個查詢：

- 限流命中速率（429）：
  - `rate(k6_rate_limited_responses[1m])`
- 請求速率（RPS）：
  - `rate(k6_http_reqs[1m])`
- 失敗率（k6 將 429 視為 failed，屬預期）：
  - `avg(k6_http_req_failed)`
- 延遲 P95：
  - `histogram_quantile(0.95, sum(rate(k6_http_req_duration_bucket[1m])) by (le))`

## API 範例

- **搶票**

```bash
curl -X POST "http://localhost:8000/buy?user_id=user_123"
```

- **查詢庫存**

```bash
curl "http://localhost:8000/stock"
```

回應範例：

```json
{ "remaining_stock": 7 }
```

## 壓力測試結果

> 詳細說明與圖示請參考 [documents/k6.md](documents/k6.md)

### Nginx Rate Limiting（100 VUs × 60s）

![Nginx Rate Limit Result](k6_nginx_result.png)

驗證 Nginx `limit_req rate=10r/s burst=20` 的限流效果。100 VU 不間斷打 60 秒，共 112,582 次請求：

- **99.45%**（111,962 次）被 Nginx 攔截並回傳 429
- **0.55%**（620 次）通過限流並成功購票，與 Nginx 10 r/s × 60s 的理論上限完全吻合
- 後端 P95 延遲 11.6 ms，全程無 5xx 錯誤

### Backend Burst Capacity（spike to 5,000 VUs）

![Backend Capacity Result](k6_backend_result.png)

直連 FastAPI，在 2 秒內暴衝至 5,000 VU，觀察後端在極限流量下的行為。HTTP Failed（紅）代表 OS TCP accept queue 溢出造成的連線中斷，是後端被打超過承載上限的預期現象。

### Ramp to Breakpoint（15 → 3,500 VUs）

![Breakpoint Result](k6_breakpoint_result.png)

每 30 秒往上加一級 VU，直到失敗率超過 3% 自動中止。`Peak VUs` 即為系統拐點，超過此數後錯誤率快速上升。

### Oversell Prevention（10,000 VUs 搶 100 張票）

![Oversell Prevention Result](k6_oversell_result.png)

10,000 VU 同時搶 100 張票，teardown 驗證：
- ✓ **No Oversell**：剩餘庫存 ≥ 0，Redis Lua Script 原子性防止超賣
- ✓ **Full Sell-Through**：剩餘庫存 = 0，票券全數正確售出，無 race condition

## 可以延伸的方向（Future Work）

- 加入 **多場次 / 多商品** 的搶購邏輯
  - 用 **Message Queue（如 Kafka / RabbitMQ）** 取代 Redis List
- 加入 **分佈式鎖 / 分庫分表** 的設計實驗
- 撰寫更多壓測腳本，模擬不同流量模型（突刺流量、持續高壓等）
