import { describe, it, expect } from 'vitest';
import {
  mapScreen,
  mapFulfillment,
  nextAction,
  type WireScreen,
  type WireFulfillment,
} from './outstanding';

const outstandingScreen: WireScreen = {
  status: {
    sent: [
      {
        id: 'bill-powerco-clean',
        doctype: 'utility-bill',
        issuer: 'power-co',
        disposition: 'accepted',
        message: null,
      },
    ],
    accepted: [
      {
        id: 'bill-powerco-clean',
        doctype: 'utility-bill',
        issuer: 'power-co',
        disposition: 'accepted',
        message: null,
      },
    ],
    outstanding: ['proof of address'],
    next: 'Send a bill from a different provider.',
    done: false,
  },
  intake: {
    prompt: 'Send a bill from a different provider.',
    doctype_hint: 'utility-bill',
    accepts: [
      { key: 'document', label: 'Upload a document', input: 'file' },
      { key: 'text', label: 'Or paste', input: 'text', required: false },
    ],
  },
};

const doneScreen: WireScreen = {
  status: {
    sent: [],
    accepted: [],
    outstanding: [],
    next: null,
    done: true,
  },
  intake: null,
};

describe('provider-portal outstanding.ts (snake→camel + next)', () => {
  it('maps the intake spec doctype_hint → doctypeHint and defaults required', () => {
    const view = mapScreen(outstandingScreen);
    expect(view.intake?.doctypeHint).toBe('utility-bill');
    expect(view.intake?.accepts[0].required).toBe(true); // default when absent
    expect(view.intake?.accepts[1].required).toBe(false);
    expect(view.status.next).toBe('Send a bill from a different provider.');
  });

  it('derives the next action', () => {
    expect(nextAction(mapScreen(outstandingScreen))).toContain(
      'different provider',
    );
    expect(nextAction(mapScreen(doneScreen))).toContain('All set');
  });

  it('drops intake when done', () => {
    const view = mapScreen(doneScreen);
    expect(view.intake).toBeUndefined();
    expect(view.status.done).toBe(true);
  });

  it('maps a fulfillment result to camelCase', () => {
    const wire: WireFulfillment = {
      phase: 'resubmit',
      disposition: 'rejected',
      attempts: 1,
      awaiting_resubmission: true,
      terminal: false,
      suspended: false,
    };
    const view = mapFulfillment(wire);
    expect(view.awaitingResubmission).toBe(true);
    expect(view.phase).toBe('resubmit');
    expect(view.disposition).toBe('rejected');
  });
});
