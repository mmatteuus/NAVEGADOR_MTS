import assert from "node:assert/strict";

export const extraFixture = `
<section aria-label="Extra controls">
<h2>Input verification</h2>
<span id="account-label" hidden>Account name</span><input id="named" aria-labelledby="account-label" value="alpha beta beta">
<div id="editor" contenteditable="true" aria-label="Rich editor"><b>alpha</b> beta</div>
<details id="details"><summary>More information</summary><p>Expanded information</p></details>
<label>Quantity <input type="number" id="quantity" value="2"></label>
<canvas id="pad" role="img" aria-label="Pointer area" width="300" height="120" style="display:block;border:1px solid black"></canvas>
<output id="pointer-state" style="display:block;height:60px;overflow:hidden">{}</output>
<output id="key-state" style="display:block;height:40px;overflow:hidden">{}</output>
<output id="input-state" style="display:block;height:40px;overflow:hidden">{}</output>
<script>
document.querySelector('#named').addEventListener('input',event=>{document.querySelector('#input-state').textContent=JSON.stringify({inputTrusted:event.isTrusted});});
document.addEventListener('keydown',event=>{document.querySelector('#key-state').textContent=JSON.stringify({key:event.key,ctrl:event.ctrlKey,trusted:event.isTrusted,target:event.target.id});});
const pad=document.querySelector('#pad');
const pointerEvents={};
for(const type of ['click','contextmenu','auxclick','dblclick','pointerdown','pointermove','pointerup']) {
    pad.addEventListener(type,event=>{
        if(type==='contextmenu') event.preventDefault();
        const rect=pad.getBoundingClientRect();
        pointerEvents[type]={x:Math.round(event.clientX-rect.x),y:Math.round(event.clientY-rect.y),button:event.button,buttons:event.buttons,detail:event.detail,trusted:event.isTrusted};
        document.querySelector('#pointer-state').textContent=JSON.stringify(pointerEvents);
    });
}
const rollback = document.createElement('input');
rollback.id = 'rollback';
rollback.addEventListener('input',()=>setTimeout(()=>{rollback.value='rolled-back';},300));
document.body.append(rollback);
const replaced = document.createElement('button');
replaced.id='replace-during-hover';
replaced.textContent='Replace during hover';
replaced.addEventListener('pointerover',()=>setTimeout(()=>replaced.replaceWith(replaced.cloneNode(true)),100),{once:true});
document.body.append(replaced);
</script>
</section>`;

export async function additionalCases(call, args) {
    const capabilities = await call("capabilities", { browser: args.browser });
    assert.equal(capabilities.trustedInput, args.browser === "chrome");
    assert.equal(capabilities.trustedKeyboard, false);
    await assert.rejects(call("click", { ...args, selector: "#replace-during-hover" }), /Target changed|stale/);
    await assert.rejects(
        call("fill", { ...args, selector: "#rollback", text: "temporary", inputMode: "dom" }),
        /mismatch/,
    );
    const state = () => call("snapshot", args);
    let snapshot = await state();
    const named = snapshot.nodes.find((node) => node.name === "Account name");
    assert.equal(named.role, "textbox");
    assert.ok(snapshot.nodes.some((node) => node.role === "heading" && node.level === 2));
    assert.ok(named.parentRef, "Semantic hierarchy includes parent refs");
    await call("select_text", { ...args, ref: named.ref, text: "beta", prefix: "alpha " });
    await call("type", { ...args, text: "B" });
    assert.equal((await state()).elements.find((node) => node.ref === named.ref).value, "alpha B beta");
    await call("press", { ...args, key: "ctrl+a" });
    await call("type", { ...args, text: "abcd" });
    await call("press", { ...args, key: "Left" });
    await call("press", { ...args, key: "shift+Left" });
    await call("type", { ...args, text: "X" });
    assert.equal((await state()).elements.find((node) => node.ref === named.ref).value, "abXd");
    await call("select_text", { ...args, selector: "#editor", text: "beta", selectionType: "cursor_after" });
    await call("paste", { ...args, selector: "#editor", format: "html", text: "<i> formatted</i>" });
    await call("select_text", { ...args, selector: "#editor", text: "alpha beta", selectionType: "text" });
    await call("type", { ...args, text: "Edited" });
    assert.match((await state()).text, /Edited\s+formatted/);
    await call("secondary", { ...args, selector: "#details", action: "Expand" });
    assert.match((await state()).text, /Expanded information/);
    await call("secondary", { ...args, selector: "#details", action: "Collapse" });
    assert.doesNotMatch((await state()).text, /Expanded information/);
    await call("secondary", { ...args, selector: "#quantity", action: "Increment" });
    assert.equal((await state()).elements.find((node) => node.name === "Quantity").value, "3");
    for (const inputMode of ["dom"]) {
        await call("hover", { ...args, selector: "#pad", inputMode });
        const { bounds } = (await state()).nodes.find((node) => node.name === "Pointer area");
        const x = bounds.x + 23;
        const y = bounds.y + 31;
        const pointer = async () => {
            const node = (await state()).nodes.find((node) => node.tag === "output" && node.name.startsWith("{"));
            return JSON.parse(node.value);
        };
        await call("click", { ...args, x, y, inputMode });
        assert.equal((await pointer()).click.x, 23, "Click keeps the supplied coordinate, not the element centre");
        assert.ok(
            Math.abs((await pointer()).click.y - 31) <= 1,
            "DOM mouse coordinates can round to integer CSS pixels",
        );
        assert.equal((await pointer()).click.trusted, inputMode === "trusted");
        await call("click", { ...args, x, y, inputMode, mouseButton: "right" });
        assert.equal((await pointer()).contextmenu.button, 2);
        await call("click", { ...args, x, y, inputMode, mouseButton: "middle" });
        assert.equal((await pointer()).auxclick.button, 1);
        await call("click", { ...args, x, y, inputMode, clickCount: 2 });
        assert.equal((await pointer()).dblclick.detail, 2);
        await call("drag", { ...args, inputMode, from: [x, y], to: [x + 70, y + 20] });
        assert.equal((await pointer()).pointerup.x, 93);
        assert.equal((await pointer()).pointerup.trusted, inputMode === "trusted");
    }
    if (args.browser === "chrome") {
        await call("focus", args);
        await call("fill", { ...args, selector: "#named", text: "Native text", inputMode: "trusted" });
        const nativeState = await state();
        assert.equal(nativeState.nodes.find((node) => node.ref === named.ref).value, "Native text");
        assert.equal(
            nativeState.nodes.find((node) => node.tag === "output" && node.name.startsWith('{"inputTrusted"')).value,
            '{"inputTrusted":true}',
        );
        const ax = await call("accessibility", args);
        assert.equal(ax.source, "chrome-accessibility");
        assert.ok(ax.nodes.some((node) => node.role === "textbox" && node.name === "Account name"));
    }
}
