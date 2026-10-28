import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { button, cx, useCopy } from "../components/ui";
import { LANGUAGE_LABELS, normalizeLanguage } from "./languageInfo";
import type { Token } from "./languages";

let highlighter: Promise<typeof import("./languages")> | null = null;
const loadHighlighter = () => (highlighter ??= import("./languages"));

const plainLines = (code: string): Token[][] => code.split("\n").map((text) => [{ text, classes: "" }]);

export function CodeBlock({ code, language }: { code: string; language?: string }) {
  const canonical = normalizeLanguage(language);
  const [lines, setLines] = useState(() => plainLines(code));
  const { copied, copy } = useCopy();
  const label = canonical ? LANGUAGE_LABELS[canonical] : language && language !== "text" ? language : "";
  const numbered = Boolean(canonical) && lines.length > 1;

  useEffect(() => {
    setLines(plainLines(code));
    if (!canonical) return;
    let cancelled = false;
    void loadHighlighter().then(({ highlightLines }) => !cancelled && setLines(highlightLines(code, canonical)));
    return () => {
      cancelled = true;
    };
  }, [code, canonical]);

  return (
    <figure className="code-frame">
      <figcaption className="flex h-10 items-center gap-2 border-b border-border-strong pr-1.5 pl-4">
        <span className="min-w-0 flex-1 truncate text-xs font-medium text-muted">{label}</span>
        <button type="button" className={button.icon} aria-label="Chép code" onClick={() => copy(code)}>
          {copied === code ? <Check className="size-4 text-success" aria-hidden /> : <Copy className="size-4" aria-hidden />}
        </button>
      </figcaption>
      <pre tabIndex={0} className={cx(numbered && "numbered")}>
        <code>
          {lines.map((tokens, index) => (
            <span key={index} className="code-line">
              {tokens.map((token, position) =>
                token.classes ? (
                  <span key={position} className={token.classes}>
                    {token.text}
                  </span>
                ) : (
                  token.text
                ),
              )}
              {"\n"}
            </span>
          ))}
        </code>
      </pre>
    </figure>
  );
}
