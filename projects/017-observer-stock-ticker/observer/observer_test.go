package observer

import (
	"testing"

	"github.com/abubakaromar18/software-engineering/projects/017-observer-stock-ticker/ticker"
)

func TestBoardKeepsNewestPerSymbolSorted(t *testing.T) {
	b := NewBoard()
	b.OnQuote(ticker.Quote{Symbol: "ZED", Price: 1, Seq: 1})
	b.OnQuote(ticker.Quote{Symbol: "ACME", Price: 2, Seq: 3})
	b.OnQuote(ticker.Quote{Symbol: "ACME", Price: 9, Seq: 2}) // stale

	got := b.Snapshot()
	if len(got) != 2 || got[0].Symbol != "ACME" || got[0].Price != 2 || got[1].Symbol != "ZED" {
		t.Fatalf("snapshot = %+v", got)
	}
}

func TestCrossingIsEdgeTriggered(t *testing.T) {
	var fired []bool
	c := NewCrossing("ACME", 100, func(_ ticker.Quote, rising bool) { fired = append(fired, rising) })
	for _, p := range []ticker.Cents{150, 120, 90, 80, 100, 110, 99} {
		c.OnQuote(ticker.Quote{Symbol: "ACME", Price: p})
	}
	want := []bool{false, true, false} // 120->90, 80->100, 110->99
	if len(fired) != len(want) {
		t.Fatalf("fired = %v, want %v", fired, want)
	}
	for i := range want {
		if fired[i] != want[i] {
			t.Fatalf("fired = %v, want %v", fired, want)
		}
	}
}

func TestCrossingIgnoresOtherSymbols(t *testing.T) {
	c := NewCrossing("ACME", 100, func(ticker.Quote, bool) { t.Fatal("should not fire") })
	c.OnQuote(ticker.Quote{Symbol: "ACME", Price: 150})
	c.OnQuote(ticker.Quote{Symbol: "OTHER", Price: 50})
}
