import http from 'k6/http';
import { check } from 'k6';
import { runBuyFlowBackend, resetStock } from './buy_flow.js';

// 後端極限（不經 Nginx）；預設 BASE_URL=http://web:8000
//
// 目的：在瞬間暴衝流量下，確認後端 HTTP 層的穩定性與最大吞吐。
// 庫存預設為 1,000,000（環境變數 INITIAL_STOCK 可覆寫），
// 確保測試期間不因庫存耗盡而讓所有請求退化成「已售罄」的 early return，
// 才能真正壓到後端業務邏輯。
export const options = {
    scenarios: {
        ramp: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2s',  target: 0    },
                { duration: '2s',  target: 5000 }, // 瞬間暴衝
                { duration: '5s',  target: 3000 },
                { duration: '5s',  target: 1000 },
                { duration: '2s',  target: 500  },
                { duration: '2s',  target: 200  },
                { duration: '2s',  target: 0    },
            ],
            gracefulRampDown: '30s',
        },
    },
    thresholds: {
        // HTTP 層：幾乎所有請求都要拿到回應（允許少量 timeout）
        checks:            ['rate>0.95'],
        // 業務成功率（會搶到票的比例）：有庫存時應 > 80%
        purchase_success_rate: ['rate>0.80'],
    },
};

/** 壓測前重置庫存，確保測試結果反映真實業務壓力而非 early-return 路徑 */
export function setup() {
    const initialStock = parseInt(__ENV.INITIAL_STOCK || '1000000');
    resetStock(initialStock);
    return { initialStock };
}

export default function () {
    runBuyFlowBackend();
}

export function handleSummary(data) {
    return { '/code/k6_summary.json': JSON.stringify(data, null, 2) };
}

/** 壓測後驗證無超賣：剩餘庫存必須 >= 0 */
export function teardown(data) {
    const baseUrl = __ENV.BASE_URL || 'http://web:8000';
    const res = http.get(`${baseUrl}/stock`);
    const remaining = parseInt(res.json('remaining_stock'));
    check(res, {
        'no oversell (remaining_stock >= 0)': () => remaining >= 0,
    });
    console.log(`[teardown] 初始庫存=${data.initialStock}，剩餘=${remaining}，已購=${data.initialStock - remaining}`);
}
