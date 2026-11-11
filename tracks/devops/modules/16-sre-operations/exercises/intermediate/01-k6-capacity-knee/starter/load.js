import http from "k6/http";
import { check } from "k6";

const TARGET = __ENV.TARGET || "http://127.0.0.1:8000";
const STEPS = (__ENV.STEPS || "10,20,30,40,60,80").split(",").map(Number);
const STEP_SECONDS = Number(__ENV.STEP_SECONDS || 5);

const scenarios = {};
const thresholds = {};
// TODO: mỗi bước một scenario step_<rate> (constant-arrival-rate, chạy nối tiếp) và threshold luôn đúng cho ba submetric của nó

export const options = { scenarios, thresholds, discardResponseBodies: true };

export default function () {
  // TODO: GET ${TARGET}/orders/<số ngẫu nhiên>, check status 200
}
