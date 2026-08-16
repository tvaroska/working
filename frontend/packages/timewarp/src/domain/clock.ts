/**
 * timewarp domain layer (lessons B3): map the virtual-clock state (snake_case)
 * to a camelCase view. The time-warp surface deliberately avoids SSE (B4): the
 * clock only moves on an explicit REST call, and "Play" is a browser interval.
 */

export interface WireSla {
  deadline: number;
  cadence: number;
  max_nudges: number;
}

export interface WireTimer {
  id: string;
  context_id: string;
  fire_at: number;
  kind: string;
  sequence: number;
  fired: boolean;
}

export interface WireFollowup {
  state: string;
  nudges_fired: number;
  escalated: boolean;
}

export interface WireTimewarpState {
  now: number;
  sla: WireSla;
  timers: WireTimer[];
  followup: WireFollowup;
}

export interface SlaView {
  deadline: number;
  cadence: number;
  maxNudges: number;
}

export interface TimerView {
  id: string;
  contextId: string;
  fireAt: number;
  kind: string;
  sequence: number;
  fired: boolean;
}

export interface FollowupView {
  state: string;
  nudgesFired: number;
  escalated: boolean;
}

export interface TimewarpView {
  now: number;
  sla: SlaView;
  timers: TimerView[];
  followup: FollowupView;
}

export function mapTimewarp(wire: WireTimewarpState): TimewarpView {
  return {
    now: wire.now,
    sla: {
      deadline: wire.sla.deadline,
      cadence: wire.sla.cadence,
      maxNudges: wire.sla.max_nudges,
    },
    timers: wire.timers.map((t) => ({
      id: t.id,
      contextId: t.context_id,
      fireAt: t.fire_at,
      kind: t.kind,
      sequence: t.sequence,
      fired: t.fired,
    })),
    followup: {
      state: wire.followup.state,
      nudgesFired: wire.followup.nudges_fired,
      escalated: wire.followup.escalated,
    },
  };
}
