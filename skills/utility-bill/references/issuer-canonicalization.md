# Issuer Canonicalization

**Rule:** Strip only corporate suffixes (`Ltd`, `Inc`, `LLC`, `GmbH`, and similar); **"Co." is NOT a suffix** — it's part of the company name.

**Process:**
1. Strip recognized corporate suffixes: `Ltd`, `Limited`, `Inc`, `Incorporated`, `LLC`, `GmbH`, `S.A.`, `PLC`, etc.
2. Lowercase the result
3. Replace spaces and punctuation with hyphens
4. Collapse multiple consecutive hyphens to one

**Examples:**
- `"Power Co."` → `power-co` (Co. is NOT stripped)
- `"PowerCo Ltd"` → `powerco` (Ltd IS stripped)
- `"Water Services Inc"` → `water-services`
- `"Gas & Electric LLC"` → `gas-electric`

**Rationale:** "Co." often appears as part of the brand name (e.g., "Power Co.", "Electric Co."), not as a legal suffix. Stripping it would lose essential identity information. Only formal corporate suffixes that are consistently added for legal registration should be normalized away.

**Cross-reference:** `docs/lessons-learned.md` section A4.
