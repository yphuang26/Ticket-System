import http from 'k6/http';
import { check } from 'k6';
import { runBuyFlowBackend, resetStock } from './buy_flow.js';

/**
 * 逐步加壓（直連 web:8000），找出「幾乎全成功」到「開始出現錯誤」的拐點。
 *
 * 庫存預設為 10,000,000（環境變數 INITIAL_STOCK 可覆寫），
 * 確保整段 ramp 期間庫存充足，錯誤率的上升反映真實後端瓶頸而非售罄。
 *
 * 延遲 SLA：buy_flow.js 對每個請求使用 HTTP 逾時（預設 60s，環境變數 BUY_HTTP_TIMEOUT）。
 * 超過則 k6 視為請求失敗，http_req_failed / checks 會上升。
 *
 * 怎麼看結果：
 * - 終端機 summary：http_req_failed、checks、purchase_success_rate
 * - 搭配 Remote Write：Grafana 畫 rate(k6_http_reqs)、rate(k6_http_req_failed)、P95
 *
 * 自動拐點偵測：當失敗率持續超過 3%（觀察 20s 後），測試自動中止。
 * 若想跑完整段以觀察完整曲線，可將 thresholds 整段註解掉。
 */
export const options = {
    scenarios: {
        ramp: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 15   },
                { duration: '30s', target: 30   },
                { duration: '30s', target: 60   },
                { duration: '30s', target: 120  },
                { duration: '30s', target: 250  },
                { duration: '30s', target: 500  },
                { duration: '30s', target: 1000 },
                { duration: '30s', target: 2000 },
                { duration: '30s', target: 3500 },
                { duration: '30s', target: 0    },
            ],
            gracefulRampDown: '30s',
        },
    },
    thresholds: {
        // 失敗率持續超過 3% 時自動中止，拐點即為此時的 VU 數
        http_req_failed: [
            { threshold: 'rate<0.03', abortOnFail: true, delayAbortEval: '20s' },
        ],
        // 業務層：搶票成功率下降比 HTTP 失敗率更早反映後端壓力
        purchase_success_rate: [
            { threshold: 'rate>0.97', abortOnFail: true, delayAbortEval: '20s' },
        ],
    },
};

/** 壓測前重置庫存，確保整段 ramp 庫存充足 */
export function setup() {
    const initialStock = parseInt(__ENV.INITIAL_STOCK || '10000000');
    resetStock(initialStock);
    return { initialStock };
}

export default function () {
    runBuyFlowBackend();
}

/** 壓測後驗證無超賣 */
export function teardown(data) {
    const baseUrl = __ENV.BASE_URL || 'http://web:8000';
    const res = http.get(`${baseUrl}/stock`);
    const remaining = parseInt(res.json('remaining_stock'));
    check(res, {
        'no oversell (remaining_stock >= 0)': () => remaining >= 0,
    });
    console.log(`[teardown] 初始庫存=${data.initialStock}，剩餘=${remaining}，已購=${data.initialStock - remaining}`);
}
