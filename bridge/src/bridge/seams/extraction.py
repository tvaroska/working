"""Extraction seam: capability axis (NOT local↔gcp).

Extraction is a capability axis (ADR-0005): engines are fixture|gemini|docai,
selected by config + per-doctype capability, deployed either way. The local build
uses the fixture engine (deterministic); Gemini is Sprint 2; DocAI is Phase 4.

CAVEAT: @runtime_checkable Protocols check method presence only, not signatures.
This is the desired behavior for M1.1 conformance smoke tests — real behavior and
signature validation are pinned by the shared suite in M1.2+. Keep every Protocol
method-only (no data attributes) or isinstance will raise/misbehave.

NOTE: This seam does NOT follow the local↔gcp axis. `local` maps to the fixture
engine; there is no `gcp` param for extraction (Gemini opts in via BRIDGE_TEST_GEMINI,
out of scope for M1.1). See wiki/bridge-seams.md §"Axis nuance" and lessons-learned.md
C3 for the env-var selection contract (BRIDGE_EXTRACTION_ENGINE).

The fixture engine returns the existing contract.Extraction type. ADR-0004
SignalProvider (four-signal disposition model) is downstream (M1.6) and reads
signals engine-agnostically.
"""

from typing import Protocol, runtime_checkable

from contract import Extraction

__all__ = ["ExtractionSeam"]


@runtime_checkable
class ExtractionSeam(Protocol):
    """Seam for document extraction (capability axis: fixture|gemini|docai).

    Local adapter: FixtureExtractionEngine (bridge.adapters.local, deterministic)
    Capability adapters: GeminiExtractionEngine (Sprint 2), DocAIEngine (Phase 4)

    This is NOT a local↔gcp seam — engines are selected by config + per-doctype
    capability (ADR-0005 resolution order is M1.7). Disposition reads signals
    engine-agnostically (ADR-0004 SignalProvider is M1.6).

    Note: The concrete document and doctype_skill types are defined by M1.7;
    signatures use `object` here as placeholders. The return type is the existing
    contract.Extraction.
    """

    async def extract(self, document: object, doctype_skill: object) -> Extraction:
        """Extract structured data from a document.

        Returns the existing contract.Extraction type. ADR-0004 SignalProvider
        (four-signal disposition model) is M1.6 and reads signals engine-agnostically.

        # M1.7 implements the fixture engine + engine resolution.
        # M1.6 implements the SignalProvider (ADR-0004).
        """
        ...
