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

/** Tệp văn phòng/ảnh: không soạn trong app, mở bằng ứng dụng ngoài (khớp `isBinaryDoc` ở server/workspace.ts). */
export const isBinaryPath = (path: string) => /\.(xlsx|xlsm|xls|ods|docx|pdf|png|jpe?g|gif)$/i.test(path);

/**
 * Thẻ trắc nghiệm dưới Workspace của bài code: "main" khi bài chỉ có tệp nhị phân (vd. .xlsx) trong starter/ và không có
 * tệp text nào để làm hay test để chạy (trắc nghiệm là phần chấm chính); còn lại "optional". Có hiện thẻ hay không
 * do `quiz.yaml` quyết định (QuizCard tự ẩn khi server trả 404).
 */
export function quizVariantOf(exercise: Pick<Exercise, "files">): "optional" | "main" {
  const starters = exercise.files.filter((file) => file.path.startsWith("starter/"));
  const hasTests = exercise.files.some((file) => file.path.startsWith("tests/"));
  return !hasTests && starters.length > 0 && starters.every((file) => isBinaryPath(file.path)) ? "main" : "optional";
}
