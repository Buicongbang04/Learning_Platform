import http from "k6/http";

const TARGET = __ENV.TARGET || "http://127.0.0.1:8000";

export const options = {
  vus: 20,
  duration: "6s",
  thresholds: {
    http_req_duration: ["p(95)<300"],
  },
};

export default function () {
  http.get(`${TARGET}/orders/${Math.floor(Math.random() * 100000)}`);
}
