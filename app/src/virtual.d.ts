declare module "virtual:track-icons" {
  import type { LucideIcon } from "lucide-react";
  const icons: Record<string, LucideIcon>;
  export const fallback: LucideIcon;
  export default icons;
}
