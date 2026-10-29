import test from "node:test";
import assert from "node:assert/strict";
import { scoreOf, storedResultFor, type QuizResult } from "./quizResult.ts";

const stored: QuizResult = { answers: { q1: ["a"] }, correct: 1, total: 2, submittedAt: "2026-01-01T00:00:00Z", quizHash: "abc" };

test("giữ kết quả khi hash khớp", () => assert.equal(storedResultFor(stored, "abc"), stored));
test("ẩn kết quả khi hash khác", () => assert.equal(storedResultFor(stored, "xyz"), null));
test("chưa có kết quả lưu", () => assert.equal(storedResultFor(undefined, "abc"), null));
test("điểm tính từ kết quả chấm, không từ số đã lưu", () =>
  assert.deepEqual(scoreOf([{ correct: true }, { correct: false }, { correct: true }]), { correct: 2, total: 3 }));
