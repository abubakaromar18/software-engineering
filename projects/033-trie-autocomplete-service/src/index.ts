// Public API for using the trie and service as a library.
export { Trie, compareCompletions, type Completion } from "./trie.js";
export { AutocompleteService, ValidationError, type AutocompleteOptions } from "./autocomplete-service.js";
export { parseCorpus, loadCorpus, CorpusParseError, type CorpusEntry } from "./corpus.js";
export { normalize } from "./normalize.js";
export { loadConfig, DEFAULT_CONFIG, type AppConfig } from "./config.js";
export { createAutocompleteServer, type ServerOptions } from "./http/server.js";
