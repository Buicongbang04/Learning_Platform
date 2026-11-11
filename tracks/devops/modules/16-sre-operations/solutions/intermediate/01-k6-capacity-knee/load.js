import http from "k6/http";
import { check } from "k6";

const TARGET = __ENV.TARGET || "http://127.0.0.1:8000";
const STEPS = (__ENV.STEPS || "10,20,30,40,60,80").split(",").map(Number);
const STEP_SECONDS = Number(__ENV.STEP_SECONDS || 5);

const scenarios = {};
const thresholds = {};
STEPS.forEach((rate, index) => {
  const name = `step_${rate}`;
  scenarios[name] = {
    executor: "constant-arrival-rate",
    rate: rate,
    timeUnit: "1s",
    duration: `${STEP_SECONDS}s`,
    startTime: `${index * STEP_SECONDS}s`,
    preAllocatedVUs: 10,
    maxVUs: 150,
    gracefulStop: "5s",
  };
  thresholds[`http_req_duration{scenario:${name}}`] = ["max>=0"];
  thresholds[`http_req_failed{scenario:${name}}`] = ["rate>=0"];
  thresholds[`http_reqs{scenario:${name}}`] = ["count>=0"];
});

export const options = { scenarios, thresholds, discardResponseBodies: true };

export default function () {
  const id = Math.floor(Math.random() * 100000);
  const response = http.get(`${TARGET}/orders/${id}`, { tags: { name: "GET /orders/{order_id}" } });
  check(response, { "status 200": (r) => r.status === 200 });
}
