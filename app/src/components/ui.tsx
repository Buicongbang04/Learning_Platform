import { icons, type LucideProps } from "lucide-react";
import { useState, type ReactNode } from "react";
import { Check, Copy, RotateCw } from "lucide-react";

export const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

/* Bốn dạng nút (button.md). Hover và focus bàn phím cùng một nền. */
export const button = {
  primary:
    "inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-primary-foreground outline-hidden transition-colors hover:bg-primary-hover focus-visible:bg-primary-hover",
  outline:
    "inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-xl border border-border-strong bg-surface px-4 py-2 text-sm font-medium text-foreground outline-hidden transition-colors hover:bg-button-hover focus-visible:bg-button-hover",
  ghost:
    "inline-flex min-h-10 cursor-pointer items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-muted outline-hidden transition-colors hover:bg-foreground/5 hover:text-foreground focus-visible:bg-foreground/5 focus-visible:text-foreground",
  icon: "inline-flex size-8 shrink-0 cursor-pointer items-center justify-center rounded-lg text-muted outline-hidden transition-colors hover:bg-foreground/5 hover:text-foreground focus-visible:bg-foreground/5 focus-visible:text-foreground",
};

export const badge = {
  done: "inline-flex h-6 shrink-0 items-center gap-1 rounded-full bg-success-bg px-2 text-xs font-medium text-success",
  now: "inline-flex h-6 shrink-0 items-center gap-1 rounded-full bg-primary-light px-2 text-xs font-medium text-primary",
  neutral: "inline-flex h-6 shrink-0 items-center rounded-full bg-neutral-bg px-2 text-xs font-medium text-neutral",
};

export const card = "rounded-2xl border border-border bg-surface";

/** Icon lucide theo tên kebab-case trong track.json. */
export function Icon({ name, ...props }: { name: string } & LucideProps) {
  const pascal = name.replace(/(^|-)([a-z0-9])/g, (_, __, char: string) => char.toUpperCase()) as keyof typeof icons;
  const Component = icons[pascal] ?? icons.BookOpen;
  return <Component aria-hidden {...props} />;
}

export function ProgressBar({ percent, label, className }: { percent: number; label: string; className?: string }) {
  return (
    <div className={cx("h-2 rounded-full bg-foreground/5", className)} role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className={cx("h-2 rounded-full", percent >= 100 ? "bg-success-fill" : "bg-primary")} style={{ width: `${Math.min(percent, 100)}%` }} />
    </div>
  );
}

export function Checkbox({ checked, onChange, label }: { checked: boolean; onChange: (checked: boolean) => void; label?: string }) {
  return (
    <span className="relative inline-flex shrink-0">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        aria-label={label}
        className="peer size-5 cursor-pointer appearance-none rounded-md border-[1.5px] border-border-strong bg-surface outline-hidden transition-colors not-checked:hover:border-foreground checked:border-primary checked:bg-primary focus-visible:border-foreground"
      />
      <Check className="pointer-events-none absolute inset-0 m-auto size-3.5 stroke-[3] text-primary-foreground opacity-0 peer-checked:opacity-100" aria-hidden />
    </span>
  );
}

export function LoadingBlock({ text }: { text: string }) {
  return <p className="py-6 text-center text-sm text-muted">{text}</p>;
}

export function ErrorBlock({ title, reason, onRetry }: { title: string; reason?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 py-10 text-center">
      <div>
        <p className="text-sm font-medium text-error-text">{title}</p>
        {reason && <p className="mt-1 text-sm text-muted">{reason}</p>}
      </div>
      {onRetry && (
        <button type="button" className={button.outline} onClick={onRetry}>
          <RotateCw className="size-4 shrink-0" aria-hidden />
          Thử lại
        </button>
      )}
    </div>
  );
}

export function useCopy() {
  const [copied, setCopied] = useState<string | null>(null);
  const copy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* trình duyệt chặn clipboard: bỏ qua */
    }
    setCopied(text);
    window.setTimeout(() => setCopied((value) => (value === text ? null : value)), 1500);
  };
  return { copied, copy };
}

export function CodeLine({ text, label = "Chép lệnh" }: { text: string; label?: string }) {
  const { copied, copy } = useCopy();
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-xl bg-code py-1.5 pr-1.5 pl-4">
      <code className="scrollbar-clean min-w-0 flex-1 overflow-x-auto font-mono text-[13px] whitespace-nowrap">{text}</code>
      <button type="button" className={button.icon} aria-label={label} onClick={() => copy(text)}>
        {copied === text ? <Check className="size-4 text-success" aria-hidden /> : <Copy className="size-4" aria-hidden />}
      </button>
    </div>
  );
}

export function PageHeader({ title, description, actions, kicker }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; kicker?: ReactNode }) {
  return (
    <header className="mb-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0 flex-1">
        {kicker}
        <h1 className={cx("text-xl font-semibold text-balance", kicker ? "mt-2" : "")}>{title}</h1>
        {description && <p className="mt-1 max-w-[55ch] text-sm text-pretty text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
