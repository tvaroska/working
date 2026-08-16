import { test, expect } from '@playwright/test';
import { fulfillSse, fulfillJson, type SseFrame } from './sse';

const RULE =
  'one accepted gov-id OR two accepted utility-bills from distinct issuers';

function bill(id: string, issuer: string) {
  return { id, doctype: 'utility-bill', issuer, disposition: 'accepted' };
}

const consoleFrames: SseFrame[] = [
  [
    'snapshot',
    {
      scenario: 'sense-b',
      party: 'jordan-lee',
      skill: 'address-proof',
      rule: RULE,
    },
  ],
  [
    'turn',
    {
      round: 1,
      ledger_handed: [bill('bill-powerco-clean', 'power-co')],
      reasoning:
        'One accepted bill from power-co; need a second distinct issuer.',
      satisfaction: {
        done: false,
        outstanding: ['gov-id', 'utility-bill'],
        accepted_issuers: ['power-co'],
      },
      requirements: [{ item: 'proof of address', status: 'required' }],
      done: false,
      terminal: false,
    },
  ],
  [
    'turn',
    {
      round: 2,
      ledger_handed: [
        bill('bill-powerco-clean', 'power-co'),
        bill('bill-powerco-clean-2', 'power-co'),
      ],
      reasoning:
        'Two accepted bills but both from power-co — rejecting the same-issuer set.',
      satisfaction: {
        done: false,
        outstanding: ['gov-id', 'utility-bill'],
        accepted_issuers: ['power-co'],
      },
      requirements: [{ item: 'proof of address', status: 'required' }],
      done: false,
      terminal: false,
    },
  ],
  [
    'turn',
    {
      round: 3,
      ledger_handed: [
        bill('bill-powerco-clean', 'power-co'),
        bill('bill-powerco-clean-2', 'power-co'),
        bill('bill-aquautil-clean', 'aqua-util'),
      ],
      reasoning: 'Accepted bills from 2 distinct issuers; routing done.',
      satisfaction: {
        done: true,
        outstanding: [],
        accepted_issuers: ['aqua-util', 'power-co'],
      },
      requirements: [{ item: 'proof of address', status: 'satisfied' }],
      done: true,
      terminal: true,
    },
  ],
];

const chasingExchange = (escalated: boolean) => ({
  id: 'exchange-two-bills',
  party: 'jordan-lee',
  ledger: [bill('bill-powerco-clean', 'power-co')],
  outstanding: ['utility-bill'],
  terminal: false,
  followup: {
    state: escalated ? 'escalated' : 'on_track',
    nudges_fired: escalated ? 2 : 0,
    escalated,
  },
});

const opsSnapshot = (escalated: boolean) => ({
  now: escalated ? 7 : 0,
  exchanges: [chasingExchange(escalated)],
  hitl_queue: [],
  escalation_queue: escalated
    ? [
        {
          exchange_id: 'exchange-two-bills',
          state: 'escalated',
          nudges_fired: 2,
          escalated: true,
        },
      ]
    : [],
});

const portalScreen = {
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
      {
        key: 'document',
        label: 'Upload a document',
        input: 'file',
        required: true,
      },
    ],
  },
};

const timewarpState = (escalated: boolean) => ({
  now: escalated ? 7 : 0,
  sla: { deadline: 3, cadence: 2, max_nudges: 2 },
  timers: [
    {
      id: 'exchange-two-bills-nudge-1',
      context_id: 'exchange-two-bills',
      fire_at: 3,
      kind: 'nudge',
      sequence: 1,
      fired: escalated,
    },
    {
      id: 'exchange-two-bills-escalation',
      context_id: 'exchange-two-bills',
      fire_at: 7,
      kind: 'escalation',
      sequence: 0,
      fired: escalated,
    },
  ],
  followup: {
    state: escalated ? 'escalated' : 'on_track',
    nudges_fired: escalated ? 2 : 0,
    escalated,
  },
});

test('Split-Screen Theater drives the address arc: sense-B reject → time-warp → escalated', async ({
  page,
}) => {
  // The clock advance flips the whole world from on-track to escalated (B1 stubs).
  let advanced = false;

  await page.route('**/console/stream*', (route) =>
    fulfillSse(route, consoleFrames),
  );
  await page.route('**/ops/stream*', (route) =>
    fulfillSse(route, [['snapshot', opsSnapshot(advanced)]]),
  );
  await page.route('**/portal/screen*', (route) =>
    fulfillJson(route, portalScreen),
  );
  await page.route('**/timewarp/state', (route) =>
    fulfillJson(route, timewarpState(advanced)),
  );
  await page.route('**/timewarp/advance', async (route) => {
    advanced = true;
    await fulfillJson(route, {
      fired: ['exchange-two-bills-escalation'],
      state: timewarpState(true),
    });
  });

  await page.goto('/theater');

  // Both zones + the Gateway boundary are drawn.
  await expect(page.getByTestId('external-zone')).toBeVisible();
  await expect(page.getByTestId('internal-zone')).toBeVisible();
  await expect(page.getByTestId('gateway-boundary')).toBeAttached();

  // Sense B is visible on the console (reject two same-issuer bills).
  await expect(
    page.getByText(/two accepted bills from the same issuer/i),
  ).toBeVisible();

  // No escalation yet on ops.
  await expect(page.getByText('No escalations.')).toBeVisible();

  // Time-warp: advance the clock past the SLA deadline.
  await page.getByRole('button', { name: 'Advance' }).click();

  // Reload so the ops stream re-fetches the now-escalated snapshot.
  await page.reload();

  // Escalation surfaces on the ops dashboard.
  await expect(page.getByText(/exchange-two-bills — escalated/i)).toBeVisible();
});
