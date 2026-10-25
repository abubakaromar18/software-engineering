import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    // Undo any vi.spyOn()/vi.fn() changes after each test so tests stay independent.
    restoreMocks: true,
  },
});
