import http from "k6/http";
import { check } from "k6";

const P95_MS = Number(__ENV.P95_MS || 300);
const BODY = JSON.stringify({ rows: [[5, 8, 1], [12, 17, 2]] });
const HEADERS = { headers: { "Content-Type": "application/json" } };

export const options = {
  scenarios: {
    warmup: {
      executor: "constant-arrival-rate",
      rate: 10,
      timeUnit: "1s",
      duration: "3s",
      preAllocatedVUs: 20,
      maxVUs: 100,
      exec: "predict",
    },
    measure: {
      executor: "constant-arrival-rate",
      rate: 30,
      timeUnit: "1s",
      duration: "8s",
      startTime: "4s",
      preAllocatedVUs: 20,
      maxVUs: 100,
      exec: "predict",
    },
  },
  thresholds: {
    "http_req_duration{scenario:measure}": [`p(95)<${P95_MS}`],
    "http_req_failed{scenario:measure}": ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

export function predict() {
  const response = http.post(`${__ENV.TARGET}/predict`, BODY, HEADERS);
  check(response, {
    "status 200": (r) => r.status === 200,
    "có model_version": (r) => r.status === 200 && r.json("model_version") !== undefined,
    "2 dự đoán": (r) => r.status === 200 && r.json("predictions").length === 2,
  });
}
