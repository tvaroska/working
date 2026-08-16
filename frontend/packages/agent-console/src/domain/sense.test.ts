import { describe, it, expect } from 'vitest';
import { mapTurn, isSameIssuerReject, type WireTurn } from './sense';

function bill(id: string, issuer: string): WireTurn['ledger_handed'][number] {
  return { id, doctype: 'utility-bill', issuer, disposition: 'accepted' };
}

const sameIssuerRound: WireTurn = {
  round: 2,
  ledger_handed: [
    bill('bill-powerco-clean', 'power-co'),
    bill('bill-powerco-clean-2', 'power-co'),
  ],
  reasoning: 'Two accepted bills but both from power-co...',
  satisfaction: {
    done: false,
    outstanding: ['gov-id', 'utility-bill'],
    accepted_issuers: ['power-co'],
  },
  requirements: [{ item: 'proof of address', status: 'required' }],
  done: false,
  terminal: false,
};

const distinctRound: WireTurn = {
  round: 3,
  ledger_handed: [
    bill('bill-powerco-clean', 'power-co'),
    bill('bill-powerco-clean-2', 'power-co'),
    bill('bill-aquautil-clean', 'aqua-util'),
  ],
  reasoning: 'Accepted 3 bills from 2 distinct issuers; routing done.',
  satisfaction: {
    done: true,
    outstanding: [],
    accepted_issuers: ['aqua-util', 'power-co'],
  },
  requirements: [{ item: 'proof of address', status: 'satisfied' }],
  done: true,
  terminal: true,
};

describe('agent-console sense.ts (sense-B derivation)', () => {
  it('flags two same-issuer bills as a sense-B reject (not done)', () => {
    expect(isSameIssuerReject(sameIssuerRound)).toBe(true);
    const view = mapTurn(sameIssuerRound);
    expect(view.sameIssuerReject).toBe(true);
    expect(view.done).toBe(false);
    expect(view.acceptedIssuers).toEqual(['power-co']);
    expect(view.requirements[0].status).toBe('required');
  });

  it('does not flag a distinct-issuer round; it is done', () => {
    expect(isSameIssuerReject(distinctRound)).toBe(false);
    const view = mapTurn(distinctRound);
    expect(view.sameIssuerReject).toBe(false);
    expect(view.done).toBe(true);
    expect(view.acceptedIssuers).toEqual(['aqua-util', 'power-co']);
    expect(view.requirements[0].status).toBe('satisfied');
  });

  it('maps the handed ledger to camelCase views', () => {
    const view = mapTurn(sameIssuerRound);
    expect(view.ledgerHanded).toHaveLength(2);
    expect(view.ledgerHanded[0].issuer).toBe('power-co');
    expect(view.ledgerHanded[0].disposition).toBe('accepted');
  });
});
