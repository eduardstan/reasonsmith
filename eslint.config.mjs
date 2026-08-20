import tseslint from "typescript-eslint";

const typeAware = {
  languageOptions: {
    parser: tseslint.parser,
    parserOptions: {
      project: ["./packages/*/tsconfig.json"],
      tsconfigRootDir: import.meta.dirname,
    },
  },
  plugins: { "@typescript-eslint": tseslint.plugin },
};

export default tseslint.config(
  {
    files: ["packages/**/*.{ts,tsx}"],
    ...typeAware,
    rules: {
      "@typescript-eslint/no-unnecessary-type-assertion": "error",
    },
  },
  {
    files: ["packages/**/*.tsx"],
    ...typeAware,
    rules: {
      "@typescript-eslint/prefer-readonly-parameter-types": ["error", { ignoreInferredTypes: true }],
    },
  },
);
