import http from "k6/http";
import { check } from "k6";

const TARGET = __ENV.TARGET || "http://127.0.0.1:28080";
const ZONES = [48, 79, 132, 138, 161, 162, 230, 236, 237];

export const options = {
  scenarios: {
    warmup: { executor: "constant-vus", vus: 1, duration: "3s", tags: { phase: "warmup" } },
    steady: { executor: "constant-arrival-rate", rate: 40, timeUnit: "1s", duration: "15s",
              preAllocatedVUs: 10, maxVUs: 20, startTime: "3s", tags: { phase: "steady" } },
  },
  thresholds: {
    http_req_duration: ["p(95)<200"],
    http_req_failed: ["rate<0.01"],
    "http_req_duration{phase:steady}": ["p(99)<500"],
    checks: ["rate>0.99"],
  },
};

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

export default function () {
  const hour = String(Math.floor(Math.random() * 24)).padStart(2, "0");
  const body = JSON.stringify({
    PULocationID: pick(ZONES),
    DOLocationID: pick(ZONES),
    pickup_datetime: `2019-03-12T${hour}:15:00`,
    trip_distance: Math.round((0.5 + Math.random() * 8) * 10) / 10,
  });
  const id = `k6-${__VU}-${__ITER}`;
  const res = http.post(`${TARGET}/predict`, body, {
    headers: { "Content-Type": "application/json", "X-Request-ID": id },
  });
  check(res, {
    "status 200": (r) => r.status === 200,
    "eta_s > 0": (r) => r.status === 200 && r.json("eta_s") > 0,
    "echo X-Request-ID": (r) => r.headers["X-Request-Id"] === id,
  });
}
