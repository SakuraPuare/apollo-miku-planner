import Mathlib

namespace MIKU.RobustEnvelope

def predicted (p v t : ℚ) : ℚ := p + v * t
def radius (εp εv t : ℚ) : ℚ := εp + t * εv

theorem propagated_error_bound
    (p v p' v' t εp εv : ℚ)
    (ht : 0 ≤ t) (hεp : 0 ≤ εp) (hεv : 0 ≤ εv)
    (hpLo : -εp ≤ p' - p) (hpHi : p' - p ≤ εp)
    (hvLo : -εv ≤ v' - v) (hvHi : v' - v ≤ εv) :
    -radius εp εv t ≤ predicted p' v' t - predicted p v t ∧
      predicted p' v' t - predicted p v t ≤ radius εp εv t := by
  dsimp [predicted, radius]
  have hvLo' : -t * εv ≤ t * (v' - v) := by
    nlinarith [mul_le_mul_of_nonneg_left hvLo ht]
  have hvHi' : t * (v' - v) ≤ t * εv :=
    mul_le_mul_of_nonneg_left hvHi ht
  constructor <;> nlinarith

theorem inflated_interval_contains_truth
    (nominal truth halfWidth error : ℚ)
    (hwidth : 0 ≤ halfWidth) (herror : 0 ≤ error)
    (hlo : -error ≤ truth - nominal)
    (hhi : truth - nominal ≤ error) :
    nominal - halfWidth - error ≤ truth - halfWidth ∧
      truth + halfWidth ≤ nominal + halfWidth + error := by
  constructor <;> linarith

theorem larger_error_tube_is_conservative
    (ε₁ ε₂ nominal truth : ℚ)
    (hε : ε₁ ≤ ε₂)
    (hlo : nominal - ε₁ ≤ truth)
    (hhi : truth ≤ nominal + ε₁) :
    nominal - ε₂ ≤ truth ∧ truth ≤ nominal + ε₂ := by
  constructor <;> linarith

end MIKU.RobustEnvelope
