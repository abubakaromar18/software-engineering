// Command paydemo is the composition root: it enables the bundled adapters,
// reads configuration, opens providers by name from the registry and runs a
// checkout. It is the only place that knows which plugins exist.
//
//	paydemo -list
//	paydemo -providers swiftpay,ledgerly -amount 1999 -currency USD -source tok_outage
//
// Provider settings come from environment variables named
// <PROVIDER>_<KEY>, e.g. SWIFTPAY_API_KEY or LEDGERLY_MERCHANT_ID. When a key
// is unset, a sandbox default is used so the demo runs out of the box.
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"log/slog"
	"os"
	"strings"
	"time"

	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/checkout"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/payment"
	_ "github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/plugins/all"
	"github.com/abubakaromar18/software-engineering/projects/009-plugin-system-with-adapters/registry"
)

// sandboxDefaults are fake, sandbox-only credentials for the simulated
// vendors. They are not secrets and grant access to nothing real.
var sandboxDefaults = map[string]registry.Config{
	"swiftpay":  {"api_key": "sp_test_demo"},
	"ledgerly":  {"merchant_id": "M-DEMO", "secret": "sandbox"},
	"quickcoin": {"api_token": "qc_sandbox", "poll_interval": "20ms"},
}

func main() {
	if err := run(os.Args[1:], os.Stdout, os.Getenv); err != nil {
		fmt.Fprintln(os.Stderr, "paydemo:", err)
		os.Exit(exitCode(err))
	}
}

// exitCode distinguishes declines (2) from other failures (1) for scripts.
func exitCode(err error) int {
	if errors.Is(err, payment.ErrDeclined) {
		return 2
	}
	return 1
}

// configFor merges sandbox defaults with <NAME>_<KEY> environment overrides.
func configFor(name string, getenv func(string) string) registry.Config {
	cfg := registry.Config{}
	for k, v := range sandboxDefaults[name] {
		cfg[k] = v
	}
	for _, k := range []string{"api_key", "merchant_id", "secret", "api_token", "poll_interval", "settle_timeout", "polls_to_settle"} {
		if v := getenv(strings.ToUpper(name + "_" + k)); v != "" {
			cfg[k] = v
		}
	}
	return cfg
}

func run(args []string, out io.Writer, getenv func(string) string) error {
	fs := flag.NewFlagSet("paydemo", flag.ContinueOnError)
	fs.SetOutput(out)
	var (
		list      = fs.Bool("list", false, "list registered providers and exit")
		providers = fs.String("providers", "swiftpay", "comma-separated provider chain: primary first, then fallbacks")
		amount    = fs.Int64("amount", 1999, "amount in minor units (e.g. cents)")
		currency  = fs.String("currency", "USD", "ISO currency code")
		source    = fs.String("source", "tok_visa", "payment source token")
		orderID   = fs.String("order", "", "order id (default: generated)")
		refund    = fs.Bool("refund", false, "fully refund the charge after it succeeds")
		timeout   = fs.Duration("timeout", 10*time.Second, "overall deadline")
		verbose   = fs.Bool("v", false, "log each attempt")
	)
	if err := fs.Parse(args); err != nil {
		return err
	}

	if *list {
		for _, n := range registry.Names() {
			fmt.Fprintln(out, n)
		}
		return nil
	}

	money, err := payment.NewMoney(*amount, *currency)
	if err != nil {
		return err
	}
	var chain []payment.Processor
	for _, name := range strings.Split(*providers, ",") {
		name = strings.TrimSpace(name)
		p, err := registry.Open(name, configFor(name, getenv))
		if err != nil {
			return err
		}
		chain = append(chain, p)
	}

	var logger *slog.Logger
	if *verbose {
		logger = slog.New(slog.NewTextHandler(out, &slog.HandlerOptions{Level: slog.LevelInfo}))
	}
	svc, err := checkout.New(logger, chain...)
	if err != nil {
		return err
	}
	if *orderID == "" {
		*orderID = fmt.Sprintf("demo-%d", time.Now().UnixNano())
	}

	ctx, cancel := context.WithTimeout(context.Background(), *timeout)
	defer cancel()
	res, err := svc.Pay(ctx, checkout.Order{ID: *orderID, Amount: money, Source: *source})
	for i, a := range res.Attempts {
		status := "ok"
		if a.Err != nil {
			status = a.Err.Error()
		}
		fmt.Fprintf(out, "attempt %d  %-10s %s\n", i+1, a.Provider, status)
	}
	if err != nil {
		return err
	}
	r := res.Receipt
	fmt.Fprintf(out, "charged    %s via %s (id %s)\n", r.Amount, r.Provider, r.ID)

	if *refund {
		for _, p := range chain {
			if p.Name() != r.Provider {
				continue
			}
			rr, err := p.Refund(ctx, payment.RefundRequest{ChargeID: r.ID, Amount: r.Amount})
			if err != nil {
				return err
			}
			fmt.Fprintf(out, "refunded   %s via %s (id %s)\n", rr.Amount, rr.Provider, rr.ID)
			break
		}
	}
	return nil
}
