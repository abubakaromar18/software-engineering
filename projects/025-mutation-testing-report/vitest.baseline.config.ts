import { defineConfig } from "vitest/config";

// The original "looks fine" suite, kept frozen so the baseline score is reproducible.
export default defineConfig({
  test: {
    include: ["test/baseline/**/*.test.ts"],
    coverage: { provider: "v8", include: ["src/**/*.ts"], exclude: ["src/index.ts"] },
  },
});
