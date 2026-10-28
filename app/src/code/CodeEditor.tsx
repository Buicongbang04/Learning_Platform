import { useEffect, useRef } from "react";
import { basicSetup } from "codemirror";
import { EditorState, type Extension } from "@codemirror/state";
import { EditorView, keymap } from "@codemirror/view";
import { indentWithTab } from "@codemirror/commands";
import { indentUnit, syntaxHighlighting } from "@codemirror/language";
import { classHighlighter } from "@lezer/highlight";
import { languageForFile } from "./languageInfo";
import { languageSupport } from "./languages";

const theme = EditorView.theme({
  "&": { height: "100%", fontSize: "13px", backgroundColor: "var(--code-frame)", color: "var(--foreground)" },
  "&.cm-focused": { outline: "none" },
  ".cm-scroller": { fontFamily: "var(--mono-font)", lineHeight: "1.6" },
  ".cm-content": { caretColor: "var(--primary)", padding: "10px 0" },
  ".cm-cursor, .cm-dropCursor": { borderLeftColor: "var(--primary)", borderLeftWidth: "2px" },
  ".cm-gutters": { backgroundColor: "var(--code-frame)", color: "var(--code-gutter)", border: "none" },
  ".cm-lineNumbers .cm-gutterElement": { padding: "0 12px 0 16px", minWidth: "3rem" },
  ".cm-activeLine": { backgroundColor: "color-mix(in srgb, var(--foreground) 4%, transparent)" },
  ".cm-activeLineGutter": { backgroundColor: "transparent", color: "var(--foreground)" },
  "&.cm-focused > .cm-scroller > .cm-selectionLayer .cm-selectionBackground, .cm-selectionBackground, ::selection": {
    backgroundColor: "color-mix(in srgb, var(--primary) 22%, transparent) !important",
  },
  ".cm-matchingBracket": { backgroundColor: "color-mix(in srgb, var(--primary) 18%, transparent)", outline: "none" },
  ".cm-foldPlaceholder": { backgroundColor: "var(--secondary)", border: "none", color: "var(--muted)" },
  ".cm-tooltip": { backgroundColor: "var(--surface-overlay)", border: "1px solid var(--border-strong)", borderRadius: "8px" },
  ".cm-tooltip-autocomplete > ul > li[aria-selected]": { backgroundColor: "var(--primary)", color: "var(--primary-foreground)" },
  ".cm-panels": { backgroundColor: "var(--surface)", color: "var(--foreground)" },
  ".cm-searchMatch": { backgroundColor: "color-mix(in srgb, #facc15 35%, transparent)" },
});

type Props = {
  path: string;
  content: string;
  revision: number;
  readOnly: boolean;
  onChange: (path: string, content: string) => void;
  onSave: () => void;
  onRun: () => void;
};

export function CodeEditor({ path, content, revision, readOnly, onChange, onSave, onRun }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const states = useRef(new Map<string, { state: EditorState; revision: number }>());
  const activePath = useRef<string | null>(null);
  const handlers = useRef({ onChange, onSave, onRun });
  handlers.current = { onChange, onSave, onRun };

  const extensions = (file: string, locked: boolean): Extension[] => {
    const language = languageSupport(languageForFile(file));
    return [
      basicSetup,
      keymap.of([
        indentWithTab,
        { key: "Mod-s", preventDefault: true, run: () => (handlers.current.onSave(), true) },
        { key: "Mod-Enter", preventDefault: true, run: () => (handlers.current.onRun(), true) },
      ]),
      indentUnit.of("    "),
      EditorState.tabSize.of(4),
      syntaxHighlighting(classHighlighter),
      theme,
      EditorState.readOnly.of(locked),
      EditorView.editable.of(!locked),
      EditorView.contentAttributes.of({ "aria-label": `Nội dung tệp ${file}` }),
      EditorView.updateListener.of((update) => {
        if (!update.docChanged) return;
        handlers.current.onChange(file, update.state.doc.toString());
      }),
      ...(language ? [language] : []),
    ];
  };

  useEffect(() => {
    if (!host.current) return;
    view.current = new EditorView({ parent: host.current });
    return () => {
      const entry = activePath.current && states.current.get(activePath.current);
      if (entry && view.current) entry.state = view.current.state;
      activePath.current = null;
      view.current?.destroy();
      view.current = null;
    };
  }, []);

  useEffect(() => {
    if (!view.current) return;
    const previous = activePath.current && states.current.get(activePath.current);
    if (previous) previous.state = view.current.state;
    activePath.current = path;
    let entry = states.current.get(path);
    if (!entry || entry.revision !== revision) {
      entry = { state: EditorState.create({ doc: content, extensions: extensions(path, readOnly) }), revision };
      states.current.set(path, entry);
    }
    view.current.setState(entry.state);
  }, [path, revision, readOnly]);

  return <div ref={host} className="h-full min-h-0 overflow-hidden" />;
}
