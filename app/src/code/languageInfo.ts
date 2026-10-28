export const LANGUAGE_LABELS = {
  python: "Python",
  sql: "SQL",
  yaml: "YAML",
  json: "JSON",
  bash: "Bash",
  dockerfile: "Dockerfile",
  cypher: "Cypher",
  lua: "Lua",
  cql: "CQL",
  hcl: "HCL",
} as const;

export type LanguageName = keyof typeof LANGUAGE_LABELS;

const ALIASES: Record<string, LanguageName> = {
  py: "python",
  sh: "bash",
  shell: "bash",
  zsh: "bash",
  console: "bash",
  yml: "yaml",
  tf: "hcl",
  terraform: "hcl",
  docker: "dockerfile",
};

export function normalizeLanguage(name: string | undefined): LanguageName | undefined {
  if (!name) return undefined;
  const key = name.toLowerCase();
  const canonical = ALIASES[key] ?? key;
  return canonical in LANGUAGE_LABELS ? (canonical as LanguageName) : undefined;
}

export function languageForFile(path: string): LanguageName | undefined {
  const base = path.split("/").pop() ?? "";
  if (/^Dockerfile/i.test(base)) return "dockerfile";
  return normalizeLanguage(/\.([^.]+)$/.exec(base)?.[1]);
}
