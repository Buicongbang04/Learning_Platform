import test from "node:test";
import assert from "node:assert/strict";
import { gradeQuiz, quizHash, parseQuiz, type QuizQuestion } from "./quiz.ts";

const questions: QuizQuestion[] = [
  { id: "q1", kind: "data", type: "single", prompt: "?", options: [{ id: "a", text: "A" }, { id: "b", text: "B" }] },
  { id: "q2", kind: "knowledge", type: "multi", prompt: "?", options: [{ id: "a", text: "A" }, { id: "b", text: "B" }, { id: "c", text: "C" }] },
];
const key = { q1: ["a"], q2: ["a", "b"] };

test("đúng khi tập trùng khớp, không phụ thuộc thứ tự", () => {
  const r = gradeQuiz(questions, key, { q1: ["a"], q2: ["b", "a"] });
  assert.equal(r.correct, 2);
  assert.equal(r.total, 2);
  assert.deepEqual(r.results.map((x) => x.correct), [true, true]);
  assert.deepEqual(r.results[1].answer, ["a", "b"]);
});

test("multi thiếu hoặc thừa một lựa chọn là sai", () => {
  assert.equal(gradeQuiz(questions, key, { q1: ["a"], q2: ["a"] }).results[1].correct, false);
  assert.equal(gradeQuiz(questions, key, { q1: ["a"], q2: ["a", "b", "c"] }).results[1].correct, false);
});

test("câu bỏ trống là sai", () => {
  const r = gradeQuiz(questions, key, { q1: [] });
  assert.equal(r.correct, 0);
  assert.deepEqual(r.results.map((x) => x.correct), [false, false]);
});

test("câu không có trong đáp án gây lỗi rõ", () => {
  assert.throws(() => gradeQuiz(questions, { q1: ["a"] }, {}), /q2/);
});

test("hash đổi khi nội dung đổi", () => {
  assert.equal(quizHash("a: 1"), quizHash("a: 1"));
  assert.notEqual(quizHash("a: 1"), quizHash("a: 2"));
});

test("parseQuiz đọc yaml và không chứa đáp án", () => {
  const q = parseQuiz("questions:\n  - {id: q1, kind: data, type: single, prompt: p, options: [{id: a, text: A}, {id: b, text: B}]}\n");
  assert.equal(q.length, 1);
  assert.equal(q[0].options[1].id, "b");
  assert.throws(() => parseQuiz("questions: 3"), /questions/);
});
