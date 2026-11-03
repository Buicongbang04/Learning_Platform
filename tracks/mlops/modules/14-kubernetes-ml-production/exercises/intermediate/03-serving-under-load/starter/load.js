import http from "k6/http";
import { check } from "k6";

export const options = {
  // TODO: kịch bản 8 VU chạy đều 15 giây, ngưỡng lỗi và ngưỡng check
};

export default function () {
  // TODO: POST ${__ENV.TARGET}/v1/models/eta:predict với 2 dòng instances, check mã 200 và số dự đoán
}
