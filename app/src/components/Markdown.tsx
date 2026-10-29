import { useEffect, useId, useRef, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { cx } from "./ui";
import { CodeBlock } from "../code/CodeBlock";

let mermaidPromise: Promise<typeof import("mermaid").default> | null = null;

function cssVar(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

async function getMermaid() {
  mermaidPromise ??= import("mermaid").then((module) => module.default);
  const mermaid = await mermaidPromise;
  // Đo chữ sau khi font đã tải, nếu không nhãn bị cắt.
  await document.fonts.ready;
  mermaid.initialize({
    startOnLoad: false,
    theme: "base",
    fontFamily: "Inter, system-ui, sans-serif",
    htmlLabels: false,
    flowchart: { useMaxWidth: false, padding: 12, htmlLabels: false },
    sequence: { useMaxWidth: false },
    themeVariables: {
      darkMode: document.documentElement.classList.contains("dark"),
      fontSize: "14px",
      background: cssVar("--surface"),
      primaryColor: cssVar("--surface"),
      primaryTextColor: cssVar("--foreground"),
      primaryBorderColor: cssVar("--border-strong"),
      secondaryColor: cssVar("--background"),
      tertiaryColor: cssVar("--background"),
      lineColor: cssVar("--muted"),
      textColor: cssVar("--foreground"),
      noteBkgColor: cssVar("--background"),
      noteTextColor: cssVar("--foreground"),
      clusterBkg: cssVar("--background"),
      clusterBorder: cssVar("--border-strong"),
      edgeLabelBackground: cssVar("--surface"),
    },
  });
  return mermaid;
}

/** Màu trạng thái cho sơ đồ lộ trình: gắn class done / now / todo vào node. */
export function statusClassDefs() {
  return [
    `classDef done fill:${cssVar("--success-bg")},stroke:${cssVar("--success")},color:${cssVar("--foreground")}`,
    `classDef now fill:${cssVar("--primary")},stroke:${cssVar("--primary")},color:${cssVar("--primary-foreground")}`,
    `classDef todo fill:${cssVar("--surface")},stroke:${cssVar("--border-strong")},color:${cssVar("--foreground")}`,
  ].join("\n");
}

function useThemeVersion() {
  const [version, setVersion] = useState(0);
  useEffect(() => {
    const observer = new MutationObserver(() => setVersion((value) => value + 1));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);
  return version;
}

export function Mermaid({ code }: { code: string }) {
  const id = useId().replace(/[^a-zA-Z0-9]/g, "");
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const themeVersion = useThemeVersion();

  useEffect(() => {
    let cancelled = false;
    getMermaid()
      .then((mermaid) => mermaid.render(`m${id}${themeVersion}`, code))
      .then(({ svg }) => {
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
          setFailed(false);
        }
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [code, id, themeVersion]);

  if (failed) return <pre><code>{code}</code></pre>;
  return <div ref={ref} className="mermaid-box" role="img" aria-label="Sơ đồ" />;
}

type HastNode = { type: string; value?: string; tagName?: string; properties?: Record<string, unknown>; children?: HastNode[] };

const textOf = (node: HastNode): string => node.value ?? (node.children ?? []).map(textOf).join("");

const components: Components = {
  code({ className, children, ...props }) {
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  pre({ children, node }) {
    const child = node?.children[0] as HastNode | undefined;
    if (!child || child.tagName !== "code") return <pre>{children}</pre>;
    const language = /^language-(.+)$/.exec(String((child.properties?.className as string[] | undefined)?.[0] ?? ""))?.[1];
    const code = textOf(child).replace(/\n$/, "");
    if (language === "mermaid") return <Mermaid code={code.trim()} />;
    return <CodeBlock code={code} language={language} />;
  },
  table({ children }) {
    return (
      <div className="table-wrap" tabIndex={0}>
        <table>{children}</table>
      </div>
    );
  },
  a({ href, children }) {
    const external = href?.startsWith("http");
    return (
      <a href={href} {...(external ? { target: "_blank", rel: "noreferrer" } : {})}>
        {children}
      </a>
    );
  },
};

// Công thức viết bằng $$...$$ (trong dòng hoặc khối riêng). Tắt $...$ một dấu để "$0.10" vẫn là tiền.
const REMARK = [remarkGfm, [remarkMath, { singleDollarTextMath: false }]] as NonNullable<Parameters<typeof ReactMarkdown>[0]["remarkPlugins"]>;
const REHYPE = [[rehypeKatex, { throwOnError: false }]] as NonNullable<Parameters<typeof ReactMarkdown>[0]["rehypePlugins"]>;

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cx("prose-md", className)}>
      <ReactMarkdown remarkPlugins={REMARK} rehypePlugins={REHYPE} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
