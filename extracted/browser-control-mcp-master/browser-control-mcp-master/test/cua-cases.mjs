import assert from "node:assert/strict";

export async function cuaCases(client, browser, tabId, url) {
    const run = async (code, error = false) => {
        const result = await client.callTool({ name: "browser_run", arguments: { code } });
        assert.equal(!!result.isError, error, JSON.stringify(result));
        return result;
    };
    const api = await client.callTool({ name: "browser_api", arguments: {} });
    assert.match(api.content[0].text, /createBrowserTab/);
    await client.callTool({ name: "browser_reset", arguments: {} });
    let result = await run(`let tab = await cua.getTab(${tabId}, {browser:${JSON.stringify(browser)}});`);
    assert.match(result.content[0].text, /Source: dom-semantic/);
    result = await run("let state = await tab.getAXState({emit:false,disableDiffing:true}); nodeRepl.write(state);");
    const match = /\[(\d+)\] textbox "Account name"/.exec(result.content[0].text);
    assert.ok(match, "Semantic state provides an actionable numeric index");
    await run(`let field = ${match[1]}; await tab.setValue(field, 'Script text');`);
    result = await run("await tab.getAXState();");
    assert.match(result.content[0].text, /Changed: .*value="Script text"/);
    await run("await tab.selectText(field, 'text'); await tab.typeText('value');");
    result = await run("await tab.getAXState();");
    assert.match(result.content[0].text, /value="Script value"/);
    await run("await tab.pressKey('ctrl+a'); await tab.paste('Pasted');");
    result = await run("await tab.getAXStateAndScreenshot();");
    assert.match(result.content[0].text, /value="Pasted"/);
    assert.equal(result.content[1].type, "image");
    assert.equal(Buffer.from(result.content[1].data, "base64").subarray(1, 4).toString(), "PNG");
    await run("await tab.markHandoff();");
    result = await run(
        `nodeRepl.write((await cua.listTabs({browser:${JSON.stringify(browser)},emit:false})).find(t=>t.id===tab.id).mark);`,
    );
    assert.equal(result.content[0].text, "handoff");
    await run("await tab.reload();");
    result = await run("await tab.setValue(field, 'Must not run');", true);
    assert.match(result.content.at(-1).text, /stale element index/);
    await run("await tab.getAXState();");
    result = await run("await tab.getAXState();");
    assert.match(result.content[0].text, /No semantic state changes/);
    await run(
        `let task = await cua.createBrowserTab(${JSON.stringify(browser)}, ${JSON.stringify(url)}, {sessionName:'Script task'});`,
    );
    result = await run(
        `nodeRepl.write((await cua.listTabs({browser:${JSON.stringify(browser)},emit:false})).find(t=>t.id===task.id).sessionName);`,
    );
    assert.equal(result.content[0].text, "Script task");
    await run("await task.close();");
    await client.callTool({ name: "browser_reset", arguments: {} });
}
