import { it,expect } from 'vitest';
import { mkdtemp,writeFile,mkdir,readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join,resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import stylelint from 'stylelint';
it('CSS typings exclude both global forms and ignore comments',async()=>{
  const root=await mkdtemp(join(tmpdir(),'weather-css-'));await mkdir(join(root,'src'));
  await writeFile(join(root,'src','Demo.module.css'),'/* .fake {} */ .local, :global .external { color: var(--text); } :global(.thirdParty) { color: var(--text); }');
  execFileSync(process.execPath,[resolve('scripts/css-types.mjs')],{cwd:root});
  const result=await readFile(join(root,'src','Demo.module.css.d.ts'),'utf8');
  expect(result).toContain('"local"');expect(result).not.toContain('external');expect(result).not.toContain('thirdParty');expect(result).not.toContain('fake');
});
it('backported recursive glob preserves excludes, overrides and explicit files',async()=>{
  const root=await mkdtemp(join(tmpdir(),'weather-lint-'));await mkdir(join(root,'nested'));await mkdir(join(root,'node_modules'));
  await writeFile(join(root,'root.css'),'.root { color: var(--text); }');await writeFile(join(root,'nested','child.css'),'.child { color: var(--text); }');await writeFile(join(root,'node_modules','ignored.css'),'.x { color: red; }');
  const config={rules:{'color-no-invalid-hex':true},overrides:[{files:['nested/*.css'],rules:{'color-no-invalid-hex':true}}]};
  const result=await stylelint.lint({cwd:root,files:'**/*.css',config});
  expect(result.errored).toBe(false);expect(result.results).toHaveLength(2);
  const explicit=await stylelint.lint({cwd:root,files:'root.css',config});expect(explicit.results).toHaveLength(1);
  const excluded=await stylelint.lint({cwd:root,files:['**/*.css','!nested/**'],config});expect(excluded.results).toHaveLength(1);
});
it('retains standard CSS errors and strict token rules',async()=>{
  const invalid=await stylelint.lint({code:'.broken { color: #gggggg; }',config:{rules:{'color-no-invalid-hex':true}}});expect(invalid.errored).toBe(true);
  const standard=await stylelint.lint({code:'.ok { color: red; }',config:{extends:['stylelint-config-standard']}});expect(standard.errored).toBe(false);
  const token=await stylelint.lint({code:'.unsafe { color: red; }',config:{plugins:['stylelint-declaration-strict-value'],rules:{'scale-unlimited/declaration-strict-value':[['color'],{ignoreValues:['transparent']}]}}});expect(token.errored).toBe(true);
// Cold loading the complete upstream rule set competes with browser compilation.
},15000);
