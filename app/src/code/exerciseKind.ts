/* Phân loại bài tập theo `files` trong frontmatter README (thuần logic, không phụ thuộc React để test được). */
import type { Exercise } from "../content";

export type ExerciseKind = "notebook" | "quiz-only" | "code";

/** Notebook của bài (starter/*.ipynb); null nếu không có. */
export function notebookOf(exercise: Pick<Exercise, "files">): string | null {
  return exercise.files.find((file) => file.path.startsWith("starter/") && file.path.endsWith(".ipynb"))?.path ?? null;
}

type KindInput = Pick<Exercise, "files"> & { filesDeclared?: boolean };

export function exerciseKind(exercise: KindInput): ExerciseKind {
  if (notebookOf(exercise) !== null) return "notebook";
  // Chỉ `files: []` khai báo tường minh mới là quiz-only; thiếu khoá / frontmatter lỗi thì coi như bài code.
  if (exercise.filesDeclared === false) return "code";
  if (!exercise.files.some((file) => file.path.startsWith("starter/") || file.path.startsWith("tests/"))) return "quiz-only";
  return "code";
}

export function isNotebookExercise(exercise: KindInput): boolean {
  return exerciseKind(exercise) === "notebook";
}
