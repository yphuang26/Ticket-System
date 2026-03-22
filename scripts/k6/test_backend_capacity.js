import { runBuyFlowBackend } from './buy_flow.js';

// 後端極限（不經 Nginx）；預設 BASE_URL=http://web:8000
export const options = {
    scenarios: {
        ramp: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 50 },
                { duration: '1m', target: 50 },
                { duration: '30s', target: 0 },
            ],
            gracefulRampDown: '30s',
        },
    },
    thresholds: {
        checks: ['rate>0.95'],
        http_req_duration: ['p(95)<500'],
    },
};

export default function () {
    runBuyFlowBackend();
}
