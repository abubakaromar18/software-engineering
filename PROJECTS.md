# Project Roadmap

183 projects — one per day from Oct 24, 2026 through Apr 24, 2027. The daily build takes the first unchecked item.

Format: `NNN | Title | Language/stack | Level | Area | Description`

## Month 1 — Craft: clean code, design patterns, testing
### Week 1 · Clean code & SOLID
- [x] 001 | Gilded Rose Refactor | Python | Starter | Refactoring | Take a tangled legacy inventory kata, pin it with characterization tests, then refactor to clean code step by step with a commit-by-commit log in the README → [folder](projects/001-gilded-rose-refactor/)
- [x] 002 | SOLID by Example | TypeScript | Starter | Design principles | Five small before/after modules, one per SOLID principle, with tests proving behavior is unchanged → [folder](projects/002-solid-by-example/)
- [x] 003 | Dependency Injection Container | C# (.NET 8) | Intermediate | Design principles | A minimal IoC container with constructor injection, lifetimes (singleton/scoped/transient) and cycle detection → [folder](projects/003-dependency-injection-container/)
- [x] 004 | Value Objects & Money | Java 21 | Starter | Domain modeling | Immutable Money/Currency value objects with exact arithmetic, allocation without losing cents, and equality semantics → [folder](projects/004-value-objects-and-money/)
- [ ] 005 | Linter Rule Pack | JavaScript (ESLint plugin) | Intermediate | Code quality | Custom ESLint rules (no magic numbers in business logic, max function params, banned imports) with RuleTester tests
- [ ] 006 | Code Smell Detector | Python (ast) | Intermediate | Static analysis | Scan Python code for long methods, deep nesting, large classes and duplicate blocks; report with severity scores
- [ ] 007 | Error Handling Patterns | Rust | Intermediate | Reliability | Library showing Result-based errors, error enums, context wrapping and a CLI that surfaces errors cleanly
### Week 2 · Creational & structural patterns
- [ ] 008 | Pizza Builder & Factory | Java 21 | Starter | Design patterns | Builder, Factory Method and Abstract Factory applied to an ordering system, with tests per pattern
- [ ] 009 | Plugin System with Adapters | Go | Intermediate | Design patterns | Adapter + Registry pattern loading payment-provider adapters behind one interface
- [ ] 010 | Decorator Middleware Pipeline | TypeScript (Node) | Intermediate | Design patterns | Compose logging, retry, caching and timing decorators around a service; ordering semantics tested
- [ ] 011 | Composite File Tree | C++20 | Starter | Design patterns | Composite + Visitor computing sizes, searching and printing a virtual filesystem tree
- [ ] 012 | Facade over a Messy API | Python | Starter | Design patterns | Wrap a simulated legacy shipping SDK behind a clean facade with typed inputs and tests
- [ ] 013 | Flyweight Text Renderer | Kotlin | Intermediate | Design patterns | Flyweight glyph cache for a text editor model; benchmark memory with and without sharing
- [ ] 014 | Proxy & Lazy Loading | C# (.NET 8) | Intermediate | Design patterns | Virtual, protection and caching proxies around a slow repository
### Week 3 · Behavioral patterns
- [ ] 015 | Undoable Text Editor | TypeScript | Intermediate | Design patterns | Command pattern with undo/redo stacks, macro commands and memento snapshots
- [ ] 016 | Strategy Pricing Engine | Python | Starter | Design patterns | Pluggable discount/tax strategies selected by rules, fully unit tested
- [ ] 017 | Observer Stock Ticker | Go | Starter | Design patterns | Pub/sub observers with goroutines and channels, unsubscribe and backpressure handling
- [ ] 018 | State Machine Vending | Rust | Intermediate | Design patterns | Type-state pattern vending machine where illegal transitions fail to compile
- [ ] 019 | Chain of Responsibility Support Desk | Java 21 | Starter | Design patterns | Ticket escalation chain with configurable handlers and audit trail
- [ ] 020 | Template Method Report Generator | C# (.NET 8) | Starter | Design patterns | CSV/JSON/HTML exporters sharing a template algorithm with hook methods
- [ ] 021 | Interpreter for Rules DSL | Python | Advanced | Design patterns | Interpreter pattern for a small business-rules language with parser, AST and evaluator
### Week 4 · Testing discipline
- [ ] 022 | TDD Bowling Kata Journal | JavaScript (Vitest) | Starter | Testing | Bowling scorer built strictly red-green-refactor with git history documenting each step
- [ ] 023 | Property-Based Testing Lab | Python (Hypothesis) | Intermediate | Testing | Property tests that find real bugs in a sorting, encoding and date-range library
- [ ] 024 | Mocks, Stubs & Fakes | Java 21 (JUnit 5, Mockito) | Intermediate | Testing | Same service tested with each kind of test double; README explains trade-offs
- [ ] 025 | Mutation Testing Report | TypeScript (Stryker) | Intermediate | Testing | Library with mutation testing wired in; raise mutation score from baseline with documented changes
- [ ] 026 | Contract Testing | Node + Python (Pact) | Advanced | Testing | Consumer-driven contracts between a JS client and a Python API, verified in CI
- [ ] 027 | Snapshot & Golden-File Tests | Go | Starter | Testing | CLI formatter tested with golden files and an -update flag
- [ ] 028 | Mini Test Framework | C | Intermediate | Testing | Write an xUnit-style test runner in C with assertions, fixtures and a summary report

