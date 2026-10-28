import type { Plugin } from "vite";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const MODULE_ID = "virtual:track-icons";
const RESOLVED_ID = "\0" + MODULE_ID;
const FALLBACK = "book-open";

const pascal = (name: string) => name.replace(/(^|-)([a-z0-9])/g, (_, __, char: string) => char.toUpperCase());

/** Chỉ nhập những icon lucide mà các track.json dùng, thay vì cả bộ ~1.900 icon. */
export function trackIcons(repoRoot: string, appRoot: string): Plugin {
  const tracksDir = resolve(repoRoot, "tracks");
  const iconDir = resolve(appRoot, "node_modules/lucide-react/dist/esm/icons");
  const trackFiles = () =>
    readdirSync(tracksDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => resolve(tracksDir, entry.name, "track.json"))
      .filter(existsSync);

  return {
    name: "track-icons",
    resolveId: (id) => (id === MODULE_ID ? RESOLVED_ID : undefined),
    load(id) {
      if (id !== RESOLVED_ID) return;
      const names = new Set([FALLBACK]);
      for (const file of trackFiles()) {
        this.addWatchFile(file);
        const icon = (JSON.parse(readFileSync(file, "utf-8")) as { icon?: unknown }).icon;
        if (typeof icon !== "string") continue;
        if (existsSync(resolve(iconDir, `${icon}.mjs`))) names.add(icon);
        else this.warn(`${file}: lucide không có icon "${icon}", dùng "${FALLBACK}"`);
      }
      const list = [...names];
      return [
        `import { ${list.map(pascal).join(", ")} } from "lucide-react";`,
        `export const fallback = ${pascal(FALLBACK)};`,
        `export default { ${list.map((name) => `${JSON.stringify(name)}: ${pascal(name)}`).join(", ")} };`,
      ].join("\n");
    },
    configureServer(server) {
      const refresh = (file: string) => {
        if (!/[\\/]tracks[\\/][^\\/]+[\\/]track\.json$/.test(file)) return;
        const module = server.moduleGraph.getModuleById(RESOLVED_ID);
        if (module) server.moduleGraph.invalidateModule(module);
      };
      server.watcher.on("add", refresh);
      server.watcher.on("change", refresh);
    },
  };
}
