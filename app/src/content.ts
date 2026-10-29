import { parse as parseYaml } from "yaml";

/* Nội dung đọc thẳng từ thư mục tracks/ ở gốc repo. Quy ước: CONTENT_SPEC.md. */

export const LEVELS = ["basic", "intermediate", "advanced"] as const;
export type Level = (typeof LEVELS)[number];
export const LEVEL_LABEL: Record<Level, string> = { basic: "Basic", intermediate: "Intermediate", advanced: "Advanced" };

export type Section = { slug: string; title: string; body: string };
export type Exercise = {
  key: string; // <module>/<level>/<slug>
  slug: string;
  level: Level;
  title: string;
  services: string[];
  files: { path: string; note?: string }[];
  /** true khi frontmatter có mảng `files` (kể cả rỗng); false nếu thiếu khoá hoặc parse lỗi. */
  filesDeclared: boolean;
  run: string[];
  dir: string; // đường dẫn từ gốc repo
  goal: string;
  task: string;
  criteria: string[];
  hints: { title: string; body: string }[];
};
export type Module = {
  id: string;
  number: string;
  title: string;
  summary: string;
  topics: string[];
  dir: string;
  intro: string;
  sections: Section[];
  exercises: Exercise[];
  hasContent: boolean;
};
export type Milestone = { id: string; title: string; after: string; doc: string };
export type Track = {
  id: string;
  name: string;
  icon: string;
  status: "active" | "soon";
  order: number;
  description: string;
  modules: Module[];
  capstone?: { title: string; readme: string; milestones: Milestone[] };
};

type TrackJson = {
  id: string;
  name: string;
  icon: string;
  status?: "active" | "soon";
  order?: number;
  description?: string;
  modules?: { id: string; title: string; summary?: string; topics?: string[] }[];
  capstone?: { title: string; readme: string; milestones: Milestone[] };
};

const trackFiles = import.meta.glob<TrackJson>("../../tracks/*/track.json", { eager: true, import: "default" });
const moduleReadmes = import.meta.glob<string>("../../tracks/*/modules/*/README.md", { eager: true, query: "?raw", import: "default" });
const exerciseReadmes = import.meta.glob<string>("../../tracks/*/modules/*/exercises/*/*/README.md", { eager: true, query: "?raw", import: "default" });
const lazyMarkdown = import.meta.glob<string>("../../tracks/**/*.md", { query: "?raw", import: "default" });

const PREFIX = "../../";
const repoPath = (globKey: string) => globKey.slice(PREFIX.length);