## Month 2 — Foundations: data structures, algorithms, APIs, data
### Week 5 · Data structures from scratch
- [ ] 029 | Generic Hash Map | Rust | Intermediate | Data structures | Open-addressing hash map with Robin Hood hashing, resizing and benchmarks against std
- [ ] 030 | LRU & LFU Caches | Go | Intermediate | Data structures | O(1) LRU and LFU caches with generics, concurrency-safe variants and tests
- [ ] 031 | Persistent Immutable List | Haskell | Intermediate | Data structures | Persistent list/vector with structural sharing, QuickCheck properties
- [ ] 032 | Skip List | Java 21 | Intermediate | Data structures | Probabilistic skip list with range queries and iterator, compared to TreeMap
- [ ] 033 | Trie Autocomplete Service | TypeScript | Starter | Data structures | Trie with prefix search, frequency ranking and a tiny HTTP endpoint
- [ ] 034 | Binary Heap & Priority Queue | C++20 | Starter | Data structures | Template heap with decrease-key and heapsort, used in a task scheduler demo
- [ ] 035 | Bloom Filter & Count-Min Sketch | Python | Intermediate | Data structures | Probabilistic structures with tunable error rates and empirical accuracy charts
### Week 6 · Algorithms in practice
- [ ] 036 | Graph Route Planner | Python | Intermediate | Algorithms | Dijkstra, A* and Bellman-Ford on a city graph with path visualization in the terminal
- [ ] 037 | Diff Tool (Myers) | Go | Advanced | Algorithms | Line diff using the Myers algorithm with unified diff output and tests against known cases
- [ ] 038 | Rate-Limited Job Scheduler | Kotlin | Intermediate | Algorithms | Topological sort for dependencies plus interval scheduling for resources
- [ ] 039 | Text Search Engine | Rust | Advanced | Algorithms | Inverted index with tokenization, TF-IDF/BM25 ranking and phrase queries
- [ ] 040 | Huffman Compressor | C | Intermediate | Algorithms | File compressor/decompressor with bit I/O and round-trip tests
- [ ] 041 | Dynamic Programming Workbench | Python | Starter | Algorithms | Knapsack, edit distance, LIS with memoized vs tabulated versions and timing comparisons
- [ ] 042 | Sudoku Solver with Constraint Propagation | TypeScript | Intermediate | Algorithms | Backtracking + constraint propagation solver with a web UI
### Week 7 · API design
- [ ] 043 | REST API Done Right | Python (FastAPI) | Intermediate | API design | Resource API with pagination, filtering, ETags, problem+json errors and OpenAPI docs
- [ ] 044 | GraphQL Server | TypeScript (Apollo) | Intermediate | API design | Schema-first GraphQL API with DataLoader batching to fix N+1 queries
- [ ] 045 | gRPC Service | Go | Intermediate | API design | Protobuf-defined service with unary and streaming RPCs, deadlines and interceptors
- [ ] 046 | API Versioning Strategies | C# (ASP.NET Core) | Intermediate | API design | Same API versioned by URL, header and media type with deprecation headers
- [ ] 047 | Rate Limiter Middleware | Go | Intermediate | API design | Token bucket, leaky bucket and sliding window limiters with tests and benchmarks
- [ ] 048 | Idempotency Keys | Java 21 (Spring Boot) | Intermediate | API design | Payment endpoint safe to retry using idempotency keys and stored responses
- [ ] 049 | Webhook Delivery System | Node (TypeScript) | Advanced | API design | Signed webhooks with retries, exponential backoff, dead-letter list and replay
### Week 8 · Databases & persistence
- [ ] 050 | Schema Migrations Tool | Python | Intermediate | Databases | Versioned up/down SQL migrations with checksums and a migration history table (SQLite)
- [ ] 051 | Repository & Unit of Work | C# (.NET 8, EF Core) | Intermediate | Databases | Persistence patterns with transactional unit of work and in-memory test doubles
- [ ] 052 | Query Optimization Lab | SQL (PostgreSQL) | Intermediate | Databases | Seeded dataset, slow queries, EXPLAIN ANALYZE before/after indexes, documented findings
- [ ] 053 | B+ Tree Index | Rust | Advanced | Databases | Disk-page B+ tree with insert, delete, range scan and persistence to a file
- [ ] 054 | LSM Key-Value Store | Go | Advanced | Databases | Memtable, WAL, SSTables and compaction for a small embedded KV store
- [ ] 055 | Transaction Isolation Demo | Java 21 + PostgreSQL | Intermediate | Databases | Reproduce dirty reads, lost updates and write skew; fix with isolation levels and locking
- [ ] 056 | Optimistic Locking Inventory | TypeScript (Prisma) | Starter | Databases | Version-column optimistic concurrency with conflict handling and tests

