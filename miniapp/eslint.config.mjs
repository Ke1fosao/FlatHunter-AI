import eslint from "@eslint/js";
import nextPlugin from "@next/eslint-plugin-next";
import tseslint from "typescript-eslint";

const typedFiles = ["**/*.{ts,tsx}"];
const typedConfigs = [
  ...tseslint.configs.strictTypeChecked,
  ...tseslint.configs.stylisticTypeChecked
].map((config) => ({ ...config, files: typedFiles }));

export default tseslint.config(
  {
    ignores: [".next/**", "node_modules/**", "coverage/**", "eslint.config.mjs"]
  },
  eslint.configs.recommended,
  ...typedConfigs,
  {
    files: typedFiles,
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname
      }
    },
    plugins: {
      "@next/next": nextPlugin
    },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      ...nextPlugin.configs["core-web-vitals"].rules,
      "@typescript-eslint/consistent-type-definitions": ["error", "type"],
      "@typescript-eslint/no-misused-promises": ["error", { "checksVoidReturn": false }]
    }
  },
  {
    files: ["src/types/**/*.d.ts"],
    rules: {
      "@typescript-eslint/consistent-type-definitions": "off"
    }
  },
  {
    files: ["**/*.test.{ts,tsx}", "vitest.config.ts"],
    rules: {
      "@typescript-eslint/no-unsafe-call": "off",
      "@typescript-eslint/no-unsafe-member-access": "off"
    }
  }
);

// Declaration merging requires an interface for Window.
