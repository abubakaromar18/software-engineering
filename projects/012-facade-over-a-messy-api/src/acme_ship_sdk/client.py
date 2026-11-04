# ruff: noqa: N802  -- PascalCase method names are part of the vendor's API.
"""In-memory implementation of the vendor client.

Behaviour is deterministic: rates are derived from billable weight and the
distance between ZIP-code zones, and tracking numbers come from a counter.
Two knobs make it misbehave on purpose so the facade's resilience can be
tested: ``flaky_every`` makes every Nth request return ``503`` and
``session_ttl_calls`` expires the session after that many calls.
"""

from __future__ import annotations

import base64
import itertools
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Return codes, as documented in the (imaginary) vendor PDF.
RC_OK = 0
RC_BAD_REQUEST = 400
RC_UNAUTHORIZED = 401
RC_NOT_FOUND = 404
RC_CONFLICT = 409
RC_SESSION_EXPIRED = 440
RC_BUSY = 503

_VALID_ACCOUNTS = {"ACME-TEST-001": "sandbox-key"}

# service code -> (base cents, cents per lb, cents per zone, transit days)
_SERVICES = {
    "GND": (899, 85, 60, 5),
    "2DA": (1899, 160, 120, 2),
    "NDA": (3499, 260, 210, 1),
}

# Tracking status codes, in the order a parcel moves through them.
_PROGRESSION = ["LC", "PU", "IT", "OD", "DL"]
# Where the early scans happen; later scans happen in the destination city.
_SCAN_SITES = {"PU": "ORIGIN FACILITY", "IT": "REGIONAL HUB"}


@dataclass
class _Label:
    tracking: str
    service: str
    charge_cents: int
    destination_city: str
    created: datetime
    events: list[tuple[datetime, str, str]] = field(default_factory=list)
    voided: bool = False


