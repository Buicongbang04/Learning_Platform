import { Link } from "react-router-dom";
import { Shell } from "../components/Shell";
import { button } from "../components/ui";

export function NotFound() {
  return (
    <Shell header={<p className="min-w-0 truncate text-base font-semibold">Không tìm thấy</p>}>
      <div className="flex flex-col items-center gap-3 py-20 text-center">
        <h1 className="text-xl font-semibold">Không có trang này</h1>
        <p className="max-w-[45ch] text-sm text-muted">Đường dẫn sai, hoặc nội dung đã được đổi tên trong thư mục tracks/.</p>
        <Link to="/" className={button.outline}>
          Về tổng quan
        </Link>
      </div>
    </Shell>
  );
}
