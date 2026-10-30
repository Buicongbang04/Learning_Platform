import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { isBinaryDoc, isText, readExerciseFiles, resolveStarterFile } from "./workspace.ts";

test("isText: .xlsx và tệp văn phòng/ảnh không phải text", () => {
  for (const name of ["sales.xlsx", "a.XLSM", "a.ods", "a.docx", "a.pdf", "a.png", "a.jpeg"]) assert.equal(isText(`starter/${name}`), false, name);
  for (const name of ["a.py", "a.ipynb", "REPORT.md", "data.csv"]) assert.equal(isText(`starter/${name}`), true, name);
  assert.equal(isText("starter/sales.xlsx"), false);
  assert.equal(isBinaryDoc("starter/sales.xlsx"), true);
  assert.equal(isBinaryDoc("starter/a.py"), false);
});

function exercise() {
  const root = mkdtempSync(join(tmpdir(), "ws-"));
  mkdirSync(join(root, "starter"));
  mkdirSync(join(root, "tests"));
  writeFileSync(join(root, "starter", "sales.xlsx"), Buffer.from([0x50, 0x4b, 0x03, 0x04, 0xff, 0x00]));
  writeFileSync(join(root, "starter", "notes.py"), "print(1)\n");
  writeFileSync(join(root, "tests", "test_x.py"), "def test_x(): pass\n");
  return root;
}

test("readExerciseFiles: .xlsx trả { path, binary: true } không có content, tệp text giữ nguyên", () => {
  const files = readExerciseFiles(exercise());
  const xlsx = files.find((f) => f.path === "starter/sales.xlsx");
  assert.deepEqual(xlsx, { path: "starter/sales.xlsx", binary: true });
  assert.ok(!("content" in xlsx!));
  assert.deepEqual(files.find((f) => f.path === "starter/notes.py"), { path: "starter/notes.py", content: "print(1)\n", editable: true });
  assert.deepEqual(files.find((f) => f.path === "tests/test_x.py"), { path: "tests/test_x.py", content: "def test_x(): pass\n", editable: false });
});

test("resolveStarterFile: chỉ nhận tệp trong starter/", () => {
  const root = exercise();
  assert.equal(resolveStarterFile(root, "starter/sales.xlsx"), join(root, "starter", "sales.xlsx"));
  assert.throws(() => resolveStarterFile(root, "tests/test_x.py"));
  assert.throws(() => resolveStarterFile(root, "starter/../tests/test_x.py"));
  assert.throws(() => resolveStarterFile(root, 5));
});
