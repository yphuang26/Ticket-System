import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter } from 'k6/metrics';

/** 供 Nginx 限流情境：在 threshold 使用 rate_limited_responses */
export const rateLimitedResponses = new Counter('rate_limited_responses');

/** 單次 POST /buy；逾時視為請求失敗（預設 60s，與可接受延遲 SLA 一致） */
function postBuy(baseUrl, opts = {}) {
    const url = `${baseUrl.replace(/\/$/, '')}/buy`;
    const timeout = opts.timeout ?? (__ENV.BUY_HTTP_TIMEOUT || '60s');
    return http.post(url, null, { timeout });
}

/**
 * 經 Nginx：驗證 limit_req / 429（預設打 http://nginx）
 */
export function runBuyFlowNginx(sleepSec = 0.05) {
    const baseUrl = __ENV.BASE_URL || 'http://nginx';
    const res = postBuy(baseUrl);
    if (res.status === 429) {
        rateLimitedResponses.add(1);
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
    check(res, {
        'status is 200': (r) => r.status === 200,
    });
    sleep(sleepSec);
}