export function slugify(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

/** Tách markdown theo heading `## `. Phần trước heading đầu là intro (bỏ dòng `# `). */
export function splitSections(markdown: string): { intro: string; sections: Section[] } {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const sections: Section[] = [];
  const introLines: string[] = [];
  let current: Section | null = null;
  let inFence = false;
  for (const line of lines) {
    if (/^(```|~~~)/.test(line.trim())) inFence = !inFence;
    const heading = !inFence && /^## (?!#)(.+)$/.exec(line);
    if (heading) {
      const title = heading[1].trim();
      current = { slug: slugify(title), title, body: "" };
      sections.push(current);
      continue;
    }
    if (current) current.body += line + "\n";
    else if (!/^# (?!#)/.test(line)) introLines.push(line);
  }
  for (const section of sections) section.body = section.body.trim();
  return { intro: introLines.join("\n").trim(), sections };
}

function parseFrontmatter(markdown: string): { data: Record<string, unknown>; body: string } {
  const match = /^---\n([\s\S]*?)\n---\n?/.exec(markdown.replace(/\r\n/g, "\n"));
  if (!match) return { data: {}, body: markdown };
  let data: Record<string, unknown> = {};
  try {
    data = (parseYaml(match[1]) as Record<string, unknown>) ?? {};
  } catch {
    data = {};
  }
  return { data, body: markdown.slice(match[0].length) };
}

function parseExercise(globKey: string, raw: string, moduleId: string): Exercise {
  const dir = repoPath(globKey).replace(/\/README\.md$/, "");
  const [level, slug] = dir.split("/").slice(-2) as [Level, string];
  const { data, body } = parseFrontmatter(raw);
  const { sections } = splitSections(body);
  const find = (name: string) => sections.find((section) => slugify(section.title) === slugify(name))?.body ?? "";
  const hints = splitSubsections(find("Gợi ý"));
  const criteria = find("Tiêu chí đạt")
    .split("\n")
    .map((line) => line.replace(/^\s*[-*]\s+(\[.\]\s+)?/, "").trim())
    .filter(Boolean);
  const files = Array.isArray(data.files)
    ? (data.files as unknown[]).map((file) => (typeof file === "string" ? { path: file } : (file as { path: string; note?: string })))
    : [];
  return {
    key: `${moduleId}/${level}/${slug}`,
    slug,
    level: LEVELS.includes(level) ? level : ((data.level as Level) ?? "basic"),
    title: String(data.title ?? slug),
    services: Array.isArray(data.services) ? (data.services as string[]) : [],
    files,
    filesDeclared: Array.isArray(data.files),
    run: Array.isArray(data.run) ? (data.run as string[]) : [],
    dir,
    goal: find("Mục tiêu"),
    task: find("Đề bài"),
    criteria,
    hints,
  };
}

function splitSubsections(markdown: string): { title: string; body: string }[] {
  const parts: { title: string; body: string }[] = [];
  for (const line of markdown.split("\n")) {
    const heading = /^### (.+)$/.exec(line);
    if (heading) parts.push({ title: heading[1].trim(), body: "" });
    else if (parts.length) parts[parts.length - 1].body += line + "\n";
  }
  return parts.map((part) => ({ ...part, body: part.body.trim() }));
}

function buildTracks(): Track[] {
  const tracks: Track[] = [];
  for (const [key, json] of Object.entries(trackFiles)) {
    const trackDir = repoPath(key).replace(/\/track\.json$/, "");
    const modules: Module[] = (json.modules ?? []).map((meta) => {
      const dir = `${trackDir}/modules/${meta.id}`;
      const readme = moduleReadmes[`${PREFIX}${dir}/README.md`];
      const { intro, sections } = readme ? splitSections(readme) : { intro: "", sections: [] };
      const exercises = Object.entries(exerciseReadmes)
        .filter(([path]) => path.startsWith(`${PREFIX}${dir}/exercises/`))
        .map(([path, raw]) => parseExercise(path, raw, meta.id))
        .sort((a, b) => LEVELS.indexOf(a.level) - LEVELS.indexOf(b.level) || a.slug.localeCompare(b.slug));
      return {
        id: meta.id,
        number: /^(\d+)/.exec(meta.id)?.[1] ?? "",
        title: meta.title,
        summary: meta.summary ?? "",
        topics: meta.topics ?? [],
        dir,
        intro,
        sections,
        exercises,
        hasContent: Boolean(readme) || exercises.length > 0,
      };
    });
    tracks.push({
      id: json.id,
      name: json.name,
      icon: json.icon,
      status: json.status ?? "active",
      order: json.order ?? 99,
      description: json.description ?? "",
      modules,
      capstone: json.capstone
        ? { ...json.capstone, readme: `${trackDir}/${json.capstone.readme}`, milestones: json.capstone.milestones.map((m) => ({ ...m, doc: `${trackDir}/${m.doc}` })) }
        : undefined,
    });
  }
  return tracks.sort((a, b) => a.order - b.order || a.name.localeCompare(b.name));
}

export const TRACKS = buildTracks();

export function findTrack(id: string | undefined) {
  return TRACKS.find((track) => track.id === id);
}

/** Đọc một tệp markdown bất kỳ trong tracks/ (đường dẫn từ gốc repo). null nếu không có. */
export async function loadMarkdown(path: string): Promise<string | null> {
  const loader = lazyMarkdown[`${PREFIX}${path}`];
  return loader ? loader() : null;
}

export function solutionDir(exercise: Exercise) {
  return exercise.dir.replace("/exercises/", "/solutions/");
}
