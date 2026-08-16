import { describe, it, expect } from 'vitest';
import { projectReadModel, type WireOpsSnapshot } from './readModel';

const snapshot: WireOpsSnapshot = {
  now: 7,
  exchanges: [
    {
      id: 'exchange-two-bills',
      party: 'jordan-lee',
      ledger: [
        {
          id: 'bill-powerco-clean',
          doctype: 'utility-bill',
          issuer: 'power-co',
          disposition: 'accepted',
        },
      ],
      outstanding: ['utility-bill'],
      terminal: false,
      followup: { state: 'escalated', nudges_fired: 2, escalated: true },
    },
    {
      id: 'exchange-hitl',
      party: 'jordan-lee',
      ledger: [
        {
          id: 'gov-id-expired',
          doctype: 'gov-id',
          disposition: 'pending',
        },
      ],
      outstanding: ['gov-id'],
      terminal: false,
      followup: { state: 'on_track', nudges_fired: 0, escalated: false },
    },
  ],
  hitl_queue: [
    {
      exchange_id: 'exchange-hitl',
      doc_id: 'gov-id-expired',
      doctype: 'gov-id',
      issuer: null,
    },
  ],
  escalation_queue: [
    {
      exchange_id: 'exchange-two-bills',
      state: 'escalated',
      nudges_fired: 2,
      escalated: true,
    },
  ],
};

describe('ops-dashboard readModel.ts (projection, B3)', () => {
  it('groups exchanges by actionable state, per exchange', () => {
    const model = projectReadModel(snapshot);
    expect(model.now).toBe(7);
    expect(model.escalated.map((e) => e.id)).toEqual(['exchange-two-bills']);
    expect(model.inFlight.map((e) => e.id)).toEqual(['exchange-hitl']);
    expect(model.done).toHaveLength(0);
  });

  it('maps HITL queue to camelCase (issuer null → undefined)', () => {
    const model = projectReadModel(snapshot);
    expect(model.hitlQueue).toHaveLength(1);
    expect(model.hitlQueue[0].docId).toBe('gov-id-expired');
    expect(model.hitlQueue[0].issuer).toBeUndefined();
  });

  it('maps the escalation queue with nudgesFired', () => {
    const model = projectReadModel(snapshot);
    expect(model.escalationQueue[0].exchangeId).toBe('exchange-two-bills');
    expect(model.escalationQueue[0].nudgesFired).toBe(2);
    expect(model.escalationQueue[0].escalated).toBe(true);
  });

  it('maps each exchange ledger to camelCase entries', () => {
    const model = projectReadModel(snapshot);
    const escalatedExchange = model.escalated[0];
    expect(escalatedExchange.ledger[0].issuer).toBe('power-co');
    expect(escalatedExchange.followup.nudgesFired).toBe(2);
  });
});
