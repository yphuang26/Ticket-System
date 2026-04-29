import { runBuyFlowNginx, resetStock } from './buy_flow.js';

/**
 * 觸發 Nginx limit_req，預期出現 429；預設 BASE_URL=http://nginx（見 buy_flow.js）
 *
 * 注意：k6 container 內所有 VU 共用同一個來源 IP，
 * Nginx 的 per-IP rate limit（10 r/s）實際上是對全部 VU 共享的，
 * 不是每個 VU 各自享有 10 r/s。
 * 因此 100 VU × no sleep 必定觸發大量 429，符合「驗證限流機制有效」的目的，
 * 但無法模擬「多個真實用戶各自觸發自身 rate limit」的場景。
 */
export const options = {
    vus: 100,
    duration: '60s',
    thresholds: {
        // 所有回應必須是合法狀態（200 或 429），不允許 5xx 或逾時
        checks: ['rate>0.95'],
        // 限流機制必須實際觸發
        rate_limited_responses: ['count>0'],
        // 後端仍存活且限流有效壓制成功率：
        //   rate>0    → 後端還活著，有請求通過限流並成功（避免後端崩潰時誤判限流正常）
        //   rate<0.20 → 限流確實壓制了成功率（100 VU × 60s，nginx burst=20，理論上限約 620 次）
        purchase_success_rate: ['rate>0', 'rate<0.20'],
    },
};

/** 壓測前重置庫存（呼叫 web:8000，繞過 Nginx 限流） */
export function setup() {
    resetStock(100000, 'http://web:8000');
}

export default function () {
    runBuyFlowNginx();
}

export function handleSummary(data) {
    return {
        // k6 container 內 /code 對應專案根目錄，壓測結束後自動寫出 JSON
        '/code/k6_summary.json': JSON.stringify(data, null, 2),
        // 不覆寫 stdout → k6 仍然印出預設的文字摘要
    };
}
