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
