import { runBuyFlowBackend } from './buy_flow.js';

/**
 * 逐步加壓（直連 web:8000），觀察從「幾乎全成功」到「開始出現錯誤」的區間。
 *
 * 延遲 SLA：`buy_flow.js` 對每個請求使用 HTTP 逾時（預設 60s，環境變數 `BUY_HTTP_TIMEOUT`）。
 * 超過則 k6 視為請求失敗，`http_req_failed` / checks 會上升。
 *
 * 怎麼看結果：
 * - 終端機 summary：`http_req_failed`、`checks`（status is 200）
 * - 搭配 Remote Write：Grafana 畫 `rate(k6_http_reqs)`、`rate(k6_http_req_failed)`、P95
 *
 * 可選：在 thresholds 裡取消註解 `http_req_failed` + `abortOnFail`，當「失敗率」持續超過門檻時自動中止（約略當作拐點）。
 */
export const options = {
    scenarios: {
        ramp: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 15 },
                { duration: '30s', target: 30 },
                { duration: '30s', target: 60 },
                { duration: '30s', target: 120 },
                { duration: '30s', target: 250 },
                { duration: '30s', target: 500 },
                { duration: '30s', target: 1000 },
                { duration: '30s', target: 2000 },
                { duration: '30s', target: 3500 },
                { duration: '30s', target: 0 },
            ],
            gracefulRampDown: '30s',
        },
    },
    // 預設不設閾值：跑完整段 ramp，從 summary / Grafana 看何時出現錯誤。
    // 若要「失敗率持續超過約 3% 就自動停」，改為取消下面整段註解：
    // thresholds: {
    //     http_req_failed: [
    //         { threshold: 'rate<0.03', abortOnFail: true, delayAbortEval: '20s' },
    //     ],
    // },
};

export default function () {
    runBuyFlowBackend();
}
