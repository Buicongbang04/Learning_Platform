import { LanguageSupport, StreamLanguage, type StreamParser } from "@codemirror/language";
import { python } from "@codemirror/lang-python";
import { PostgreSQL, sql } from "@codemirror/lang-sql";
import { yaml } from "@codemirror/lang-yaml";
import { json } from "@codemirror/lang-json";
import { shell } from "@codemirror/legacy-modes/mode/shell";
import { dockerFile } from "@codemirror/legacy-modes/mode/dockerfile";
import { cypher } from "@codemirror/legacy-modes/mode/cypher";
import { lua } from "@codemirror/legacy-modes/mode/lua";
import { cassandra } from "@codemirror/legacy-modes/mode/sql";
import { classHighlighter, highlightCode } from "@lezer/highlight";
import type { LanguageName } from "./languageInfo";

const hcl: StreamParser<{ blockComment: boolean }> = {
  name: "hcl",
  startState: () => ({ blockComment: false }),
  token(stream, state) {
    if (state.blockComment) {
      state.blockComment = !stream.match(/^.*?\*\//);
      if (state.blockComment) stream.skipToEnd();
      return "comment";
    }
    if (stream.eatSpace()) return null;
    if (stream.match("/*")) {
      state.blockComment = true;
      return "comment";
    }
    if (stream.match("#") || stream.match("//")) {
      stream.skipToEnd();
      return "comment";
    }
    if (stream.match(/^"(?:[^"\\]|\\.)*"?/) || stream.match(/^<<-?\w+/)) return "string";
    if (stream.match(/^-?\d+(?:\.\d+)?\b/)) return "number";
    if (stream.match(/^(?:true|false|null)\b/)) return "atom";
    if (stream.match(/^(?:for|in|if|else|endfor|endif)\b/)) return "keyword";
    const atLineStart = stream.column() === stream.indentation();
    if (atLineStart && stream.match(/^[A-Za-z_][\w-]*(?=\s*["{])/)) return "keyword";
    if (stream.match(/^[A-Za-z_][\w-]*(?=\s*=(?!=))/)) return "propertyName";
    if (stream.match(/^[A-Za-z_][\w-]*(?=\()/)) return "variableName.special";
    if (stream.match(/^[A-Za-z_][\w-]*/)) return "variableName";
    stream.next();
    return null;
  },
  languageData: { commentTokens: { line: "#", block: { open: "/*", close: "*/" } } },
};

const stream = (parser: StreamParser<unknown>) => new LanguageSupport(StreamLanguage.define(parser));

const LANGUAGES: Record<LanguageName, () => LanguageSupport> = {
  python,
  sql: () => sql({ dialect: PostgreSQL }),
  yaml,
  json,
  bash: () => stream(shell),
  dockerfile: () => stream(dockerFile),
  cypher: () => stream(cypher),
  lua: () => stream(lua),
  cql: () => stream(cassandra),
  hcl: () => stream(hcl as StreamParser<unknown>),
};

const cache = new Map<LanguageName, LanguageSupport>();
export function languageSupport(name: LanguageName | undefined): LanguageSupport | undefined {
  if (!name) return undefined;
  if (!cache.has(name)) cache.set(name, LANGUAGES[name]());
  return cache.get(name);
}

export type Token = { text: string; classes: string };

export function highlightLines(code: string, name: LanguageName): Token[][] {
  const language = languageSupport(name)!.language;
  const lines: Token[][] = [[]];
  highlightCode(
    code,
    language.parser.parse(code),
    classHighlighter,
    (text, classes) => lines[lines.length - 1].push({ text, classes }),
    () => lines.push([]),
  );
  return lines;
}
