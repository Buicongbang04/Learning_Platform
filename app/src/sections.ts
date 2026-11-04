/* Phân nhóm module của một track (không phụ thuộc Vite/React để test được). */

export type ModuleSection = "main" | "cloud-lab";

export const moduleSection = (meta: { section?: ModuleSection }): ModuleSection => (meta.section === "cloud-lab" ? "cloud-lab" : "main");

export function moduleNumber(id: string): string {
  const digits = /^(\d+)/.exec(id)?.[1];
  if (digits) return digits;
  const lab = /^c(\d+)/i.exec(id)?.[1];
  return lab ? `C${lab}` : "";
}

type Sectioned = { section: ModuleSection };
export const mainModules = <M extends Sectioned>(track: { modules: M[] }) => track.modules.filter((module) => module.section === "main");
export const cloudLabModules = <M extends Sectioned>(track: { modules: M[] }) => track.modules.filter((module) => module.section === "cloud-lab");