## Month 3 — Architecture & concurrency
### Week 9 · Architecture styles
- [ ] 057 | Hexagonal Architecture Bank | Java 21 | Intermediate | Architecture | Ports-and-adapters banking core with swappable REST/CLI adapters and in-memory/SQL persistence
- [ ] 058 | Clean Architecture Todo | TypeScript | Intermediate | Architecture | Entities, use cases, interface adapters and frameworks layers with dependency rule enforced by lint
- [ ] 059 | CQRS Library System | C# (.NET 8) | Advanced | Architecture | Separate command and query models with a projection-updated read store
- [ ] 060 | Event-Sourced Shopping Cart | Kotlin | Advanced | Architecture | Event store, aggregates, snapshots and rebuildable projections
- [ ] 061 | DDD Bounded Contexts | Python | Advanced | Architecture | Ordering and Shipping contexts with aggregates, domain events and an anti-corruption layer
- [ ] 062 | Modular Monolith | Go | Intermediate | Architecture | One deployable with enforced module boundaries and internal APIs
- [ ] 063 | Architecture Decision Records | Markdown + Node CLI | Starter | Architecture | ADR CLI that creates, links, supersedes and indexes decision records
### Week 10 · Concurrency
- [ ] 064 | Thread Pool from Scratch | C++20 | Advanced | Concurrency | Work-stealing thread pool with futures and graceful shutdown
- [ ] 065 | Producer-Consumer Pipelines | Go | Intermediate | Concurrency | Fan-out/fan-in pipeline with context cancellation and bounded channels
- [ ] 066 | Async Web Crawler | Python (asyncio) | Intermediate | Concurrency | Polite concurrent crawler of a local test site with semaphores and robots handling
- [ ] 067 | Actor Model Chat | Elixir | Intermediate | Concurrency | GenServer-based chat rooms with supervision trees and crash recovery
- [ ] 068 | Lock-Free Queue | Rust | Advanced | Concurrency | Michael-Scott lock-free queue with atomics, loom tests and benchmarks
- [ ] 069 | Deadlock Detector | Java 21 | Intermediate | Concurrency | Wait-for graph detection on instrumented locks with a reproducible deadlock demo
- [ ] 070 | Parallel Map-Reduce | Scala | Intermediate | Concurrency | Word-count and log analytics using parallel collections and futures
### Week 11 · Distributed systems
- [ ] 071 | Raft Consensus | Go | Advanced | Distributed systems | Leader election and log replication over simulated network with partition tests
- [ ] 072 | Consistent Hashing Ring | Python | Intermediate | Distributed systems | Ring with virtual nodes; show key movement when nodes join and leave
- [ ] 073 | Vector Clocks & CRDTs | TypeScript | Advanced | Distributed systems | G-Counter, PN-Counter, OR-Set and LWW register with merge property tests
- [ ] 074 | Gossip Membership | Rust | Advanced | Distributed systems | SWIM-style failure detection across simulated nodes
- [ ] 075 | Saga Orchestrator | Java 21 | Advanced | Distributed systems | Order saga with compensating actions and failure injection
- [ ] 076 | Two-Phase Commit | Python | Intermediate | Distributed systems | Coordinator and participants with crash scenarios and recovery log
- [ ] 077 | Distributed Lock Service | Go + Redis | Intermediate | Distributed systems | Leases with fencing tokens and an explanation of why naive locks fail
### Week 12 · Networking
- [ ] 078 | HTTP/1.1 Server from Sockets | C | Advanced | Networking | Socket-level HTTP server with keep-alive, static files and request parsing tests
- [ ] 079 | Reverse Proxy & Load Balancer | Go | Intermediate | Networking | Round-robin, least-connections and health checks for local backends
- [ ] 080 | WebSocket Chat | TypeScript (Node) | Intermediate | Networking | Hand-rolled WebSocket framing plus rooms and presence
- [ ] 081 | DNS Resolver | Rust | Advanced | Networking | Iterative DNS resolver parsing wire-format messages (tested on recorded fixtures)
- [ ] 082 | TCP Port Scanner for Localhost | Python | Starter | Networking | Concurrent scanner restricted to localhost/own hosts with service banners
- [ ] 083 | Reliable UDP Transfer | Go | Advanced | Networking | Sliding-window ARQ protocol over UDP with simulated loss
- [ ] 084 | Packet Parser | C++20 | Intermediate | Networking | Parse pcap files into Ethernet/IP/TCP/UDP layers and print summaries

