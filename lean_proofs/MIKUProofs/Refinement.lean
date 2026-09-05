import Mathlib

namespace MIKU.Refinement

def update (old estimate alpha : ℚ) : ℚ := (1 - alpha) * old + alpha * estimate

theorem update_preserves_interval
    (lo hi old estimate alpha : ℚ)
    (hold : lo ≤ old) (hold' : old ≤ hi)
    (hest : lo ≤ estimate) (hest' : estimate ≤ hi)
    (ha : 0 ≤ alpha) (ha' : alpha ≤ 1) :
    lo ≤ update old estimate alpha ∧ update old estimate alpha ≤ hi := by
  dsimp [update]
  constructor <;> nlinarith [
    mul_nonneg (sub_nonneg.mpr ha') (sub_nonneg.mpr hold),
    mul_nonneg ha (sub_nonneg.mpr hest),
    mul_nonneg (sub_nonneg.mpr ha') (sub_nonneg.mpr (sub_nonneg.mpr hold')),
    mul_nonneg ha (sub_nonneg.mpr (sub_nonneg.mpr hest'))]

theorem update_equals_old (old estimate : ℚ) (h : estimate = old) (alpha : ℚ) :
    update old estimate alpha = old := by
  subst estimate
  dsimp [update]
  ring

theorem update_equals_estimate (old estimate alpha : ℚ) (h : alpha = 1) :
    update old estimate alpha = estimate := by
  subst alpha
  dsimp [update]
  ring

end MIKU.Refinement
