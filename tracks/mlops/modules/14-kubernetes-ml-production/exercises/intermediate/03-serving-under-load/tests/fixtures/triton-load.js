import http from "k6/http";
import { check } from "k6";

export const options = {
  scenarios: { steady: { executor: "constant-vus", vus: 16, duration: "20s" } },
  thresholds: { http_req_failed: ["rate<0.01"] },
};

const body = JSON.stringify({
  inputs: [{ name: "INPUT", shape: [1, 3], datatype: "FP32", data: [3.2, 8, 1] }],
});
const params = { headers: { "Content-Type": "application/json" } };

export default function () {
  const response = http.post(`${__ENV.TARGET}/v2/models/eta/infer`, body, params);
  check(response, { "status 200": (r) => r.status === 200 });
}