## Month 4 — Security, DevOps, observability, performance
### Week 13 · Security engineering (defensive)
- [ ] 085 | Password Hashing Service | Go | Intermediate | Security | Argon2id hashing, pepper, rehash-on-login and timing-safe compare
- [ ] 086 | JWT Auth with Refresh Rotation | TypeScript (Express) | Intermediate | Security | Access/refresh tokens with rotation, reuse detection and revocation
- [ ] 087 | OAuth 2.0 PKCE Flow | Python (Flask) | Advanced | Security | Local authorization server and client implementing auth code + PKCE
- [ ] 088 | Input Validation & OWASP Fixes | Java 21 (Spring Boot) | Intermediate | Security | Deliberately vulnerable local app and the fixed version for SQLi, XSS and CSRF with tests
- [ ] 089 | Secrets Scanner | Rust | Intermediate | Security | Scan a repo for high-entropy strings and key patterns; pre-commit hook
- [ ] 090 | RBAC & ABAC Authorization | C# (.NET 8) | Intermediate | Security | Policy engine supporting roles and attribute rules with test matrix
- [ ] 091 | Audit Log with Hash Chain | Python | Intermediate | Security | Tamper-evident append-only log verified by hash chaining
### Week 14 · DevOps & delivery
- [ ] 092 | Dockerized Multi-Service App | Docker Compose (Node + Postgres + Redis) | Intermediate | DevOps | Multi-stage builds, healthchecks, non-root users and a Makefile
- [ ] 093 | CI Pipeline Template | GitHub Actions | Starter | DevOps | Reusable workflows: lint, test matrix, coverage, caching and release on tag
- [ ] 094 | Infrastructure as Code | Terraform | Intermediate | DevOps | Modules for a VPC + app stack with variables, outputs and validated plans (no apply)
- [ ] 095 | Kubernetes Manifests & Helm | Kubernetes + Helm | Intermediate | DevOps | Deployment, service, HPA, probes and config, linted and template-tested
- [ ] 096 | Blue-Green Deploy Simulator | Python | Intermediate | DevOps | Simulate blue-green and canary rollouts with automated rollback on error rate
- [ ] 097 | Semantic Release Tool | Go | Intermediate | DevOps | Parse conventional commits, bump versions and generate a changelog
- [ ] 098 | Feature Flag Service | TypeScript | Intermediate | DevOps | Flags with percentage rollouts, targeting rules and an SDK
### Week 15 · Observability & reliability
- [ ] 099 | Structured Logging Library | Python | Starter | Observability | JSON logs with context propagation, levels and redaction of sensitive fields
- [ ] 100 | Metrics & Prometheus Exporter | Go | Intermediate | Observability | Counters, histograms and a /metrics endpoint with example Grafana dashboard JSON
- [ ] 101 | Distributed Tracing Demo | Node + OpenTelemetry | Intermediate | Observability | Trace requests across three services with spans and context propagation
- [ ] 102 | Circuit Breaker | Java 21 | Intermediate | Reliability | Closed/open/half-open breaker with sliding window stats and fallbacks
- [ ] 103 | Retry & Backoff Library | Rust | Starter | Reliability | Exponential backoff with jitter, retry budgets and classification of retryable errors
- [ ] 104 | Chaos Testing Harness | Python | Intermediate | Reliability | Inject latency, errors and dropped connections into a local service and report SLO impact
- [ ] 105 | SLO Calculator & Error Budgets | TypeScript | Starter | Reliability | Compute SLIs from logs, burn rates and alerts
### Week 16 · Performance engineering
- [ ] 106 | Profiling Case Study | Python | Intermediate | Performance | Profile a slow program with cProfile/py-spy, fix hot spots, document 10x speedup
- [ ] 107 | Benchmark Harness | Rust (Criterion) | Intermediate | Performance | Benchmark data structure choices with statistical comparison
- [ ] 108 | Cache Strategies | Go + Redis | Intermediate | Performance | Cache-aside, write-through, write-behind and stampede protection compared
- [ ] 109 | Memory Leak Hunt | Node (TypeScript) | Intermediate | Performance | Reproduce and fix leaks using heap snapshots, with the investigation written up
- [ ] 110 | Load Testing Suite | k6 (JavaScript) | Starter | Performance | Load, stress and soak tests against a local API with thresholds
- [ ] 111 | SIMD Image Filters | C++20 | Advanced | Performance | Scalar vs SIMD blur/grayscale filters with benchmarks
- [ ] 112 | Database Connection Pool | Java 21 | Intermediate | Performance | Pool with max size, idle eviction, validation and wait timeouts

