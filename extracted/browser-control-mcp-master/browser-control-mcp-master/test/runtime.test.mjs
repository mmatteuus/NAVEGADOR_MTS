import test from "node:test";
import assert from "node:assert/strict";
import { createRuntime } from "../dist/runtime.js";

test(
    "JavaScript runtime preserves declarations and awaits, isolates clients and resets runaway code",
    { timeout: 15000 },
    async (t) => {
        const runtime = createRuntime();
        const other = createRuntime();
        t.after(() => {
            runtime.reset();
            other.reset();
        });
        let result = await runtime.run("let counter = await Promise.resolve(4); nodeRepl.write(counter);", 5000);
        assert.equal(result.content[0].text, "4");
        result = await runtime.run("counter++; nodeRepl.write(counter);", 5000);
        assert.equal(result.content[0].text, "5");
        result = await other.run("nodeRepl.write(typeof counter);", 5000);
        assert.equal(result.content[0].text, "undefined");
        result = await runtime.run("throw new Error('expected failure');", 5000);
        assert.equal(result.isError, true);
        for (const code of ["throw null;", "await Promise.reject(new Error('rejected'));", "let = ;"]) {
            result = await runtime.run(code, 5000);
            assert.equal(result.isError, true, code);
        }
        result = await runtime.run("nodeRepl.write(counter);", 5000);
        assert.equal(result.content[0].text, "5", "Ordinary errors preserve variables");
        await assert.rejects(runtime.run("while (true) {}", 500), /timed out/);
        result = await runtime.run("nodeRepl.write(typeof counter);", 5000);
        assert.equal(result.content[0].text, "undefined", "Timeout resets the worker");
        await runtime.run("let pending = 1;", 5000);
        runtime.reset();
        result = await runtime.run("nodeRepl.write(typeof pending);", 5000);
        assert.equal(result.content[0].text, "undefined");
    },
);
