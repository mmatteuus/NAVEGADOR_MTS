import { resolve } from "node:path";
import { getConfig, root } from "../dist/config.js";
import { buildExtensions } from "./extensions.mjs";

await buildExtensions(resolve(root, "build"), await getConfig());
console.log("Built build/chrome and build/firefox. These contain a local pairing secret; do not publish them.");
