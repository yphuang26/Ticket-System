import { runBuyFlowNginx } from './buy_flow.js';

// 觸發 Nginx limit_req，預期出現 429；預設 BASE_URL=http://nginx（見 buy_flow.js）
export const options = {
    vus: 100,
    duration: '10s',
    thresholds: {
        checks: ['rate>0.95'],
        rate_limited_responses: ['count>0'],
    },
};

export default function () {
    runBuyFlowNginx();
}
