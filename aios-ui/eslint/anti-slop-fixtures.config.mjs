import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import antiSlop from "eslint-plugin-anti-slop";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const antiSlopConfig = JSON.parse(readFileSync(path.join(__dirname, "..", ".config", "anti-slop.json"), "utf8"));

const config = [
  {
    files: ["eslint/fixtures/anti-slop/pass/**/*.{js,jsx}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      "anti-slop": antiSlop,
    },
    settings: {
      "anti-slop": antiSlopConfig,
    },
    rules: {
      "anti-slop/no-unjustified-use-client": "error",
      "anti-slop/no-useless-memo": "warn",
      "anti-slop/no-placeholder-copy": "error",
      "anti-slop/no-marketing-copy": "warn",
      "anti-slop/require-empty-state-action": "warn",
      "anti-slop/no-demo-data-primary-path": "error",
      "anti-slop/no-generic-stat-label": "warn",
    },
  },
];

export default config;
