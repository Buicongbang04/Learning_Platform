import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: {
    steady: { executor: "constant-vus", vus: 8, duration: "15s" },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
  },
};

const body = JSON.stringify({ instances: [[3.2, 8, 1], [12.5, 14, 2]] });
const params = { headers: { "Content-Type": "application/json" } };

export default function () {
  const response = http.post(`${__ENV.TARGET}/v1/models/eta:predict`, body, params);
  check(response, {
    "status 200": (r) => r.status === 200,
    "2 dự đoán": (r) => r.status === 200 && r.json("predictions").length === 2,
  });
}
