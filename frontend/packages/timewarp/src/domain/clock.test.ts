import { describe, it, expect } from 'vitest';
import { mapTimewarp, type WireTimewarpState } from './clock';

const wire: WireTimewarpState = {
  now: 5,
  sla: { deadline: 3, cadence: 2, max_nudges: 2 },
  timers: [
    {
      id: 'exchange-two-bills-nudge-1',
      context_id: 'exchange-two-bills',
      fire_at: 3,
      kind: 'nudge',
      sequence: 1,
      fired: true,
    },
  ],
  followup: { state: 'overdue', nudges_fired: 1, escalated: false },
};

describe('timewarp clock.ts (snake→camel)', () => {
  it('maps sla + timers + followup to camelCase', () => {
    const view = mapTimewarp(wire);
    expect(view.sla.maxNudges).toBe(2);
    expect(view.timers[0].contextId).toBe('exchange-two-bills');
    expect(view.timers[0].fireAt).toBe(3);
    expect(view.timers[0].fired).toBe(true);
    expect(view.followup.nudgesFired).toBe(1);
    expect(view.followup.escalated).toBe(false);
  });
});
