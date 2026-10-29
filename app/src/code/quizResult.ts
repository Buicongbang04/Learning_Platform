/* Kiểu và logic thuần của kết quả trắc nghiệm (không phụ thuộc React để test được). */

export type QuizResult = {
  answers: Record<string, string[]>;
  correct: number;
  total: number;
  submittedAt: string;
  quizHash: string;
};

/** Kết quả đã lưu chỉ còn giá trị khi bộ câu hỏi chưa đổi (cùng quizHash); ngược lại coi như chưa làm. */
export function storedResultFor(stored: QuizResult | undefined, currentHash: string): QuizResult | null {
  return stored && stored.quizHash === currentHash ? stored : null;
}

/** Điểm hiển thị tính từ kết quả chấm lại hiện tại, để luôn khớp với dấu đúng/sai từng câu (dù đáp án đã sửa sau khi nộp). */
export function scoreOf(results: { correct: boolean }[]): { correct: number; total: number } {
  return { correct: results.filter((item) => item.correct).length, total: results.length };
}
