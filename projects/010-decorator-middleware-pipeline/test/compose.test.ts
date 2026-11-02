import { describe, expect, it } from "vitest";
import { compose, Pipeline } from "../src/core/compose.js";
import { tracer } from "./support/fakes.js";

describe("compose", () => {
  it("wraps like an onion: first middleware is outermost", async () => {
    const trace: string[] = [];
    const handler = compose<number, number>([tracer("a", trace), tracer("b", trace), tracer("c", trace)])(
      async (n) => {
        trace.push("handler");
        return n * 2;
      },
    );

    await expect(handler(21)).resolves.toBe(42);
    expect(trace).toEqual(["a:in", "b:in", "c:in", "handler", "c:out", "b:out", "a:out"]);
  });

  it("is the identity when given no middlewares", async () => {
    const h = async (s: string) => s.toUpperCase();
    expect(compose<string, string>([])(h)).toBe(h);
  });

  it("propagates errors back through every layer", async () => {
    const trace: string[] = [];
    const handler = compose<void, never>([tracer("a", trace), tracer("b", trace)])(async () => {
      throw new Error("nope");
    });
    await expect(handler()).rejects.toThrow("nope");
    expect(trace).toEqual(["a:in", "b:in", "b:out", "a:out"]);
  });
});

describe("Pipeline", () => {
  it("describes layer order and builds the same chain as compose", async () => {
    const trace: string[] = [];
    const pipeline = Pipeline.create<number, number>().use(tracer("outer", trace)).use(tracer("inner", trace));

    expect(pipeline.describe()).toBe("outer → inner → handler");
    await pipeline.build(async (n) => n)(1);
    expect(trace).toEqual(["outer:in", "inner:in", "inner:out", "outer:out"]);
  });

  it("is immutable: use() returns a new pipeline and leaves the base unchanged", () => {
    const base = Pipeline.create<number, number>().use(tracer("base", []));
    const extended = base.use(tracer("extra", []));
    expect(base.describe()).toBe("base → handler");
    expect(extended.describe()).toBe("base → extra → handler");
  });
});
