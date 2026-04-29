## Prometheus 和 Grafana 介紹

Prometheus 和 Grafana 是現代後端系統（特別是雲原生、微服務架構）中非常常見的一組「監控 + 視覺化」工具，通常會一起使用。

- Prometheus: 收集 + 儲存 + 查詢 metrics
- Grafana: 把 metrics 畫成你看得懂的圖

### Prometheus 是什麼

Prometheus 是一個 監控系統 + 時序資料庫（Time Series DB）。

抓 metrics（指標）:

- 透過 HTTP 定期去抓服務的 `/metrics`
- 這種模式叫 pull model（拉取）

存時間序列資料:

- 每筆資料都有

```
CPU_usage{host="server1"} 0.65 @timestamp
```

查詢語言（PromQL）:

- 可以做像

```
rate(http_requests_total[5m])
```

告警（Alerting）:

- 搭配 Alertmanager 發送通知（Slack / Email）

### Grafana 是什麼

Grafana 是一個 資料視覺化工具。

連接資料來源（Data Source）:

- Prometheus
- MySQL / PostgreSQL
- Elasticsearch

畫 Dashboard:

- CPU 使用率
- QPS（每秒請求）
- 錯誤率

即時監控

- 幾秒更新一次圖表

### 兩者如何搭配

以搶票系統為例。

Prometheus 收：

- 每秒請求數（QPS）
- Redis latency
- 成功 / 失敗訂單數
- Lua script 執行時間

Grafana 顯示：

- 瞬間流量暴增圖
- 錯誤率飆高
- DB latency 上升

---

## 本專案的設定

### 服務端口

| 服務 | 端口 | 說明 |
| --- | --- | --- |
| Prometheus | `localhost:9090` | 指標查詢、抓取狀態 |
| Grafana | `localhost:3000` | Dashboard 視覺化 |

### Prometheus 抓取設定（`prometheus.yml`）

```yaml
scrape_configs:
  - job_name: 'fastapi-app'
    scrape_interval: 5s
    static_configs:
      - targets: ['web:8000']
```

每 5 秒從 FastAPI 的 `/metrics` 端點抓取指標，由 `prometheus_fastapi_instrumentator` 自動產生。

同時啟用 `--web.enable-remote-write-receiver`，讓 k6 可以在壓測期間把指標即時推送進來。

### Grafana 設定步驟

**1. 新增 Prometheus Data Source**

開啟 `http://localhost:3000`（預設帳密 `admin` / `admin`）

左側選單 → Connections → Data sources → Add new data source → 選 Prometheus

Connection URL 填入：
```
http://prometheus:9090
```

點 Save & test，看到綠色確認即完成。

**2. 匯入 k6 Dashboard**

左側選單 → Dashboards → New → Import → 輸入 Dashboard ID：
```
18030
```

選剛才建立的 Prometheus data source → Import。

此 Dashboard 包含 VUs、RPS、HTTP 延遲分佈、錯誤率等面板，專為 k6 Prometheus Remote Write 設計。

### 搭配 k6 即時觀測

執行 k6 時加上 `-o experimental-prometheus-rw` 參數，壓測期間指標即時推送到 Prometheus：

```bash
docker compose run --rm \
  -e K6_PROMETHEUS_RW_SERVER_URL=http://prometheus:9090/api/v1/write \
  k6 run -o experimental-prometheus-rw \
  /code/scripts/k6/test_nginx_rate_limit.js
```

**常用 PromQL 查詢**

| 用途 | PromQL |
| --- | --- |
| 即時 RPS | `rate(k6_http_reqs_total[15s])` |
| 即時失敗率 | `rate(k6_http_req_failed_total[15s])` |
| 429 限流速率 | `rate(k6_rate_limited_responses_total[15s])` |
| P95 延遲 | `k6_http_req_duration{quantile="0.95"}` |
| 搶票成功率 | `k6_purchase_success_rate` |

### 資料持久化（選用）

預設重啟 container 後 Grafana 設定會消失，在 `docker-compose.yml` 加上 volume 可永久保留：

```yaml
grafana:
  image: grafana/grafana:latest
  volumes:
    - grafana_data:/var/lib/grafana

volumes:
  grafana_data:
```
