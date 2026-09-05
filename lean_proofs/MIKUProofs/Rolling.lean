import Mathlib

namespace MIKU.Rolling

inductive Mode
  | searching
  | committed
  | blocked
  deriving DecidableEq

def update (old fresh : Mode) : Mode :=
  match old with
  | .committed => .committed
  | .blocked => .blocked
  | .searching => fresh

theorem commitment_persists (fresh : Mode) :
    update .committed fresh = .committed := by
  rfl

theorem blocked_is_fail_closed (fresh : Mode) :
    update .blocked fresh = .blocked := by
  rfl

theorem searching_accepts_new_decision (fresh : Mode) :
    update .searching fresh = fresh := by
  rfl

structure TemporalChoice where
  station : ℚ
  arrival : ℚ
  windowStart : ℚ
  windowEnd : ℚ
  validWindow : windowStart ≤ arrival ∧ arrival ≤ windowEnd

def causallyOrdered (maxSpeed : ℚ) (a b : TemporalChoice) : Prop :=
  a.station ≤ b.station ∧
    a.arrival + (b.station - a.station) / maxSpeed ≤ b.arrival

theorem causal_transitive
    (v : ℚ) (hv : 0 < v)
    (a b c : TemporalChoice)
    (hab : causallyOrdered v a b)
    (hbc : causallyOrdered v b c) :
    a.station ≤ c.station ∧
      a.arrival + (c.station - a.station) / v ≤ c.arrival := by
  constructor
  · linarith [hab.1, hbc.1]
  · have hv0 : 0 ≤ v := le_of_lt hv
    have htravel : (b.station - a.station) / v +
        (c.station - b.station) / v = (c.station - a.station) / v := by
      field_simp [ne_of_gt hv]
      ring
    linarith [hab.2, hbc.2]

end MIKU.Rolling
