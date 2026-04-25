import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate } from 'k6/metrics';

/** 供 Nginx 限流情境：在 threshold 使用 rate_limited_responses */
export const rateLimitedResponses = new Counter('rate_limited_responses');

/**
 * 業務層成功率：HTTP 200 且 body.status === 'success'。
 * 注意：API 對「售罄」也回傳 HTTP 200，故純看 http_req_failed 無法反映真實搶票結果。
 */
export const purchaseSuccessRate = new Rate('purchase_success_rate');

/**
 * 售罄率：HTTP 200 且 body.status === 'fail'（庫存耗盡）。
 */
export const purchaseSoldOutRate = new Rate('purchase_sold_out_rate');

/**
 * 單次 POST /buy；逾時視為請求失敗（預設 60s，與可接受延遲 SLA 一致）。
 * user_id 使用 VU 編號 + iteration 編號組成，確保每次請求身份唯一。
 */
function postBuy(baseUrl, opts = {}) {
    const url = `${baseUrl.replace(/\/$/, '')}/buy`;
    const timeout = opts.timeout ?? (__ENV.BUY_HTTP_TIMEOUT || '60s');
    const userId = `vu${__VU}_iter${__ITER}`;
    return http.post(`${url}?user_id=${userId}`, null, { timeout, tags: { name: url } });
}

/**
 * 重置庫存，供各測試腳本的 setup() 呼叫。
 * 預設打 web:8000（直連，不經 Nginx 限流）。
 */
export function resetStock(stock, backendUrl = 'http://web:8000') {
    const url = `${backendUrl.replace(/\/$/, '')}/admin/reset?stock=${stock}`;
    const res = http.post(url);
    check(res, { 'reset stock ok': (r) => r.status === 200 });
    return res;
}

/**
 * 經 Nginx：驗證 limit_req / 429（預設打 http://nginx）
 */
export function runBuyFlowNginx(sleepSec = 0.05) {
    const baseUrl = __ENV.BASE_URL || 'http://nginx';
    const res = postBuy(baseUrl);

    if (res.status === 429) {
        rateLimitedResponses.add(1);
        // 被限流視為未成功搶票，不計入業務指標
        purchaseSuccessRate.add(false);
        purchaseSoldOutRate.add(false);
    } else {
        const body = res.json();
        const isSuccess = body?.status === 'success';
        const isSoldOut = body?.status === 'fail';
        purchaseSuccessRate.add(isSuccess);
        purchaseSoldOutRate.add(isSoldOut);
        check(res, {
            'body has status field': () => body?.status !== undefined,
        });
    }

    check(res, {
        'status is 200 or 429': (r) => r.status === 200 || r.status === 429,
    });
    sleep(sleepSec);
}

/**
 * 直連 web：測後端吞吐（預設打 http://web:8000，不經 Nginx 限流）
 */
export function runBuyFlowBackend(sleepSec = 0.01) {
    const baseUrl = __ENV.BASE_URL || 'http://web:8000';
    const res = postBuy(baseUrl);

    if (res.body === null) {
        // connection reset / network error；http_req_failed 會自動計入，不需額外讓 check 失敗
        purchaseSuccessRate.add(false);
        purchaseSoldOutRate.add(false);
        sleep(sleepSec);
        return;
    }

    const body = res.json();
    const isSuccess = body?.status === 'success';
    const isSoldOut = body?.status === 'fail';

    purchaseSuccessRate.add(isSuccess);
    purchaseSoldOutRate.add(isSoldOut);

    check(res, {
        'status is 200': (r) => r.status === 200,
        'body has status field': () => body?.status !== undefined,
    });
    sleep(sleepSec);
}
