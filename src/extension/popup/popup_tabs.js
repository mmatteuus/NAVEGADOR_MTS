/** UI de concessão explícita de uma ou mais abas ao agente. */
(function () {
  const list = document.getElementById('tab-access-list');
  const message = document.getElementById('tab-access-message');
  const count = document.getElementById('tab-access-count');
  const directory = document.getElementById('agent-directory');
  let agents = [];
  const send = (type, extra = {}) => new Promise(resolve => {
    chrome.runtime.sendMessage({ type, ...extra }, response => resolve(response || {}));
  });

  function render(tabs) {
    list.textContent = '';
    if (!tabs.length) { list.textContent = 'Nenhuma aba disponível.'; count.textContent = '0 abas selecionadas'; return; }
    tabs.forEach(tab => {
      const label = document.createElement('label');
      label.className = 'tab-access-item';
      const input = document.createElement('input');
      input.type = 'checkbox'; input.value = String(tab.id); input.checked = !!tab.allowedForAgent;
      input.disabled = tab.selectable === false;
      input.setAttribute('aria-label', `Permitir acesso para a aba ${tab.title || '(sem título)'}`);
      const text = document.createElement('span'); text.className = 'tab-access-text';
      const title = document.createElement('strong'); title.textContent = tab.title || '(sem título)';
      const url = document.createElement('small'); url.textContent = tab.url || '';
      const meta = document.createElement('small'); meta.textContent = `ID ${tab.id} · janela ${tab.windowId}${input.disabled ? ' · protegida' : ''}`;
      if (agents.length && tab.selectable !== false) {
        const select = document.createElement('select'); select.className = 'tab-agent-select';
        select.dataset.tabId = String(tab.id); select.setAttribute('aria-label', `Agente da aba ${title.textContent}`);
        select.dataset.expectedSessionId = tab.sessionId || '';
        if (!tab.sessionId) { const empty = document.createElement('option'); empty.value = ''; empty.textContent = 'Escolha o agente'; empty.selected = true; select.append(empty); }
        agents.forEach(agent => {
          const option = document.createElement('option'); option.value = agent.sessionId;
          option.textContent = agent.agentId ? `${agent.agentId} (${agent.sessionId.slice(0, 8)})` : agent.sessionId;
          option.selected = agent.sessionId === tab.sessionId; select.append(option);
        });
        text.append(select);
      }
      text.title = `${title.textContent} — ${url.textContent} (${meta.textContent})`;
      text.append(title, url, meta); label.append(input, text); list.append(label);
    });
    count.textContent = `${tabs.filter(tab => tab.allowedForAgent).length} abas selecionadas`;
    directory.textContent = agents.length ? `${agents.length} agente(s) conectado(s)` : 'Nenhum agente conectado';
  }

  async function load() {
    const response = await send('GET_TAB_GRANTS');
    if (!response.success) { message.textContent = response.error || 'Falha ao carregar abas.'; return; }
    agents = Array.isArray(response.agents) ? response.agents : [];
    render(response.data || []);
  }

  document.getElementById('save-tab-grants').addEventListener('click', async () => {
    const tabIds = [...list.querySelectorAll('input:checked')].map(input => Number(input.value));
    const selects = [...list.querySelectorAll('.tab-agent-select')];
    const assignments = selects
      .filter(select => tabIds.includes(Number(select.dataset.tabId)))
      .map(select => ({ tabId: Number(select.dataset.tabId), sessionId: select.value,
        expectedSessionId: select.dataset.expectedSessionId || '' }));
    const revocations = [...list.querySelectorAll('.tab-access-item')]
      .filter(row => !row.querySelector('input')?.checked)
      .map(row => row.querySelector('.tab-agent-select'))
      .filter(Boolean).map(select => ({ tabId: Number(select.dataset.tabId), expectedSessionId: select.dataset.expectedSessionId }))
      .filter(item => item.expectedSessionId);
    const response = await send(agents.length ? 'ASSIGN_TAB_GRANTS' : 'SAVE_TAB_GRANTS',
      agents.length ? { assignments, revocations } : { tabIds });
    message.textContent = response.success ? 'Seleção salva.' : (response.error || 'Falha ao salvar.');
    if (response.success) render(response.data || []);
  });

  document.getElementById('clear-tab-grants').addEventListener('click', async () => {
    const response = await send('CLEAR_TAB_GRANTS');
    message.textContent = response.success ? 'Seleção limpa.' : (response.error || 'Falha ao limpar.');
    if (response.success) render(response.data || []);
  });

  const urlInput = document.getElementById('new-agent-tab-url');
  if (urlInput) {
    urlInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('open-agent-tab')?.click();
      }
    });
  }

  document.getElementById('open-agent-tab').addEventListener('click', async () => {
    const input = document.getElementById('new-agent-tab-url');
    const response = await send('OPEN_GRANTED_TAB', { url: input.value });
    message.textContent = response.success ? 'Aba aberta e liberada.' : (response.error || 'URL recusada.');
    if (response.success) { input.value = ''; render(response.data || []); }
  });

  load();
}());
