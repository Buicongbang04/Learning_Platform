import type { Exercise } from "./content";
import type { NextItem } from "./progress";

export const trackLink = (trackId: string) => `/t/${trackId}`;
export const moduleLink = (trackId: string, moduleId: string, tab?: string, section?: string) => {
  const query = new URLSearchParams();
  if (tab) query.set("tab", tab);
  if (section) query.set("s", section);
  const search = query.toString();
  return `/t/${trackId}/m/${moduleId}${search ? `?${search}` : ""}`;
};
export const exerciseLink = (trackId: string, exercise: Exercise) => `/t/${trackId}/m/${exercise.key.split("/")[0]}/e/${exercise.level}/${exercise.slug}`;
export const milestoneLink = (trackId: string, milestoneId: string) => `/t/${trackId}/capstone/${milestoneId}`;

export function nextItemLink(trackId: string, item: NextItem) {
  if (item.kind === "section") return moduleLink(trackId, item.module.id, undefined, item.slug);
  if (item.kind === "exercise") return exerciseLink(trackId, item.exercise);
  return milestoneLink(trackId, item.id);
}
