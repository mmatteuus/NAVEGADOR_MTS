import { mkdtemp, mkdir, readFile, writeFile, readdir } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { root } from "../dist/config.js";
import { buildExtensions } from "./extensions.mjs";

const { version } = JSON.parse(await readFile(resolve(root, "package.json"), "utf8"));
const staging = await mkdtemp(resolve(tmpdir(), "browser-control-release-"));
const output = resolve(root, "releases", `v${version}`);
await mkdir(output, { recursive: true });
await buildExtensions(staging);
const checksums = [];
for (const browser of ["chrome", "firefox"]) {
    const folder = resolve(staging, browser);
    const connection = JSON.parse(await readFile(resolve(folder, "connection.json"), "utf8"));
    if (connection.token !== null) throw new Error("Release extension must not contain a pairing token.");
    const name = `browser-control-${browser}-${version}.zip`;
    const path = resolve(output, name);
    const zip = execFileSync("zip", ["-q", "-X", "-", ...(await readdir(folder)).sort()], { cwd: folder });
    // Refuse replacement so stale files cannot survive an archive update.
    await writeFile(path, zip, { flag: "wx" });
    checksums.push(`${createHash("sha256").update(zip).digest("hex")}  ${name}`);
}
await writeFile(resolve(output, "SHA256SUMS"), checksums.join("\n") + "\n", { flag: "wx" });
console.log(`Created secret-free release archives in ${output}. Firefox archive is unsigned.`);
