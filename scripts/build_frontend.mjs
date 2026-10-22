import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import path from "node:path";
import { projectRoot, sourceIdentity } from "./build_identity.mjs";
import { collectNotices } from "./collect_notices.mjs";

const before = sourceIdentity();
const build = spawnSync(process.execPath, [path.join(projectRoot, "node_modules/vinext/dist/cli.js"), "build"], {
  cwd: projectRoot, stdio: "inherit",
});
if (build.status !== 0) process.exit(build.status ?? 1);
collectNotices(projectRoot, path.join(projectRoot, "dist/standalone/third-party-licenses"));
const after = sourceIdentity();
if (JSON.stringify(before) !== JSON.stringify(after)) throw new Error("构建期间源码发生变化，请重新构建。");
writeFileSync(path.join(projectRoot, "dist/standalone/BUILD_SOURCE.json"), JSON.stringify(after));
