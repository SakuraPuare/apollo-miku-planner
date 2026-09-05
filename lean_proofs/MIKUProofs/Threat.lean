import Mathlib

namespace MIKU.Threat

structure Factors where
  ttc : ℚ
  overlap : ℚ
  velocity : ℚ
  kind : ℚ
  interaction : ℚ

def threat (w : Factors) (f : Factors) : ℚ :=
  w.ttc * f.ttc + w.overlap * f.overlap +
    w.velocity * f.velocity + w.kind * f.kind +
    w.interaction * f.interaction

def margin (δmin δmax θ : ℚ) : ℚ := δmin + (δmax - δmin) * θ

theorem threat_bounded
    (w f : Factors)
    (hw₁ : 0 ≤ w.ttc) (hw₂ : 0 ≤ w.overlap)
    (hw₃ : 0 ≤ w.velocity) (hw₄ : 0 ≤ w.kind)
    (hw₅ : 0 ≤ w.interaction)
    (hws : w.ttc + w.overlap + w.velocity + w.kind + w.interaction = 1)
    (hf₁ : 0 ≤ f.ttc) (hf₁' : f.ttc ≤ 1)
    (hf₂ : 0 ≤ f.overlap) (hf₂' : f.overlap ≤ 1)
    (hf₃ : 0 ≤ f.velocity) (hf₃' : f.velocity ≤ 1)
    (hf₄ : 0 ≤ f.kind) (hf₄' : f.kind ≤ 1)
    (hf₅ : 0 ≤ f.interaction) (hf₅' : f.interaction ≤ 1) :
    0 ≤ threat w f ∧ threat w f ≤ 1 := by
  dsimp [threat]
  constructor
  · positivity
  · nlinarith [mul_le_mul_of_nonneg_left hf₁' hw₁,
      mul_le_mul_of_nonneg_left hf₂' hw₂,
      mul_le_mul_of_nonneg_left hf₃' hw₃,
      mul_le_mul_of_nonneg_left hf₄' hw₄,
      mul_le_mul_of_nonneg_left hf₅' hw₅]

theorem margin_bounded
    (δmin δmax θ : ℚ)
    (horder : δmin ≤ δmax)
    (hθ : 0 ≤ θ) (hθ' : θ ≤ 1) :
    δmin ≤ margin δmin δmax θ ∧ margin δmin δmax θ ≤ δmax := by
  dsimp [margin]
  constructor <;> nlinarith

theorem margin_monotone
    (δmin δmax θ₁ θ₂ : ℚ)
    (horder : δmin ≤ δmax) (hθ : θ₁ ≤ θ₂) :
    margin δmin δmax θ₁ ≤ margin δmin δmax θ₂ := by
  dsimp [margin]
  nlinarith

end MIKU.Threat

namespace MIKU.ThreatConcrete

def weights : MIKU.Threat.Factors :=
  ⟨3 / 10, 1 / 5, 3 / 20, 1 / 10, 1 / 4⟩

theorem weights_nonnegative :
    0 ≤ weights.ttc ∧ 0 ≤ weights.overlap ∧ 0 ≤ weights.velocity ∧
      0 ≤ weights.kind ∧ 0 ≤ weights.interaction := by
  norm_num [weights]

theorem weights_sum_one :
    weights.ttc + weights.overlap + weights.velocity + weights.kind +
      weights.interaction = 1 := by
  norm_num [weights]

theorem concrete_threat_bounded (f : MIKU.Threat.Factors)
    (hf₁ : 0 ≤ f.ttc) (hf₁' : f.ttc ≤ 1)
    (hf₂ : 0 ≤ f.overlap) (hf₂' : f.overlap ≤ 1)
    (hf₃ : 0 ≤ f.velocity) (hf₃' : f.velocity ≤ 1)
    (hf₄ : 0 ≤ f.kind) (hf₄' : f.kind ≤ 1)
    (hf₅ : 0 ≤ f.interaction) (hf₅' : f.interaction ≤ 1) :
    0 ≤ MIKU.Threat.threat weights f ∧ MIKU.Threat.threat weights f ≤ 1 := by
  apply MIKU.Threat.threat_bounded weights f
  · norm_num [weights]
  · norm_num [weights]
  · norm_num [weights]
  · norm_num [weights]
  · norm_num [weights]
  · exact weights_sum_one
  · exact hf₁
  · exact hf₁'
  · exact hf₂
  · exact hf₂'
  · exact hf₃
  · exact hf₃'
  · exact hf₄
  · exact hf₄'
  · exact hf₅
  · exact hf₅'

theorem concrete_margin_bounds
    (δmin δmax θ : ℚ) (horder : δmin ≤ δmax)
    (hθ : 0 ≤ θ) (hθ' : θ ≤ 1) :
    δmin ≤ MIKU.Threat.margin δmin δmax θ ∧
      MIKU.Threat.margin δmin δmax θ ≤ δmax :=
  MIKU.Threat.margin_bounded δmin δmax θ horder hθ hθ'

end MIKU.ThreatConcrete
