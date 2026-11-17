import { defineConfig } from "vitest/config";

// Default suite: the strengthened tests that raised the mutation score.
export default defineConfig({
  test: {
    include: ["test/strengthened/**/*.test.ts"],
    coverage: { provider: "v8", include: ["src/**/*.ts"], exclude: ["src/index.ts"] },
  },
});
