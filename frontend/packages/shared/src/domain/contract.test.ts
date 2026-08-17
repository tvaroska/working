import { describe, it, expect } from 'vitest';
import {
  mapLedgerEntry,
  mapRequirement,
  mapExtraction,
  type WireLedgerEntry,
} from './contract';

describe('contract mappers (snake → camel, B3)', () => {
  it('maps a ledger entry with extraction to camelCase', () => {
    const wire: WireLedgerEntry = {
      id: 'bill-powerco-clean',
      doctype: 'utility-bill',
      issuer: 'power-co',
      disposition: 'accepted',
      extraction: {
        fields: {
          doctype: 'utility-bill',
          issuer: 'power-co',
          key_fields: { account_holder: 'Jordan Lee' },
        },
        overall_confidence: 0.95,
        field_confidence: { issuer: 0.9 },
        legible: true,
        flagged_fields: [],
      },
      reason_code: null,
      message: null,
    };

    const view = mapLedgerEntry(wire);

    expect(view.id).toBe('bill-powerco-clean');
    expect(view.issuer).toBe('power-co');
    expect(view.disposition).toBe('accepted');
    expect(view.extraction?.overallConfidence).toBe(0.95);
    expect(view.extraction?.fields.keyFields).toEqual({
      account_holder: 'Jordan Lee',
    });
    // nulls become undefined, not null
    expect(view.reasonCode).toBeUndefined();
    expect(view.message).toBeUndefined();
  });

  it('handles a ledger entry with no extraction', () => {
    const view = mapLedgerEntry({
      id: 'x',
      doctype: 'gov-id',
      disposition: 'pending',
    });
    expect(view.extraction).toBeUndefined();
    expect(view.issuer).toBeUndefined();
  });

  it('maps requirement doctype_hint → doctypeHint', () => {
    const req = mapRequirement({
      item: 'proof of address',
      status: 'required',
      doctype_hint: 'utility-bill',
      message: 'Send a bill from a different provider.',
    });
    expect(req.doctypeHint).toBe('utility-bill');
    expect(req.status).toBe('required');
    expect(req.message).toContain('different provider');
  });

  it('defaults missing collections to empty', () => {
    const ext = mapExtraction({
      fields: { doctype: 'utility-bill' },
    });
    expect(ext.fields.keyFields).toEqual({});
    expect(ext.fieldConfidence).toEqual({});
    expect(ext.flaggedFields).toEqual([]);
  });
});