class AcmeShipClient:
    """The vendor's client object. One instance holds one session."""

    def __init__(
        self,
        *,
        flaky_every: int = 0,
        session_ttl_calls: int = 0,
        clock_start: datetime = datetime(2026, 1, 5, 9, 0, 0),
    ) -> None:
        self._flaky_every = flaky_every
        self._session_ttl = session_ttl_calls
        self._clock = clock_start
        self._session: str | None = None
        self._calls_in_session = 0
        self._request_count = 0
        self._labels: dict[str, _Label] = {}
        self._serial = itertools.count(1)
        self.connect_count = 0  # exposed so tests can observe reconnects

    # ------------------------------------------------------------- session
    def Connect(self, acct: str, key: str, env: str = "PROD") -> int:
        self.connect_count += 1
        if _VALID_ACCOUNTS.get(acct) != key or env not in ("PROD", "SANDBOX"):
            self._session = None
            return RC_UNAUTHORIZED
        self._session = f"SESS-{acct}-{self.connect_count}"
        self._calls_in_session = 0
        return RC_OK

    # ------------------------------------------------------------- requests
    def GetRates(self, payload: dict) -> dict:
        if (err := self._gate()) is not None:
            return err
        problem = _check_address(payload.get("frm")) or _check_address(payload.get("to"))
        if problem:
            return {"rc": RC_BAD_REQUEST, "msg": problem}
        pkg = _parse_pkg(payload.get("pkg", ""))
        if pkg is None:
            return {"rc": RC_BAD_REQUEST, "msg": "PKG STRING MALFORMED"}
        zones = _zones(payload["frm"]["zp"], payload["to"]["zp"])
        rates = []
        for svc, (base, per_lb, per_zone, days) in _SERVICES.items():
            amount = base + per_lb * _billable_lbs(pkg) + per_zone * zones
            rates.append({"svc": svc, "amt": str(amount), "eta": str(days)})
        return {"rc": RC_OK, "rates": rates}

    def CreateLabel(self, payload: dict) -> dict:
        rates = self.GetRates(payload)
        if rates["rc"] != RC_OK:
            return rates
        match = [r for r in rates["rates"] if r["svc"] == payload.get("svc")]
        if not match:
            return {"rc": RC_BAD_REQUEST, "msg": f"UNKNOWN SVC {payload.get('svc')!r}"}
        tracking = f"1ZACME{next(self._serial):08d}"
        label = _Label(
            tracking=tracking,
            service=match[0]["svc"],
            charge_cents=int(match[0]["amt"]),
            destination_city=f"{payload['to']['cty'].upper()} {payload['to']['st'].upper()}",
            created=self._clock,
        )
        label.events.append((self._clock, "LC", "LABEL CREATED"))
        self._labels[tracking] = label
        pdf_ish = base64.b64encode(f"%PDF-SIM {tracking}".encode()).decode()
        return {"rc": RC_OK, "trk": tracking, "lbl": pdf_ish, "chg": match[0]["amt"]}

    def Track(self, trk: str) -> str:
        """Returns ``'RC=0~YYYYMMDD HHMMSS|CODE|DESC;...'`` -- yes, really."""
        if (err := self._gate()) is not None:
            return f"RC={err['rc']}~{err['msg']}"
        label = self._labels.get(trk)
        if label is None:
            return f"RC={RC_NOT_FOUND}~NO SUCH TRK"
        lines = [f"{ts:%Y%m%d %H%M%S}|{code}|{desc}" for ts, code, desc in label.events]
        return f"RC={RC_OK}~" + ";".join(lines)

    def VoidLabel(self, trk: str) -> dict:
        if (err := self._gate()) is not None:
            return err
        label = self._labels.get(trk)
        if label is None:
            return {"rc": RC_NOT_FOUND, "msg": "NO SUCH TRK"}
        if label.voided:
            return {"rc": RC_CONFLICT, "msg": "ALREADY VOID"}
        if label.events[-1][1] != "LC":
            return {"rc": RC_CONFLICT, "msg": "PKG ALREADY IN NETWORK"}
        label.voided = True
        label.events.append((self._clock, "VD", "LABEL VOIDED"))
        return {"rc": RC_OK}

    # ----------------------------------------------------- simulator hooks
    def _simulate_scan(self, trk: str, hours: int = 6) -> None:
        """Advance a parcel one step through the network (test/demo hook)."""
        label = self._labels[trk]
        last_code = label.events[-1][1]
        if label.voided or last_code == "DL":
            return
        step = _PROGRESSION.index(last_code) + 1
        self._clock += timedelta(hours=hours)
        code = _PROGRESSION[step]
        where = _SCAN_SITES.get(code, label.destination_city)
        label.events.append((self._clock, code, f"SCANNED AT {where}"))

    # ------------------------------------------------------------- helpers
    def _gate(self) -> dict | None:
        """Session and availability checks shared by every request."""
        self._request_count += 1
        if self._session is None:
            return {"rc": RC_UNAUTHORIZED, "msg": "NOT CONNECTED"}
        if self._flaky_every and self._request_count % self._flaky_every == 0:
            return {"rc": RC_BUSY, "msg": "SERVER BUSY TRY LATER"}
        self._calls_in_session += 1
        if self._session_ttl and self._calls_in_session > self._session_ttl:
            self._session = None
            return {"rc": RC_SESSION_EXPIRED, "msg": "SESSION EXPIRED"}
        return None


def _check_address(addr: dict | None) -> str | None:
    if not isinstance(addr, dict):
        return "ADDR MISSING"
    for key in ("nm", "a1", "cty", "st", "zp", "ctry"):
        if not addr.get(key):
            return f"ADDR FIELD {key.upper()} REQUIRED"
    if addr["ctry"] != "US":
        return "DOMESTIC ONLY"
    if len(addr["zp"]) != 5 or not addr["zp"].isdigit():
        return "BAD ZP"
    return None


def _parse_pkg(spec: str) -> dict[str, float] | None:
    try:
        parts = dict(item.split("=", 1) for item in spec.split(";"))
        values = {k: float(parts[k]) for k in ("WT", "L", "W", "H")}
    except (KeyError, ValueError):
        return None
    return values if all(v > 0 for v in values.values()) else None


def _billable_lbs(pkg: dict[str, float]) -> int:
    """Carriers bill the greater of actual and dimensional weight (DIM 139)."""
    dim_weight = pkg["L"] * pkg["W"] * pkg["H"] / 139
    return max(1, math.ceil(max(pkg["WT"], dim_weight)))


def _zones(from_zip: str, to_zip: str) -> int:
    return abs(int(from_zip[0]) - int(to_zip[0])) + 1
