import test from "node:test";
import assert from "node:assert/strict";
import { starterFilesOf, writtenReportOf } from "./starterFiles.ts";

const de = {
  files: [
    { path: "starter/web_logs.ipynb", note: "5 hàm TODO + 2 biểu đồ" },
    { path: "tests/test_web_logs.py", note: "Không sửa" },
  ],
};
const dsReport = {
  files: [
    { path: "starter/readout.ipynb", note: "4 hàm TODO + phân tích tự do" },
    { path: "starter/launch_data.py", note: "Sinh dữ liệu, không sửa" },
    { path: "starter/REPORT.md", note: "Khuyến nghị cho PM" },
    { path: "tests/test_readout.py", note: "Không sửa" },
  ],
};
const dsMemo = {
  files: [
    { path: "starter/MEMO.md", note: "Memo một trang theo SCQA" },
    { path: "starter/eda.ipynb", note: "3 hàm TODO + phân tích tự do" },
    { path: "tests/test_eda.py", note: "Không sửa" },
  ],
};

test("bài DE notebook: chỉ có .ipynb", () => {
  assert.deepEqual(starterFilesOf(de).map((file) => file.path), ["starter/web_logs.ipynb"]);
  assert.equal(writtenReportOf(de), null);
});

test("bài DS có REPORT.md: notebook trước, bỏ tệp không sửa và test", () => {
  assert.deepEqual(starterFilesOf(dsReport), [
    { path: "starter/readout.ipynb", note: "4 hàm TODO + phân tích tự do" },
    { path: "starter/REPORT.md", note: "Khuyến nghị cho PM" },
  ]);
  assert.equal(writtenReportOf(dsReport), "REPORT.md");
});

test("bài DS module 09 có MEMO.md: notebook vẫn đứng đầu", () => {
  assert.deepEqual(starterFilesOf(dsMemo).map((file) => file.path), ["starter/eda.ipynb", "starter/MEMO.md"]);
  assert.equal(writtenReportOf(dsMemo), "MEMO.md");
});
