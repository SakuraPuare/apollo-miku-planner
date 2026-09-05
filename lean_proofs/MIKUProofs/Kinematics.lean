import Mathlib

namespace MIKU.Kinematics

def displacement (v₀ a t : ℚ) : ℚ := v₀ * t + (a * t^2) / 2

theorem displacement_nonnegative
    (v₀ a t : ℚ) (hv : 0 ≤ v₀) (ha : 0 ≤ a) (ht : 0 ≤ t) :
    0 ≤ displacement v₀ a t := by
  dsimp [displacement]
  positivity

theorem displacement_monotone
    (v₀ a t₁ t₂ : ℚ)
    (hv : 0 ≤ v₀) (ha : 0 ≤ a)
    (ht : 0 ≤ t₁) (h : t₁ ≤ t₂) :
    displacement v₀ a t₁ ≤ displacement v₀ a t₂ := by
  dsimp [displacement]
  have hdt : 0 ≤ t₂ - t₁ := by linarith
  have hsum : 0 ≤ t₂ + t₁ := by linarith
  have hsq : 0 ≤ t₂^2 - t₁^2 := by
    nlinarith [mul_nonneg hdt hsum]
  nlinarith [mul_nonneg hv hdt, mul_nonneg ha hsq]

theorem constant_velocity_identity
    (s s₀ v t : ℚ) (hv : v ≠ 0)
    (ht : t = (s - s₀) / v) : s₀ + v * t = s := by
  subst ht
  field_simp [hv]
  ring

end MIKU.Kinematics
