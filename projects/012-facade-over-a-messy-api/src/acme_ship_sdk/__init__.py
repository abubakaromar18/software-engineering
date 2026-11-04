"""A simulated legacy shipping SDK ("AcmeShip SDK v2.3").

This package stands in for a third-party vendor library that we do not own
and cannot change. Its awkwardness is deliberate and is the reason the facade
exists:

* PascalCase methods and a stateful session that must be opened with
  ``Connect`` and silently expires after a number of calls.
* Status codes (``rc``) instead of exceptions, with a transient ``503``.
* Imperial units, packed into a ``"WT=..;L=..;W=..;H=.."`` string.
* Money as strings of cents, ETAs as strings of days.
* Cryptic abbreviated dictionary keys (``nm``, ``a1``, ``cty``, ``zp``...).
* Tracking history returned as one pipe-and-semicolon delimited string.

Nothing outside ``shipping_facade.gateway`` should import from here.
"""

from acme_ship_sdk.client import AcmeShipClient

__all__ = ["AcmeShipClient"]
__version__ = "2.3.0"
