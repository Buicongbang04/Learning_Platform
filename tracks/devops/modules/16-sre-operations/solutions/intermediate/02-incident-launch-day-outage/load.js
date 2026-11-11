import http from "k6/http";
import { check } from "k6";

const TARGET = __ENV.TARGET || "http://127.0.0.1:8000";

export const options = {
  scenarios: {
    launch: {
      executor: "constant-arrival-rate",
      rate: 80,
      timeUnit: "1s",
      duration: "6s",
      preAllocatedVUs: 20,
      maxVUs: 200,
    },
  },
  thresholds: {
    "http_req_duration{expected_response:true}": ["p(95)<300"],
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

export default function () {
  const response = http.get(`${TARGET}/orders/${Math.floor(Math.random() * 100000)}`, {
    tags: { name: "GET /orders/{order_id}" },
  });
  check(response, { "status 200": (r) => r.status === 200 });
}
