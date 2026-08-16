/**
 * ops-dashboard domain layer (lessons B3): project the raw ops read-model
 * snapshot (snake_case) into a camelCase model grouped **by actionable state,
 * per exchange** (not per raw task). The BFF sends raw ledger/queue snapshots;
 * the grouping lives here.
 */

import {
  mapLedger,
  type LedgerEntry,
  type WireLedgerEntry,
} from '@bridge/shared';

export type FollowupState = 'on_track' | 'overdue' | 'escalated';

export interface WireFollowup {
  state: FollowupState;
  nudges_fired: number;
  escalated: boolean;
}

export interface WireExchange {
  id: string;
  party: string;
  ledger: WireLedgerEntry[];
  outstanding: string[];
  terminal: boolean;
  followup: WireFollowup;
}

export interface WireHitlItem {
  exchange_id: string;
  doc_id: string;
  doctype: string;
  issuer?: string | null;
}

export interface WireEscalationItem {
  exchange_id: string;
  state: FollowupState;
  nudges_fired: number;
  escalated: boolean;
}

export interface WireOpsSnapshot {
  now: number;
  exchanges: WireExchange[];
  hitl_queue: WireHitlItem[];
  escalation_queue: WireEscalationItem[];
}

export interface FollowupView {
  state: FollowupState;
  nudgesFired: number;
  escalated: boolean;
}

export interface ExchangeView {
  id: string;
  party: string;
  ledger: LedgerEntry[];
  outstanding: string[];
  terminal: boolean;
  followup: FollowupView;
}

export interface HitlItemView {
  exchangeId: string;
  docId: string;
  doctype: string;
  issuer?: string;
}

export interface EscalationItemView {
  exchangeId: string;
  state: FollowupState;
  nudgesFired: number;
  escalated: boolean;
}

export interface ReadModel {
  now: number;
  exchanges: ExchangeView[];
  hitlQueue: HitlItemView[];
  escalationQueue: EscalationItemView[];
  /** Non-terminal, non-escalated exchanges still being chased. */
  inFlight: ExchangeView[];
  /** Exchanges whose SLA ladder has escalated. */
  escalated: ExchangeView[];
  /** Terminal (all-accepted) exchanges. */
  done: ExchangeView[];
}

function mapFollowup(wire: WireFollowup): FollowupView {
  return {
    state: wire.state,
    nudgesFired: wire.nudges_fired,
    escalated: wire.escalated,
  };
}

function mapExchange(wire: WireExchange): ExchangeView {
  return {
    id: wire.id,
    party: wire.party,
    ledger: mapLedger(wire.ledger),
    outstanding: wire.outstanding,
    terminal: wire.terminal,
    followup: mapFollowup(wire.followup),
  };
}

export function projectReadModel(wire: WireOpsSnapshot): ReadModel {
  const exchanges = wire.exchanges.map(mapExchange);
  return {
    now: wire.now,
    exchanges,
    hitlQueue: wire.hitl_queue.map((h) => ({
      exchangeId: h.exchange_id,
      docId: h.doc_id,
      doctype: h.doctype,
      issuer: h.issuer ?? undefined,
    })),
    escalationQueue: wire.escalation_queue.map((e) => ({
      exchangeId: e.exchange_id,
      state: e.state,
      nudgesFired: e.nudges_fired,
      escalated: e.escalated,
    })),
    inFlight: exchanges.filter(
      (e) => !e.terminal && e.followup.state !== 'escalated',
    ),
    escalated: exchanges.filter((e) => e.followup.state === 'escalated'),
    done: exchanges.filter((e) => e.terminal),
  };
}
