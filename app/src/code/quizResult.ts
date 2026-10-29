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
