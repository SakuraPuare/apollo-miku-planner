import Mathlib

namespace MIKU.ContinuousSafety

def lerp (a b t : ℚ) : ℚ := (1 - t) * a + t * b

theorem lerp_lower
    (a b t δ : ℚ) (ha : δ ≤ a) (hb : δ ≤ b)
    (ht : 0 ≤ t) (ht' : t ≤ 1) : δ ≤ lerp a b t := by
  dsimp [lerp]
  nlinarith [mul_nonneg (sub_nonneg.mpr ht') (sub_nonneg.mpr ha),
    mul_nonneg ht (sub_nonneg.mpr hb)]

theorem lerp_upper
    (a b t U : ℚ) (ha : a ≤ U) (hb : b ≤ U)
    (ht : 0 ≤ t) (ht' : t ≤ 1) : lerp a b t ≤ U := by
  dsimp [lerp]
  nlinarith [mul_nonneg (sub_nonneg.mpr ht') (sub_nonneg.mpr (sub_nonneg.mpr ha)),
    mul_nonneg ht (sub_nonneg.mpr (sub_nonneg.mpr hb))]

def axisSeparated (ego obstacle egoRadius obstacleRadius : ℚ) : Prop :=
  obstacle - ego ≥ egoRadius + obstacleRadius

theorem linear_axis_separation
    (ego₀ ego₁ obs₀ obs₁ re ro t : ℚ)
    (h₀ : axisSeparated ego₀ obs₀ re ro)
    (h₁ : axisSeparated ego₁ obs₁ re ro)
    (ht : 0 ≤ t) (ht' : t ≤ 1) :
    axisSeparated (lerp ego₀ ego₁ t) (lerp obs₀ obs₁ t) re ro := by
  dsimp [axisSeparated] at h₀ h₁ ⊢
  dsimp [lerp]
  have hd₀ : 0 ≤ obs₀ - ego₀ - (re + ro) := by linarith
  have hd₁ : 0 ≤ obs₁ - ego₁ - (re + ro) := by linarith
  have hm₀ := mul_nonneg (sub_nonneg.mpr ht') hd₀
  have hm₁ := mul_nonneg ht hd₁
  nlinarith

theorem rectangle_noncollision_from_axis
    (ego₀ ego₁ obs₀ obs₁ re ro t : ℚ)
    (h₀ : axisSeparated ego₀ obs₀ re ro)
    (h₁ : axisSeparated ego₁ obs₁ re ro)
    (ht : 0 ≤ t) (ht' : t ≤ 1) :
    ¬ (lerp obs₀ obs₁ t - lerp ego₀ ego₁ t < re + ro) := by
  have hs := linear_axis_separation ego₀ ego₁ obs₀ obs₁ re ro t h₀ h₁ ht ht'
  dsimp [axisSeparated] at hs
  linarith

end MIKU.ContinuousSafety
