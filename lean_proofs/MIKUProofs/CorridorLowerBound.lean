import Mathlib

namespace MIKU.CorridorLowerBound

def distZero (lo hi : ℚ) : ℚ :=
  if lo ≤ 0 ∧ 0 ≤ hi then 0 else min |lo| |hi|

theorem distZero_nonnegative (lo hi : ℚ) : 0 ≤ distZero lo hi := by
  dsimp [distZero]
  split_ifs
  · norm_num
  · exact le_min (abs_nonneg _) (abs_nonneg _)

theorem distZero_sq_le
    (lo hi x : ℚ) (hlohi : lo ≤ hi) (hlo : lo ≤ x) (hhi : x ≤ hi) :
    (distZero lo hi)^2 ≤ x^2 := by
  by_cases hz : lo ≤ 0 ∧ 0 ≤ hi
  · simp [distZero, hz]
    positivity
  · have hside : 0 < lo ∨ hi < 0 := by
      by_cases hlo0 : lo ≤ 0
      · right
        have : ¬ 0 ≤ hi := by
          intro hhi0
          exact hz ⟨hlo0, hhi0⟩
        exact lt_of_not_ge this
      · left
        exact lt_of_not_ge hlo0
    rcases hside with hpos | hneg
    · have hlo0 : 0 ≤ lo := le_of_lt hpos
      have hhi0 : 0 ≤ hi := le_trans hlo0 hlohi
      rw [distZero, if_neg hz, abs_of_nonneg hlo0, abs_of_nonneg hhi0,
        min_eq_left hlohi]
      nlinarith [sq_nonneg (x - lo)]
    · have hhi0 : hi ≤ 0 := le_of_lt hneg
      have hlo0 : lo ≤ 0 := le_trans hlohi hhi0
      rw [distZero, if_neg hz, abs_of_nonpos hlo0, abs_of_nonpos hhi0,
        min_eq_right (neg_le_neg hlohi)]
      nlinarith [sq_nonneg (x - hi)]

theorem weighted_station_lower_bound
    (weight lo hi x : ℚ)
    (hw : 0 ≤ weight) (hlohi : lo ≤ hi)
    (hlo : lo ≤ x) (hhi : x ≤ hi) :
    weight * (distZero lo hi)^2 ≤ weight * x^2 := by
  exact mul_le_mul_of_nonneg_left (distZero_sq_le lo hi x hlohi hlo hhi) hw

theorem full_objective_admissible
    (lateralLowerBound lateralCost otherCost : ℚ)
    (hlat : lateralLowerBound ≤ lateralCost)
    (hother : 0 ≤ otherCost) :
    lateralLowerBound ≤ lateralCost + otherCost := by
  linarith

end MIKU.CorridorLowerBound
