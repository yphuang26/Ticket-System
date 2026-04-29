import http from 'k6/http';
import { check } from 'k6';
import { runBuyFlowBackend, resetStock } from './buy_flow.js';

/**
 * 多人搶少票場景：驗證高並發下不發生超賣，且票券能被正確售完。
 *
 * 情境：10,000 VU 同時搶 100 張票。
 * 絕大多數請求會因庫存耗盡而收到 status=fail（售罄），
 * 測試結束後驗證剩餘庫存恰好為 0：
 *   - remaining > 0 → 有 race condition 導致部分票無法售出
 *   - remaining < 0 → 超賣（oversell）
 *   - remaining == 0 → 正確
 */
export const options = {
    scenarios: {
        rush: {
            executor: 'constant-vus',
            vus: 10000,
            duration: '10s',
        },
    },
    thresholds: {
        // teardown check 必須全數通過，確保 CI/CD 能正確攔截超賣或 race condition
        checks: ['rate==1.0'],
        // 絕大多數請求應收到售罄回應（確認測試確實跑在搶票壓力情境）
        purchase_sold_out_rate: ['rate>0.99'],
    },
};

const INITIAL_STOCK = parseInt(__ENV.INITIAL_STOCK || '100');

export function setup() {
    resetStock(INITIAL_STOCK);
    return { initialStock: INITIAL_STOCK };
}

export default function () {
    runBuyFlowBackend(0); // 不 sleep，最大並發壓力
}

export function handleSummary(data) {
    return { '/code/k6_summary.json': JSON.stringify(data, null, 2) };
}

export function teardown(data) {
    const baseUrl = __ENV.BASE_URL || 'http://web:8000';
    const res = http.get(`${baseUrl}/stock`);
    const remaining = parseInt(res.json('remaining_stock'));
    check(res, {
        'no oversell (remaining_stock >= 0)':   () => remaining >= 0,
        'no under-sell (remaining_stock == 0)': () => remaining === 0,
    });
    console.log(`[teardown] 初始庫存=${data.initialStock}，剩餘=${remaining}，已購=${data.initialStock - remaining}`);
}
