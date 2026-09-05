import Mathlib

namespace MIKU.SafeWindowComplement

def inHorizon (lo hi t : ℚ) : Prop := lo ≤ t ∧ t ≤ hi
def occupied (enter exit guard t : ℚ) : Prop :=
  enter - guard ≤ t ∧ t ≤ exit + guard
def safeBefore (horizonLo enter guard t : ℚ) : Prop :=
  horizonLo ≤ t ∧ t < enter - guard
def safeAfter (exit guard horizonHi t : ℚ) : Prop :=
  exit + guard < t ∧ t ≤ horizonHi

theorem before_safe
    (horizonLo enter exit guard t : ℚ)
    (h : safeBefore horizonLo enter guard t) :
    ¬ occupied enter exit guard t := by
  intro ho
  dsimp [safeBefore, occupied] at h ho
  linarith

theorem after_safe
    (enter exit guard horizonHi t : ℚ)
    (h : safeAfter exit guard horizonHi t) :
    ¬ occupied enter exit guard t := by
  intro ho
  dsimp [safeAfter, occupied] at h ho
  linarith

theorem horizon_complement
    (horizonLo horizonHi enter exit guard t : ℚ)
    (horizon : inHorizon horizonLo horizonHi t)
    (hocc : enter ≤ exit)
    (hnot : ¬ occupied enter exit guard t) :
    safeBefore horizonLo enter guard t ∨ safeAfter exit guard horizonHi t := by
  by_cases hleft : t < enter - guard
  · exact Or.inl ⟨horizon.1, hleft⟩
  · right
    constructor
    · by_contra hright
      apply hnot
      dsimp [occupied]
      constructor
      · exact le_of_not_gt hleft
      · exact le_of_not_gt hright
    · exact horizon.2

theorem safe_components_disjoint
    (horizonLo horizonHi enter exit guard t : ℚ)
    (hocc : enter ≤ exit) (hguard : 0 ≤ guard) :
    ¬ (safeBefore horizonLo enter guard t ∧ safeAfter exit guard horizonHi t) := by
  intro h
  dsimp [safeBefore, safeAfter] at h
  linarith

end MIKU.SafeWindowComplement
