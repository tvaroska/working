import { Chip } from '@mui/material';
import type { Disposition, RequirementStatus } from './domain/contract';

type ChipColor =
  'default' | 'success' | 'warning' | 'error' | 'info' | 'primary';

const DISPOSITION_COLOR: Record<Disposition, ChipColor> = {
  accepted: 'success',
  pending: 'warning',
  rejected: 'error',
};

/** A colored chip for a document disposition (accepted/pending/rejected). */
export function DispositionBadge({
  disposition,
}: {
  disposition: Disposition;
}) {
  return (
    <Chip
      size="small"
      label={disposition}
      color={DISPOSITION_COLOR[disposition]}
    />
  );
}

const REQUIREMENT_COLOR: Record<RequirementStatus, ChipColor> = {
  required: 'warning',
  optional: 'info',
  satisfied: 'success',
  waived: 'default',
};

/** A colored chip for a requirement status (required/optional/satisfied/waived). */
export function RequirementBadge({ status }: { status: RequirementStatus }) {
  return <Chip size="small" label={status} color={REQUIREMENT_COLOR[status]} />;
}

/** A done / in-progress badge for the completeness flag. */
export function DoneBadge({ done }: { done: boolean }) {
  return (
    <Chip
      size="small"
      label={done ? 'done' : 'in progress'}
      color={done ? 'success' : 'default'}
      variant={done ? 'filled' : 'outlined'}
    />
  );
}

/** A follow-up state badge (on_track / overdue / escalated). */
export function FollowupBadge({ state }: { state: string }) {
  const color: ChipColor =
    state === 'escalated'
      ? 'error'
      : state === 'overdue'
        ? 'warning'
        : 'success';
  return <Chip size="small" label={state} color={color} />;
}
