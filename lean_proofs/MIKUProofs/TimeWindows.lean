import Mathlib

namespace MIKU.Time

structure Window where
  start : ℚ
  finish : ℚ

def contains (w : Window) (t : ℚ) : Prop := w.start ≤ t ∧ t ≤ w.finish

def occupied (enter exit guard t : ℚ) : Prop :=
  enter - guard ≤ t ∧ t ≤ exit + guard

def before (horizon occupancy guard : ℚ) : Window :=
  ⟨horizon, occupancy - guard⟩

def after (occupancy guard horizon : ℚ) : Window :=
  ⟨occupancy + guard, horizon⟩

theorem before_avoids_occupied
    (horizon occupancy guard t : ℚ)
    (ht : contains (before horizon occupancy guard) t) :
    t ≤ occupancy - guard := by
  exact ht.2

theorem after_avoids_occupied
    (occupancy guard horizon t : ℚ)
    (ht : contains (after occupancy guard horizon) t) :
    occupancy + guard ≤ t := by
  exact ht.1

theorem before_not_occupied
    (horizon enter exit guard t : ℚ)
    (ht : t < enter - guard) :
    ¬ occupied enter exit guard t := by
  intro ho
  dsimp [occupied] at ho
  linarith

theorem after_not_occupied
    (enter exit guard horizon t : ℚ)
    (ht : exit + guard < t) :
    ¬ occupied enter exit guard t := by
  intro ho
  dsimp [occupied] at ho
  linarith

theorem outside_occupied_is_before_or_after
    (enter exit guard t : ℚ) (hnot : ¬ occupied enter exit guard t) :
    t < enter - guard ∨ exit + guard < t := by
  by_cases hleft : enter - guard ≤ t
  · right
    by_contra hright
    apply hnot
    exact ⟨hleft, le_of_not_gt hright⟩
  · left
    exact lt_of_not_ge hleft

theorem before_after_disjoint
    (horizon enter exit guard : ℚ)
    (hguard : 0 ≤ guard) (hocc : enter ≤ exit)
    (hstrict : enter < exit ∨ 0 < guard) :
    ∀ t, ¬ (contains (before horizon enter guard) t ∧
      contains (after exit guard horizon) t) := by
  intro t h
  dsimp [contains, before, after] at h
  rcases hstrict with hstrict | hstrict <;> linarith [h.1.2, h.2.1]

theorem before_nonempty
  (horizon enter guard : ℚ) (h : horizon + guard ≤ enter) :
    (before horizon enter guard).start ≤ (before horizon enter guard).finish := by
  dsimp [before]
  linarith

theorem after_nonempty
  (exit guard horizon : ℚ) (h : exit + guard ≤ horizon) :
    (after exit guard horizon).start ≤ (after exit guard horizon).finish := by
  dsimp [after]
  linarith

def monotoneArrival (s₀ v : ℚ) (s : ℚ) : ℚ := (s - s₀) / v

theorem monotone_arrival
    (s₀ v s₁ s₂ : ℚ) (hv : 0 < v) (hs : s₁ ≤ s₂) :
    monotoneArrival s₀ v s₁ ≤ monotoneArrival s₀ v s₂ := by
  dsimp [monotoneArrival]
  apply div_le_div_of_nonneg_right _ (le_of_lt hv)
  linarith

end MIKU.Time
