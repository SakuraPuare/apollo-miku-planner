import Mathlib

namespace MIKU.QuadraticSweep

def quadratic (a b c t : ℚ) : ℚ := a * t ^ 2 + b * t + c

theorem nonnegative_of_discriminant_nonpositive
    (a b c : ℚ) (ha : 0 < a) (hdisc : b ^ 2 - 4 * a * c ≤ 0) (t : ℚ) :
    0 ≤ quadratic a b c t := by
  dsimp [quadratic]
  nlinarith [sq_nonneg (2 * a * t + b)]

theorem positive_of_discriminant_negative
    (a b c : ℚ) (ha : 0 < a) (hdisc : b ^ 2 - 4 * a * c < 0) (t : ℚ) :
    0 < quadratic a b c t := by
  dsimp [quadratic]
  nlinarith [sq_nonneg (2 * a * t + b)]

end MIKU.QuadraticSweep
