import { createHmac, randomUUID } from "node:crypto";
import { mkdir, open, readFile, rename, readdir, unlink } from "node:fs/promises";
import { join } from "node:path";

const retention = 24 * 60 * 60 * 1000;
export const operationId = () => `${Date.now()}_${randomUUID()}`;
type Phase = "requested" | "dispatched" | "completed" | "rejected" | "unknown";
interface Entry {
    id: string;
    fingerprint: string;
    phase: Phase;
    updatedAt: number;
}
function canonical(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
    if (value && typeof value === "object") {
        return `{${Object.entries(value)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`)
            .join(",")}}`;
    }
    return JSON.stringify(value) ?? "null";
}

// Only keyed request fingerprints and lifecycle metadata touch disk: never URLs,
// selectors, typed secrets, screenshots, response bodies or exception messages.
export function createJournal(directory: string, token: string) {
    function validate(id: string) {
        if (!/^\d{13}_[a-f0-9-]{36}$/.test(id)) throw new Error("Invalid operation ID");
        const age = Date.now() - Number(id.split("_")[0]);
        if (age < -60_000 || age > retention)
            throw new Error("Operation ID expired or from the future; do not replay it.");
    }
    async function status(id: string): Promise<Entry | undefined> {
        validate(id);
        try {
            const entry = JSON.parse(await readFile(join(directory, `${id}.json`), "utf8")) as Entry;
            if (
                entry.id !== id ||
                typeof entry.fingerprint !== "string" ||
                !["requested", "dispatched", "completed", "rejected", "unknown"].includes(entry.phase)
            )
                throw new Error("Invalid action journal; refusing replay");
            return entry;
        } catch (error) {
            if ((error as NodeJS.ErrnoException).code === "ENOENT") return undefined;
            throw error;
        }
    }
    return {
        status,
        async claim(id: string, request: unknown): Promise<boolean> {
            validate(id);
            await mkdir(directory, { recursive: true, mode: 0o700 });
            const fingerprint = createHmac("sha256", token).update(canonical(request)).digest("hex");
            let file;
            try {
                file = await open(join(directory, `${id}.json`), "wx", 0o600);
            } catch (error) {
                if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
                const existing = await status(id);
                if (existing?.fingerprint !== fingerprint)
                    throw new Error("Operation ID already belongs to a different request");
                return false;
            }
            try {
                await file.writeFile(JSON.stringify({ id, fingerprint, phase: "requested", updatedAt: Date.now() }));
                await file.sync();
            } finally {
                await file.close();
            }
            return true;
        },
        async phase(id: string, phase: Phase) {
            const entry = await status(id);
            if (!entry) throw new Error("Missing action journal; refusing dispatch");
            const temporary = join(directory, `${id}.${randomUUID()}.tmp`);
            const file = await open(temporary, "wx", 0o600);
            try {
                await file.writeFile(JSON.stringify({ ...entry, phase, updatedAt: Date.now() }));
                await file.sync();
            } finally {
                await file.close();
            }
            await rename(temporary, join(directory, `${id}.json`));
        },
        async cleanup() {
            await mkdir(directory, { recursive: true, mode: 0o700 });
            for (const name of await readdir(directory)) {
                if (
                    /^\d{13}_[a-f0-9-]{36}(\.json|\.[a-f0-9-]{36}\.tmp)$/.test(name) &&
                    Date.now() - Number(name.split("_")[0]) > retention
                ) {
                    await unlink(join(directory, name)).catch((error) => {
                        if (error.code !== "ENOENT") throw error;
                    });
                }
            }
        },
    };
}
