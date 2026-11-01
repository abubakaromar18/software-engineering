// Package registry implements the plugin registry: adapters register a
// Factory under a unique name (typically from an init function, the same
// way database/sql drivers and image decoders do), and the application opens
// a Processor by name from configuration without importing any vendor code.
package registry

import (
	"errors"
	"fmt"
	"sort"
	"strings"
	"sync"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
)

// Config is the flat key/value settings bag handed to a Factory. A flat map
// keeps the registry independent of each adapter's settings shape; each
// adapter validates what it needs.
type Config map[string]string

// Require returns the value for key or an error naming the missing key.
func (c Config) Require(key string) (string, error) {
	v := strings.TrimSpace(c[key])
	if v == "" {
		return "", fmt.Errorf("missing required config %q", key)
	}
	return v, nil
}

// GetOr returns the value for key, or def when it is unset.
func (c Config) GetOr(key, def string) string {
	if v := strings.TrimSpace(c[key]); v != "" {
		return v
	}
	return def
}

// Factory builds a configured Processor. Returning an error (rather than
// panicking) lets misconfiguration surface at startup with a clear message.
type Factory func(cfg Config) (payment.Processor, error)

// Errors returned by the registry.
var (
	ErrUnknownProvider   = errors.New("unknown payment provider")
	ErrDuplicateProvider = errors.New("payment provider already registered")
)

// Registry is a concurrency-safe name → Factory map. The zero value is not
// usable; call New.
type Registry struct {
	mu        sync.RWMutex
	factories map[string]Factory
}

// New returns an empty registry. Tests use private registries so they never
// depend on global state.
func New() *Registry {
	return &Registry{factories: make(map[string]Factory)}
}

func normalise(name string) string { return strings.ToLower(strings.TrimSpace(name)) }

// Register adds a factory. Names are case-insensitive. Registering the same
// name twice is an error: silently replacing a payment adapter would be a
// nasty surprise.
func (r *Registry) Register(name string, f Factory) error {
	key := normalise(name)
	if key == "" {
		return errors.New("provider name must not be empty")
	}
	if f == nil {
		return fmt.Errorf("provider %q: factory must not be nil", key)
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, exists := r.factories[key]; exists {
		return fmt.Errorf("%w: %q", ErrDuplicateProvider, key)
	}
	r.factories[key] = f
	return nil
}

// MustRegister is Register for use in init functions, where a duplicate name
// is a programming error that should fail fast at program start.
func (r *Registry) MustRegister(name string, f Factory) {
	if err := r.Register(name, f); err != nil {
		panic(err)
	}
}

// Open builds a Processor for the named provider.
func (r *Registry) Open(name string, cfg Config) (payment.Processor, error) {
	key := normalise(name)
	r.mu.RLock()
	f, ok := r.factories[key]
	r.mu.RUnlock()
	if !ok {
		return nil, fmt.Errorf("%w: %q (registered: %s)", ErrUnknownProvider, key, strings.Join(r.Names(), ", "))
	}
	p, err := f(cfg)
	if err != nil {
		return nil, fmt.Errorf("configure provider %q: %w", key, err)
	}
	return p, nil
}

// Names lists registered providers in sorted order.
func (r *Registry) Names() []string {
	r.mu.RLock()
	defer r.mu.RUnlock()
	names := make([]string, 0, len(r.factories))
	for n := range r.factories {
		names = append(names, n)
	}
	sort.Strings(names)
	return names
}

// Default is the process-wide registry that adapters self-register into.
var Default = New()

// Register adds a factory to the Default registry (panicking on duplicates).
func Register(name string, f Factory) { Default.MustRegister(name, f) }

// Open opens a provider from the Default registry.
func Open(name string, cfg Config) (payment.Processor, error) { return Default.Open(name, cfg) }

// Names lists the Default registry's providers.
func Names() []string { return Default.Names() }
