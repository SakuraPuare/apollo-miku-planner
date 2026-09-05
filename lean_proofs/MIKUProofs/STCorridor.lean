import Mathlib

namespace MIKU.STCorridor

def conflict (sLo sHi a b s t : ℚ) : Prop :=
  sLo < s ∧ s < sHi ∧ a ≤ t ∧ t ≤ b

def passBefore (sHi b epsS s t : ℚ) : Prop :=
  sHi + epsS ≤ s ∧ b ≤ t

def yieldAfter (sLo a epsS s t : ℚ) : Prop :=
  s ≤ sLo - epsS ∧ t < a

theorem pass_before_excludes_conflict
    (sLo sHi a b epsS s t : ℚ)
    (heps : 0 ≤ epsS)
    (hpass : passBefore sHi b epsS s t) :
    ¬ conflict sLo sHi a b s t := by
  intro hconf
  dsimp [passBefore, conflict] at hpass hconf
  linarith

theorem yield_after_excludes_conflict
    (sLo sHi a b epsS s t : ℚ)
    (heps : 0 ≤ epsS)
    (hyield : yieldAfter sLo a epsS s t) :
    ¬ conflict sLo sHi a b s t := by
  intro hconf
  dsimp [yieldAfter, conflict] at hyield hconf
  linarith

theorem causal_edge_transitive
    (v : ℚ) (hv : 0 < v)
    (s₁ t₁ s₂ t₂ s₃ t₃ : ℚ)
    (h12 : s₁ ≤ s₂ ∧ t₁ + (s₂ - s₁) / v ≤ t₂)
    (h23 : s₂ ≤ s₃ ∧ t₂ + (s₃ - s₂) / v ≤ t₃) :
    s₁ ≤ s₃ ∧ t₁ + (s₃ - s₁) / v ≤ t₃ := by
  constructor
  · linarith
  · have hsum : (s₂ - s₁) / v + (s₃ - s₂) / v = (s₃ - s₁) / v := by
      field_simp [ne_of_gt hv]
      ring
    linarith [h12.2, h23.2]

theorem causal_edge_implies_non_decreasing_time
    (v : ℚ) (hv : 0 < v) (s₁ t₁ s₂ t₂ : ℚ)
    (h : s₁ ≤ s₂ ∧ t₁ + (s₂ - s₁) / v ≤ t₂) :
    t₁ ≤ t₂ := by
  have hnonneg : 0 ≤ (s₂ - s₁) / v :=
    div_nonneg (sub_nonneg.mpr h.1) (le_of_lt hv)
  linarith [h.2]

end MIKU.STCorridor
