import Mathlib

namespace MIKU.ThreatSigmoid

noncomputable def sigmoid (x : ℝ) : ℝ := 1 / (1 + Real.exp (-x))

noncomputable def fVel (relativeVelocity : ℝ) : ℝ :=
  sigmoid (5 * relativeVelocity / 12)

theorem sigmoid_pos (x : ℝ) : 0 < sigmoid x := by
  dsimp [sigmoid]
  positivity

theorem sigmoid_lt_one (x : ℝ) : sigmoid x < 1 := by
  dsimp [sigmoid]
  have he : 0 < Real.exp (-x) := Real.exp_pos _
  have hd : 0 < 1 + Real.exp (-x) := by linarith
  apply (div_lt_iff₀ hd).2
  linarith

theorem sigmoid_bounds (x : ℝ) : 0 < sigmoid x ∧ sigmoid x < 1 :=
  ⟨sigmoid_pos x, sigmoid_lt_one x⟩

theorem sigmoid_monotone {x y : ℝ} (h : x ≤ y) : sigmoid x ≤ sigmoid y := by
  dsimp [sigmoid]
  have hxy : Real.exp (-y) ≤ Real.exp (-x) := by
    exact Real.exp_le_exp.mpr (by linarith)
  have hp : 0 < 1 + Real.exp (-y) := by positivity
  have hden : 1 + Real.exp (-y) ≤ 1 + Real.exp (-x) := by linarith
  exact one_div_le_one_div_of_le hp hden

theorem fVel_bounds (relativeVelocity : ℝ) :
    0 < fVel relativeVelocity ∧ fVel relativeVelocity < 1 := by
  exact sigmoid_bounds _

theorem fVel_monotone {v₁ v₂ : ℝ} (h : v₁ ≤ v₂) :
    fVel v₁ ≤ fVel v₂ := by
  apply sigmoid_monotone
  nlinarith

end MIKU.ThreatSigmoid
