import Mathlib

namespace MIKU.Fallback

inductive Decision
  | feasible
  | blocked
  deriving DecidableEq, Repr

def classify (gap epsilon : ℚ) : Decision :=
  if epsilon ≤ gap then .feasible else .blocked

theorem feasible_sound (gap epsilon : ℚ)
    (h : classify gap epsilon = .feasible) : epsilon ≤ gap := by
  by_cases he : epsilon ≤ gap
  · exact he
  · simp [classify, he] at h

theorem blocked_sound (gap epsilon : ℚ)
    (h : classify gap epsilon = .blocked) : gap < epsilon := by
  by_cases he : epsilon ≤ gap
  · simp [classify, he] at h
  · exact lt_of_not_ge he

theorem fail_closed (gap epsilon : ℚ) :
    classify gap epsilon = .blocked ∨ classify gap epsilon = .feasible := by
  exact (classify gap epsilon).casesOn (Or.inr rfl) (Or.inl rfl)

end MIKU.Fallback
