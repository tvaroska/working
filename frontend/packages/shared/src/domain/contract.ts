/**
 * Shared contract types + snake→camel mappers (lessons B3).
 *
 * The A2A/BFF wire is snake_case (it mirrors the Python contract in
 * `contract/src/contract/models.py`); TS components consume camelCase. These are
 * the *shared* wire types + mappers every surface builds on; each surface keeps
 * its own projection (`sense.ts`, `readModel.ts`, `outstanding.ts`) on top.
 *
 * Keep raw wire (snake) at the fetch/SSE boundary; map to camel here; never let
 * snake_case leak into JSX.
 */

// ---- shared vocabularies (identical on the wire and in TS) ------------------

export type Disposition = 'accepted' | 'pending' | 'rejected';
export type RequirementStatus =
  'required' | 'optional' | 'satisfied' | 'waived';

// ---- raw wire types (snake_case) -------------------------------------------

export interface WireExtractedFields {
  doctype: string;
  issuer?: string | null;
  key_fields?: Record<string, string>;
}

export interface WireExtraction {
  fields: WireExtractedFields;
  overall_confidence?: number | null;
  field_confidence?: Record<string, number>;
  legible?: boolean | null;
  flagged_fields?: string[];
}

export interface WireLedgerEntry {
  id: string;
  doctype: string;
  issuer?: string | null;
  disposition: Disposition;
  extraction?: WireExtraction | null;
  reason_code?: string | null;
  message?: string | null;
}

export interface WireRequirement {
  item: string;
  status: RequirementStatus;
  doctype_hint?: string | null;
  reason_code?: string | null;
  message?: string | null;
}

// ---- camelCase view types --------------------------------------------------

export interface ExtractedFields {
  doctype: string;
  issuer?: string;
  keyFields: Record<string, string>;
}

export interface Extraction {
  fields: ExtractedFields;
  overallConfidence?: number;
  fieldConfidence: Record<string, number>;
  legible?: boolean;
  flaggedFields: string[];
}

export interface LedgerEntry {
  id: string;
  doctype: string;
  issuer?: string;
  disposition: Disposition;
  extraction?: Extraction;
  reasonCode?: string;
  message?: string;
}

export interface Requirement {
  item: string;
  status: RequirementStatus;
  doctypeHint?: string;
  reasonCode?: string;
  message?: string;
}

// ---- mappers (snake → camel) -----------------------------------------------

/** Coerce a nullable wire field to an optional camel field (drop null). */
function opt<T>(value: T | null | undefined): T | undefined {
  return value === null || value === undefined ? undefined : value;
}

export function mapExtractedFields(wire: WireExtractedFields): ExtractedFields {
  return {
    doctype: wire.doctype,
    issuer: opt(wire.issuer),
    keyFields: wire.key_fields ?? {},
  };
}

export function mapExtraction(wire: WireExtraction): Extraction {
  return {
    fields: mapExtractedFields(wire.fields),
    overallConfidence: opt(wire.overall_confidence),
    fieldConfidence: wire.field_confidence ?? {},
    legible: opt(wire.legible),
    flaggedFields: wire.flagged_fields ?? [],
  };
}

export function mapLedgerEntry(wire: WireLedgerEntry): LedgerEntry {
  return {
    id: wire.id,
    doctype: wire.doctype,
    issuer: opt(wire.issuer),
    disposition: wire.disposition,
    extraction: wire.extraction ? mapExtraction(wire.extraction) : undefined,
    reasonCode: opt(wire.reason_code),
    message: opt(wire.message),
  };
}

export function mapLedger(wire: WireLedgerEntry[]): LedgerEntry[] {
  return wire.map(mapLedgerEntry);
}

export function mapRequirement(wire: WireRequirement): Requirement {
  return {
    item: wire.item,
    status: wire.status,
    doctypeHint: opt(wire.doctype_hint),
    reasonCode: opt(wire.reason_code),
    message: opt(wire.message),
  };
}
