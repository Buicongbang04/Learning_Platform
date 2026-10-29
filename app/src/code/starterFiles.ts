/* Logic thuần về tệp starter của bài notebook (không phụ thuộc React để test được). */
import type { Exercise } from "../content";

export type StarterFile = { path: string; note?: string };

const READ_ONLY_NOTE = /không sửa/i;

/**
 * Tệp người học cần mở trong bài notebook: mọi `starter/*` trong `files` của frontmatter, notebook (.ipynb) đứng đầu.
 * Bỏ tệp test và tệp có ghi chú "không sửa" (vd. `starter/launch_data.py` chỉ để notebook import).
 */
export function starterFilesOf(exercise: Pick<Exercise, "files">): StarterFile[] {
  const files = exercise.files.filter((file) => file.path.startsWith("starter/") && !READ_ONLY_NOTE.test(file.note ?? ""));
  return [...files.filter((file) => file.path.endsWith(".ipynb")), ...files.filter((file) => !file.path.endsWith(".ipynb"))];
}

/** Báo cáo viết tay (REPORT.md, MEMO.md...) do test chấm, nếu bài có; dùng để phân biệt với trắc nghiệm. */
export function writtenReportOf(exercise: Pick<Exercise, "files">): string | null {
  const report = starterFilesOf(exercise).find((file) => file.path.toLowerCase().endsWith(".md"));
  return report ? report.path.slice("starter/".length) : null;
}
