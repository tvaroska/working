/**
 * provider-portal domain layer (lessons B3): map the declarative A2UI screen
 * (snake_case wire from `build_screen`) to a camelCase view, and map the
 * Path-B fulfillment result. Content-not-pixels: the wire describes *what* to
 * show; the React portal decides *how*.
 */

import type { Disposition } from '@bridge/shared';

// ---- wire (snake_case) -----------------------------------------------------

export interface WireDocStatus {
  id: string;
  doctype: string;
  issuer?: string | null;
  disposition: Disposition;
  message?: string | null;
}

export interface WirePartyStatusView {
  sent: WireDocStatus[];
  accepted: WireDocStatus[];
  outstanding: string[];
  next: string | null;
  done: boolean;
}

export interface WireResponseField {
  key: string;
  label: string;
  input: 'file' | 'text' | 'form';
  required?: boolean;
}

export interface WireIntakeSpec {
  prompt: string;
  doctype_hint?: string | null;
  accepts: WireResponseField[];
}

export interface WireScreen {
  status: WirePartyStatusView;
  intake: WireIntakeSpec | null;
}

export interface WireFulfillment {
  phase: string;
  disposition: Disposition | null;
  attempts: number;
  awaiting_resubmission: boolean;
  terminal: boolean;
  suspended: boolean;
}

// ---- camelCase views -------------------------------------------------------

export interface DocStatusView {
  id: string;
  doctype: string;
  issuer?: string;
  disposition: Disposition;
  message?: string;
}

export interface PartyStatusView {
  sent: DocStatusView[];
  accepted: DocStatusView[];
  outstanding: string[];
  next?: string;
  done: boolean;
}

export interface ResponseField {
  key: string;
  label: string;
  input: 'file' | 'text' | 'form';
  required: boolean;
}

export interface IntakeSpec {
  prompt: string;
  doctypeHint?: string;
  accepts: ResponseField[];
}

export interface ScreenView {
  status: PartyStatusView;
  intake?: IntakeSpec;
}

export interface FulfillmentView {
  phase: string;
  disposition?: Disposition;
  attempts: number;
  awaitingResubmission: boolean;
  terminal: boolean;
  suspended: boolean;
}

function mapDoc(wire: WireDocStatus): DocStatusView {
  return {
    id: wire.id,
    doctype: wire.doctype,
    issuer: wire.issuer ?? undefined,
    disposition: wire.disposition,
    message: wire.message ?? undefined,
  };
}

export function mapScreen(wire: WireScreen): ScreenView {
  return {
    status: {
      sent: wire.status.sent.map(mapDoc),
      accepted: wire.status.accepted.map(mapDoc),
      outstanding: wire.status.outstanding,
      next: wire.status.next ?? undefined,
      done: wire.status.done,
    },
    intake: wire.intake
      ? {
          prompt: wire.intake.prompt,
          doctypeHint: wire.intake.doctype_hint ?? undefined,
          accepts: wire.intake.accepts.map((a) => ({
            key: a.key,
            label: a.label,
            input: a.input,
            required: a.required ?? true,
          })),
        }
      : undefined,
  };
}

export function mapFulfillment(wire: WireFulfillment): FulfillmentView {
  return {
    phase: wire.phase,
    disposition: wire.disposition ?? undefined,
    attempts: wire.attempts,
    awaitingResubmission: wire.awaiting_resubmission,
    terminal: wire.terminal,
    suspended: wire.suspended,
  };
}

/** Human summary of what the party should do next (or that they are done). */
export function nextAction(screen: ScreenView): string {
  if (screen.status.done) return 'All set — nothing outstanding.';
  return screen.status.next ?? 'Upload the outstanding document.';
}