## Month 5 — Systems & languages, frontend, mobile, tooling
### Week 17 · Compilers & interpreters
- [ ] 113 | Tokenizer & Recursive-Descent Parser | Python | Intermediate | Compilers | Arithmetic and boolean expression parser with precedence climbing and error messages
- [ ] 114 | Tree-Walking Interpreter | Go | Advanced | Compilers | Small language with variables, functions, closures and a REPL
- [ ] 115 | Bytecode VM | Rust | Advanced | Compilers | Compile a tiny language to bytecode and run it on a stack VM
- [ ] 116 | JSON Parser | C | Intermediate | Compilers | Spec-compliant JSON parser tested against a conformance suite
- [ ] 117 | Regex Engine | TypeScript | Advanced | Compilers | Thompson NFA construction with matching and a test corpus
- [ ] 118 | Static Type Checker | OCaml | Advanced | Compilers | Hindley-Milner type inference for a mini-ML
- [ ] 119 | Template Engine | Ruby | Intermediate | Compilers | Mustache-like templates with partials, escaping and caching compiled templates
### Week 18 · Operating systems concepts
- [ ] 120 | Unix Shell | C | Advanced | Operating systems | Pipes, redirection, job control and builtins
- [ ] 121 | Memory Allocator | C | Advanced | Operating systems | malloc/free with free lists, coalescing and fragmentation stats
- [ ] 122 | CPU Scheduler Simulator | Python | Intermediate | Operating systems | FCFS, SJF, Round Robin and MLFQ with Gantt chart output
- [ ] 123 | Virtual Memory Simulator | Java 21 | Intermediate | Operating systems | Page tables, TLB and FIFO/LRU/Clock replacement with fault statistics
- [ ] 124 | File System in a File | Rust | Advanced | Operating systems | Inode-based filesystem image with mkdir/ls/cat/write tools
- [ ] 125 | Process Monitor | Go | Intermediate | Operating systems | top-like TUI reading /proc for CPU, memory and processes
- [ ] 126 | Container from Scratch | Go | Advanced | Operating systems | Namespaces, chroot and cgroups to run an isolated process (Linux)
### Week 19 · Frontend engineering
- [ ] 127 | Component Library | React + TypeScript + Storybook | Intermediate | Frontend | Accessible buttons, modals and forms with stories and interaction tests
- [ ] 128 | State Management from Scratch | TypeScript | Intermediate | Frontend | Build a Redux-like store with middleware and selectors, then a signals version
- [ ] 129 | Accessibility Audit & Fix | HTML/CSS/JS | Starter | Frontend | Take an inaccessible page to WCAG AA with axe tests and a written audit
- [ ] 130 | Virtual DOM | JavaScript | Advanced | Frontend | Minimal virtual DOM with diffing, keyed reconciliation and components
- [ ] 131 | Offline-First PWA | TypeScript (Vite) | Intermediate | Frontend | Service worker caching, IndexedDB sync queue and conflict handling
- [ ] 132 | Micro-Frontends | Webpack Module Federation | Advanced | Frontend | Shell app composing two independently built frontends
- [ ] 133 | E2E Testing Suite | Playwright | Intermediate | Frontend | Page objects, fixtures and visual regression for a sample app
### Week 20 · Mobile, desktop & CLI craft
- [ ] 134 | Cross-Platform Habit App | Flutter (Dart) | Intermediate | Mobile | BLoC state management, local persistence and widget tests
- [ ] 135 | Native Notes App | Kotlin (Jetpack Compose) | Intermediate | Mobile | MVVM, Room database and unit tests for view models
- [ ] 136 | SwiftUI Expense Tracker | Swift | Intermediate | Mobile | MVVM with Combine and XCTest (build notes for macOS)
- [ ] 137 | Desktop Markdown Editor | Tauri (Rust + TypeScript) | Intermediate | Desktop | Live preview, file system access and IPC between frontend and backend
- [ ] 138 | Polished CLI Toolkit | Python (Typer + Rich) | Starter | CLI | Subcommands, config files, colored output, shell completion and tests
- [ ] 139 | TUI Kanban | Go (Bubble Tea) | Intermediate | CLI | Terminal kanban board with keyboard navigation and persistence
- [ ] 140 | Cross-Platform Release Builds | Rust + GitHub Actions | Intermediate | CLI | CLI built for Linux/macOS/Windows with checksums and install script
### Week 21 · Developer tooling
- [ ] 141 | Static Site Generator | Go | Intermediate | Tooling | Markdown to HTML with templates, front matter and incremental builds
- [ ] 142 | Build System | Python | Advanced | Tooling | Dependency graph, content-hash caching and parallel task execution
- [ ] 143 | Package Version Resolver | TypeScript | Advanced | Tooling | Semver constraint solver with conflict explanations
- [ ] 144 | Git Internals | Python | Advanced | Tooling | Implement init/add/commit/log/cat-file on real .git object format
- [ ] 145 | Code Formatter | Rust | Intermediate | Tooling | Formatter for a small language with idempotency tests
- [ ] 146 | Language Server | TypeScript (LSP) | Advanced | Tooling | LSP for a tiny config language: diagnostics, hover and completion
- [ ] 147 | Pre-commit Framework | Go | Intermediate | Tooling | Configurable hooks with parallel runs and staged-file filtering

