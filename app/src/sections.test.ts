import test from "node:test";
import assert from "node:assert/strict";
import { cloudLabModules, mainModules, moduleNumber, moduleSection } from "./sections.ts";

const mods = [{ id: "00-a", section: "main" as const }, { id: "01-b", section: "main" as const }, { id: "c1-aws-byoc", section: "cloud-lab" as const }];

test("module không ghi section là main", () => assert.equal(moduleSection({}), "main"));
test("module ghi cloud-lab", () => assert.equal(moduleSection({ section: "cloud-lab" }), "cloud-lab"));
test("giá trị section lạ rơi về main", () => assert.equal(moduleSection({ section: "x" as never }), "main"));
test("số module: dãy số đầu, C<n> cho cloud-lab, rỗng nếu không có", () => {
  assert.equal(moduleNumber("03-foo"), "03");
  assert.equal(moduleNumber("c1-aws-byoc"), "C1");
  assert.equal(moduleNumber("misc"), "");
});
test("mainModules bỏ module cloud-lab", () => assert.deepEqual(mainModules({ modules: mods }).map((m) => m.id), ["00-a", "01-b"]));
test("cloudLabModules chỉ lấy cloud-lab", () => assert.deepEqual(cloudLabModules({ modules: mods }).map((m) => m.id), ["c1-aws-byoc"]));
