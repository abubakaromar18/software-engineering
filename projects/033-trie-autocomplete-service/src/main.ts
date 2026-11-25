// Composition root: the only place that touches process.env, disk and the network.
import { AutocompleteService } from "./autocomplete-service.js";
import { loadConfig } from "./config.js";
import { loadCorpus } from "./corpus.js";
import { createAutocompleteServer } from "./http/server.js";

async function main(): Promise<void> {
  const config = loadConfig(process.env);
  const service = new AutocompleteService(config);
  service.load(await loadCorpus(config.corpusPath));

  const server = createAutocompleteServer(service);
  server.listen(config.port, config.host, () => {
    console.log(`autocomplete: ${service.size} words, listening on http://${config.host}:${config.port}`);
  });

  // Graceful shutdown: stop accepting connections, let in-flight requests finish.
  const shutdown = (signal: string): void => {
    console.log(`received ${signal}, shutting down`);
    server.close(() => process.exit(0));
  };
  process.once("SIGINT", () => shutdown("SIGINT"));
  process.once("SIGTERM", () => shutdown("SIGTERM"));
}

main().catch((err: unknown) => {
  console.error("failed to start:", err instanceof Error ? err.message : err);
  process.exit(1);
});
