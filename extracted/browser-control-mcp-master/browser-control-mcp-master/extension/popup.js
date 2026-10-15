/* global chrome */
const api = globalThis.browser ?? chrome;
const status = document.querySelector("#status");
const toggle = document.querySelector("#toggle");
let enabled = false;
let loadedSettings = false;
async function refresh() {
    try {
        const result = await api.runtime.sendMessage({ type: "status" });
        enabled = result.enabled;
        if (!loadedSettings) {
            document.querySelector("#idle-hours").value = result.idleHours;
            loadedSettings = true;
        }
        status.textContent = result.state;
        toggle.textContent = enabled ? "Disable browser control" : "Enable browser control";
        toggle.disabled = false;
    } catch (error) {
        status.textContent = error.message;
    }
}
toggle.addEventListener("click", async () => {
    toggle.disabled = true;
    try {
        await api.runtime.sendMessage({ type: "toggle", enabled: !enabled });
    } catch (error) {
        status.textContent = error.message;
    }
    await refresh();
});
void refresh();
document.querySelector("#cleanup-settings").addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = document.querySelector("#settings-status");
    try {
        const result = await api.runtime.sendMessage({
            type: "cleanup-settings",
            idleHours: Number(document.querySelector("#idle-hours").value),
        });
        status.textContent = result.error ?? "Saved.";
    } catch (error) {
        status.textContent = error.message;
    }
});
setInterval(refresh, 1000);
