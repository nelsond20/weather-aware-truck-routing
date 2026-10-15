import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import hooks from 'eslint-plugin-react-hooks';
import a11y from 'eslint-plugin-jsx-a11y';
import storybook from 'eslint-plugin-storybook';
import globals from 'globals';
export default tseslint.config(
  { ignores: ['node_modules/**','vendor/**','dist/**','public/**','test-results/**','.cache/**'] },
  js.configs.recommended, ...tseslint.configs.recommended,
  ...storybook.configs['flat/recommended'],
  { files: ['**/*.{ts,tsx,js,mjs}'], languageOptions: { globals: { ...globals.browser,...globals.node } },
    plugins: { 'react-hooks': hooks,'jsx-a11y':a11y },
    rules: { ...hooks.configs.recommended.rules,...a11y.configs.recommended.rules,
      '@typescript-eslint/no-explicit-any':'error',
      '@typescript-eslint/ban-ts-comment':['error',{'ts-expect-error':'allow-with-description','ts-ignore':true}],
      'no-eval':'error','no-implied-eval':'error','no-new-func':'error',
      'no-restricted-syntax':['error',{selector:"JSXAttribute[name.name='style']",message:'Use CSS Modules.'},{selector:"JSXAttribute[name.name='dangerouslySetInnerHTML']",message:'Use safe text nodes.'}],
    } },
);
