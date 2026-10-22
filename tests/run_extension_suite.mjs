/** Executa regressões unitárias da extensão em processos isolados e seriais. */
import { readdirSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

const root = path.resolve('tests');
const files = readdirSync(root)
  .filter(name => /^test_extension_.*\.mjs$/.test(name) || name === 'test_agent_tab_policy.mjs')
  .sort();
const timeout = 60_000;
let failed = 0;

for (const file of files) {
  console.log(`[SUITE] ${file}`);
  const result = spawnSync(process.execPath, [path.join(root, file)], {
    stdio: 'inherit', timeout, windowsHide: true
  });
  if (result.status !== 0) {
    failed += 1;
    const reason = result.error?.code === 'ETIMEDOUT' ? 'timeout de 60s' : `exit=${result.status}`;
    console.error(`[FAIL] ${file}: ${reason}`);
  }
}

if (failed) {
  console.error(`[SUITE] ${failed}/${files.length} testes falharam.`);
  process.exit(1);
}
console.log(`[SUITE] ${files.length} testes passaram.`);
