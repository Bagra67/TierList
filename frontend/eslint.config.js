import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
// Fork maintenu d'eslint-plugin-jsx-a11y (mêmes règles), compatible avec ESLint 10
import jsxA11y from 'eslint-plugin-jsx-a11y-x';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import { defineConfig, globalIgnores } from 'eslint/config';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default defineConfig([
  // schema.d.ts est généré par `pnpm gen:api` depuis backend/openapi.json : ne pas le modifier à la main
  globalIgnores(['dist', 'src/api/schema.d.ts']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      // Accessibilité du JSX : textes alternatifs, labels, rôles ARIA, interactions au clavier
      jsxA11y.configs.recommended,
    ],
    languageOptions: {
      ecmaVersion: 2023,
      globals: globals.browser,
    },
  },
  // Composants shadcn/ui : ils exportent aussi leurs variantes (ex. buttonVariants) ; les garder
  // proches de la version générée facilite leur mise à jour
  {
    files: ['src/components/ui/**/*.tsx'],
    rules: { 'react-refresh/only-export-components': 'off' },
  },
  // Doit rester en dernier : désactive les règles ESLint qui entrent en conflit avec Prettier
  prettier,
]);
