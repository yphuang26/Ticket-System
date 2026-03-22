import { runBuyFlowBackend } from './buy_flow.js';

// 後端極限（不經 Nginx）；預設 BASE_URL=http://web:8000
export const options = {
    scenarios: {
        ramp: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '2s', target: 0 },
                { duration: '2s', target: 5000 }, // 瞬間暴衝
                { duration: '5s', target: 3000 },
                { duration: '5s', target: 1000 },
                { duration: '2s', target: 500 },
                { duration: '2s', target: 200 },
                { duration: '2s', target: 0 },
            ],
            gracefulRampDown: '30s',
        },
    },
    // 極限壓測勿用輕載 SLO；http_req_duration 閾值單位為毫秒（30000 = 30s）
    thresholds: {
        checks: ['rate>0.95'],
        http_req_duration: ['p(95)<30000'],
    },
};

export default function () {
    runBuyFlowBackend();
}