## Month 6 — Data, messaging, ML engineering, capstones
### Week 22 · Messaging & event-driven
- [ ] 148 | Message Broker | Go | Advanced | Messaging | Topics, partitions, consumer groups and offsets persisted to disk
- [ ] 149 | Outbox Pattern | Java 21 (Spring Boot) + Postgres | Intermediate | Messaging | Transactional outbox with a relay for reliable event publishing
- [ ] 150 | Kafka Stream Processing | Python + Kafka (docker compose) | Intermediate | Messaging | Windowed aggregations of clickstream events
- [ ] 151 | Dead-Letter & Retry Queues | TypeScript + RabbitMQ | Intermediate | Messaging | Retry topologies with delays and poison-message handling
- [ ] 152 | Event Schema Registry | Rust | Intermediate | Messaging | Store schema versions and check backward/forward compatibility
- [ ] 153 | Job Queue with Workers | Ruby (Sidekiq-like) + Redis | Intermediate | Messaging | Reliable job queue with retries, scheduled jobs and a dashboard
- [ ] 154 | Exactly-Once Illusion | Python | Intermediate | Messaging | Show at-least-once delivery plus idempotent consumers and dedup stores
### Week 23 · Data engineering
- [ ] 155 | ETL Pipeline | Python (Polars) | Intermediate | Data engineering | Extract, validate, transform and load with data quality checks and tests
- [ ] 156 | Workflow Orchestrator | Go | Advanced | Data engineering | DAG scheduler with retries, backfills and a status API
- [ ] 157 | Columnar File Format | Rust | Advanced | Data engineering | Write/read a simple columnar format with dictionary and RLE encoding
- [ ] 158 | dbt Analytics Project | SQL (dbt + DuckDB) | Intermediate | Data engineering | Staging/marts models, tests and documentation on a sample dataset
- [ ] 159 | Change Data Capture | Python + Postgres | Advanced | Data engineering | Logical replication consumer streaming row changes to a sink
- [ ] 160 | Data Contract Validator | TypeScript | Starter | Data engineering | Validate datasets against YAML contracts with clear reports
- [ ] 161 | SQL Query Engine | Java 21 | Advanced | Data engineering | Parse SELECT/WHERE/JOIN/GROUP BY over CSV with a volcano iterator model
### Week 24 · ML engineering & AI systems
- [ ] 162 | Model Serving API | Python (FastAPI + scikit-learn) | Intermediate | ML engineering | Versioned model registry, input validation and latency metrics
- [ ] 163 | Feature Store Lite | Python | Intermediate | ML engineering | Offline/online feature consistency with point-in-time joins
- [ ] 164 | ML Pipeline with Experiment Tracking | Python (MLflow) | Intermediate | ML engineering | Reproducible training pipeline with params, metrics and artifacts tracked
- [ ] 165 | Vector Search Index | Rust | Advanced | ML engineering | HNSW approximate nearest neighbor index with recall benchmarks
- [ ] 166 | RAG Service | TypeScript | Advanced | AI systems | Retrieval-augmented QA with chunking, embeddings interface (mockable) and evaluation set
- [ ] 167 | LLM Eval Harness | Python | Intermediate | AI systems | Run prompt test cases against pluggable model backends (mocked in tests) and score them
- [ ] 168 | Data Drift Monitor | Python | Intermediate | ML engineering | PSI/KS drift detection with alert reports
### Week 25 · Full-stack capstones I
- [ ] 169 | Realtime Collaborative Whiteboard | TypeScript (React + Node + WebSockets) | Advanced | Full-stack | CRDT-based shared canvas with presence and persistence
- [ ] 170 | URL Shortener at Scale | Go + Postgres + Redis | Advanced | System design | Base62 IDs, caching, analytics and a capacity planning write-up
- [ ] 171 | E-commerce Checkout | Java 21 (Spring Boot) + React | Advanced | Full-stack | Cart, inventory reservation, payments (mock) and order state machine
- [ ] 172 | Multi-Tenant SaaS Starter | Next.js + Prisma + Postgres | Advanced | Full-stack | Tenant isolation, auth, billing stubs and row-level security
- [ ] 173 | Ride-Matching Service | Kotlin (Ktor) | Advanced | System design | Geospatial indexing for driver matching with simulation
- [ ] 174 | Notification Service | Python + Redis | Intermediate | System design | Email/SMS/push fan-out (mocked providers) with templates, preferences and rate limits
- [ ] 175 | Ticket Booking System | C# (.NET 8) | Advanced | System design | Seat holds with expiry and concurrency-safe booking
### Week 26 · Capstones II
- [ ] 176 | Mini Cloud Storage | Go | Advanced | System design | Chunked uploads, deduplication, metadata service and resumable transfers
- [ ] 177 | Search-as-a-Service | Rust + TypeScript | Advanced | System design | Indexing API, query DSL and admin UI on top of an inverted index
- [ ] 178 | Observability Platform Lite | Go + React | Advanced | Observability | Ingest logs and metrics, query them, and chart dashboards
- [ ] 179 | CI Server | Python | Advanced | DevOps | Webhook-triggered builds in containers with logs and status API
- [ ] 180 | Social Feed System | Elixir (Phoenix) | Advanced | System design | Fan-out-on-write vs read feeds with live updates
- [ ] 181 | Banking Ledger | Rust | Advanced | System design | Double-entry ledger with idempotent transfers and reconciliation
- [ ] 182 | Distributed Key-Value Store | Go | Advanced | Distributed systems | Combine Raft, consistent hashing and LSM storage from earlier projects into one system
- [ ] 183 | Portfolio Retrospective | Markdown + Python | Starter | Engineering practice | Generate a portfolio index of all 183 projects by concept and language with stats and lessons learned
