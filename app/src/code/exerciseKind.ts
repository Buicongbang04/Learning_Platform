/* Phân loại bài tập theo `files` trong frontmatter README (thuần logic, không phụ thuộc React để test được). */
import type { Exercise } from "../content";

export type ExerciseKind = "notebook" | "quiz-only" | "code";

/** Notebook của bài (starter/*.ipynb); null nếu không có. */
export function notebookOf(exercise: Pick<Exercise, "files">): string | null {
  return exercise.files.find((file) => file.path.startsWith("starter/") && file.path.endsWith(".ipynb"))?.path ?? null;
}

export function exerciseKind(exercise: Pick<Exercise, "files">): ExerciseKind {
  if (notebookOf(exercise) !== null) return "notebook";
  if (!exercise.files.some((file) => file.path.startsWith("starter/") || file.path.startsWith("tests/"))) return "quiz-only";
  return "code";
}

export function isNotebookExercise(exercise: Pick<Exercise, "files">): boolean {
  return exerciseKind(exercise) === "notebook";
}
