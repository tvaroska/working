/**
 * agent-console domain layer (lessons B3): map the raw console turn frames
 * (snake_case) to a camelCase view and derive the **sense-B** display beat.
 *
 * Sense B is the console's whole point: the agent (not the Bridge) rejects two
 * accepted utility bills from the *same* canonical issuer and asks for one more
 * from a distinct provider. Completeness is NOT recomputed here — the wire
 * `satisfaction.done` is the authoritative `is_satisfied` verdict; this layer
 * only *reads* it and derives the presentation flag.
 */

import {
  mapLedger,
  mapRequirement,
  type LedgerEntry,
  type Requirement,
  type RequirementStatus,
  type WireLedgerEntry,
} from '@bridge/shared';

const UTILITY_BILL = 'utility-bill';

export interface WireSatisfaction {
  done: boolean;
  outstanding: string[];
  accepted_issuers: string[];
}

export interface WireRequirementItem {
  item: string;
  status: RequirementStatus;
}

export interface WireTurn {
  round: number;
  ledger_handed: WireLedgerEntry[];
  reasoning: string;
  satisfaction: WireSatisfaction;
  requirements: WireRequirementItem[];
  done: boolean;
  terminal: boolean;
}

export interface TurnView {
  round: number;
  ledgerHanded: LedgerEntry[];
  reasoning: string;
  done: boolean;
  outstanding: string[];
  acceptedIssuers: string[];
  requirements: Requirement[];
  terminal: boolean;
  /** True when the agent is rejecting a two-same-issuer bill set (sense B). */
  sameIssuerReject: boolean;
}

/**
 * The sense-B beat: ≥2 accepted utility bills but only one distinct canonical
 * issuer, and the gate is not done → the agent asks for one more from a
 * different provider.
 */
export function isSameIssuerReject(wire: WireTurn): boolean {
  const acceptedBills = wire.ledger_handed.filter(
    (e) => e.doctype === UTILITY_BILL && e.disposition === 'accepted',
  );
  return (
    !wire.satisfaction.done &&
    acceptedBills.length >= 2 &&
    wire.satisfaction.accepted_issuers.length === 1
  );
}

export function mapTurn(wire: WireTurn): TurnView {
  return {
    round: wire.round,
    ledgerHanded: mapLedger(wire.ledger_handed),
    reasoning: wire.reasoning,
    done: wire.satisfaction.done,
    outstanding: wire.satisfaction.outstanding,
    acceptedIssuers: wire.satisfaction.accepted_issuers,
    requirements: wire.requirements.map((r) => mapRequirement(r)),
    terminal: wire.terminal,
    sameIssuerReject: isSameIssuerReject(wire),
  };
}
