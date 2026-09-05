import Mathlib

namespace MIKU.ThreatExact

def fTTC (ttc : ℚ) : ℚ :=
  if ttc ≤ 2 then 1 else if 7 ≤ ttc then 0 else (7 - ttc) / 5

theorem fTTC_bounds (ttc : ℚ) : 0 ≤ fTTC ttc ∧ fTTC ttc ≤ 1 := by
  by_cases hcrit : ttc ≤ 2
  · simp [fTTC, hcrit]
  · have h2 : 2 ≤ ttc := le_of_not_ge hcrit
    by_cases hmax : 7 ≤ ttc
    · simp [fTTC, hcrit, hmax]
    · have h7 : ttc ≤ 7 := le_of_not_ge hmax
      constructor
      · dsimp [fTTC]
        rw [if_neg hcrit, if_neg hmax]
        linarith
      · dsimp [fTTC]
        rw [if_neg hcrit, if_neg hmax]
        linarith

def fTTCPipeline (distance relativeVelocity : ℚ) : ℚ :=
  if distance ≤ 0 ∨ relativeVelocity ≤ 1 / 1000 then 0
  else fTTC (distance / relativeVelocity)

theorem fTTCPipeline_bounds (distance relativeVelocity : ℚ) :
    0 ≤ fTTCPipeline distance relativeVelocity ∧
      fTTCPipeline distance relativeVelocity ≤ 1 := by
  by_cases h : distance ≤ 0 ∨ relativeVelocity ≤ 1 / 1000
  · rw [fTTCPipeline, if_pos h]
    norm_num
  · simp only [fTTCPipeline, if_neg h]
    exact fTTC_bounds _

theorem fTTCPipeline_zero_nonclosing
    (distance relativeVelocity : ℚ)
    (h : distance ≤ 0 ∨ relativeVelocity ≤ 1 / 1000) :
    fTTCPipeline distance relativeVelocity = 0 := by
  rw [fTTCPipeline, if_pos h]

theorem fTTC_antitone {t₁ t₂ : ℚ} (h : t₁ ≤ t₂) :
    fTTC t₂ ≤ fTTC t₁ := by
  by_cases h₂ : t₂ ≤ 2
  · have h₁ : t₁ ≤ 2 := le_trans h h₂
    simp [fTTC, h₁, h₂]
  · by_cases h₁ : t₁ ≤ 2
    · dsimp [fTTC]
      rw [if_neg h₂, if_pos h₁]
      simpa [fTTC, h₂] using (fTTC_bounds t₂).2
    · by_cases h₂max : 7 ≤ t₂
      · by_cases h₁max : 7 ≤ t₁
        · simp [fTTC, h₁, h₂, h₁max, h₂max]
        · dsimp [fTTC]
          rw [if_pos h₂max, if_neg h₂, if_neg h₁, if_neg h₁max]
          have ht₁ : t₁ ≤ 7 := le_of_not_ge h₁max
          linarith
      · have ht₂ : t₂ ≤ 7 := le_of_not_ge h₂max
        by_cases h₁max : 7 ≤ t₁
        · have : 7 ≤ t₂ := le_trans h₁max h
          exact False.elim (h₂max this)
        · dsimp [fTTC]
          rw [if_neg h₂, if_neg h₂max, if_neg h₁, if_neg h₁max]
          linarith

def overlapFraction (overlap denom : ℚ) : ℚ :=
  min 1 (max 0 overlap / max (1 / 10) denom)

structure ClosedInterval where
  lo : ℚ
  hi : ℚ
  ordered : lo ≤ hi

def overlapLength (a b : ClosedInterval) : ℚ :=
  max 0 (min a.hi b.hi - max a.lo b.lo)

theorem overlapLength_nonnegative (a b : ClosedInterval) :
    0 ≤ overlapLength a b := by
  exact le_max_left _ _

theorem overlapLength_zero_of_separated
    (a b : ClosedInterval) (h : a.hi ≤ b.lo ∨ b.hi ≤ a.lo) :
    overlapLength a b = 0 := by
  dsimp [overlapLength]
  apply max_eq_left
  rcases h with h | h
  · have hmax : b.lo ≤ max a.lo b.lo := le_max_right _ _
    have hmin : min a.hi b.hi ≤ a.hi := min_le_left _ _
    linarith
  · have hmax : a.lo ≤ max a.lo b.lo := le_max_left _ _
    have hmin : min a.hi b.hi ≤ b.hi := min_le_right _ _
    linarith

def overlapFractionIntervals (a b : ClosedInterval) (denom : ℚ) : ℚ :=
  overlapFraction (overlapLength a b) denom

theorem overlapFractionIntervals_bounds
    (a b : ClosedInterval) (denom : ℚ) (hden : 0 < denom) :
    0 ≤ overlapFractionIntervals a b denom ∧
      overlapFractionIntervals a b denom ≤ 1 := by
  dsimp [overlapFractionIntervals, overlapFraction]
  have hden' : 0 < max (1 / 10) denom := by positivity
  have hratio : 0 ≤ max 0 (overlapLength a b) / max (1 / 10) denom :=
    div_nonneg (by positivity) (le_of_lt hden')
  exact ⟨le_min (by norm_num) hratio, min_le_left _ _⟩

theorem overlapFraction_code_bounds (overlap denom : ℚ) :
    0 ≤ overlapFraction overlap denom ∧ overlapFraction overlap denom ≤ 1 := by
  dsimp [overlapFraction]
  have hden : 0 < max (1 / 10) denom := by positivity
  have hratio : 0 ≤ max 0 overlap / max (1 / 10) denom :=
    div_nonneg (by positivity) (le_of_lt hden)
  exact ⟨le_min (by norm_num) hratio, min_le_left _ _⟩

theorem overlapFraction_zero_of_nonpositive (overlap denom : ℚ)
    (h : overlap ≤ 0) : overlapFraction overlap denom = 0 := by
  dsimp [overlapFraction]
  rw [max_eq_left h, zero_div, min_eq_right]
  norm_num

def interactionTerm (distance radius : ℚ) : ℚ :=
  if distance < radius then (radius - distance) / radius else 0

theorem interactionTerm_bounds
    (distance radius : ℚ) (hd : 0 ≤ distance) (hr : 0 < radius) :
    0 ≤ interactionTerm distance radius ∧ interactionTerm distance radius ≤ 1 := by
  by_cases h : distance < radius
  · dsimp [interactionTerm]
    rw [if_pos h]
    constructor
    · positivity
    · apply (div_le_iff₀ hr).2
      linarith
  · simp [interactionTerm, h]

def interactionScore (total neighbourCount : ℚ) : ℚ :=
  min 1 (max 0 total / max 1 neighbourCount)

theorem interactionScore_bounds
    (total neighbourCount : ℚ) (htotal : 0 ≤ total)
    (hcount : 0 ≤ neighbourCount) :
    0 ≤ interactionScore total neighbourCount ∧
      interactionScore total neighbourCount ≤ 1 := by
  dsimp [interactionScore]
  have hden : 0 < max 1 neighbourCount := by positivity
  have hratio : 0 ≤ max 0 total / max 1 neighbourCount :=
    div_nonneg (by positivity) (le_of_lt hden)
  exact ⟨le_min (by norm_num) hratio, min_le_left _ _⟩

def boundedAverage (terms : List ℚ) : ℚ :=
  min 1 (max 0 terms.sum / max 1 (terms.length : ℚ))

theorem sum_nonneg_of_unit_terms :
    ∀ terms : List ℚ, (∀ x ∈ terms, 0 ≤ x) → 0 ≤ terms.sum := by
  intro terms h
  exact List.sum_nonneg h

theorem sum_le_length_of_unit_terms :
    ∀ terms : List ℚ, (∀ x ∈ terms, x ≤ 1) → terms.sum ≤ (terms.length : ℚ) := by
  intro terms h
  induction terms with
  | nil => norm_num
  | cons x xs ih =>
      simp only [List.sum_cons, List.length_cons]
      have hx := h x (by simp)
      have hxs : ∀ y ∈ xs, y ≤ 1 := by
        intro y hy
        exact h y (by simp [hy])
      have hi := ih hxs
      norm_num at hi ⊢
      linarith

theorem boundedAverage_bounds
    (terms : List ℚ)
    (hlo : ∀ x ∈ terms, 0 ≤ x)
    (hhi : ∀ x ∈ terms, x ≤ 1) :
    0 ≤ boundedAverage terms ∧ boundedAverage terms ≤ 1 := by
  dsimp [boundedAverage]
  have hsum : 0 ≤ terms.sum := sum_nonneg_of_unit_terms terms hlo
  have hsum' : terms.sum ≤ (terms.length : ℚ) :=
    sum_le_length_of_unit_terms terms hhi
  have hden : 0 < max 1 (terms.length : ℚ) := by positivity
  have hratio : 0 ≤ max 0 terms.sum / max 1 (terms.length : ℚ) :=
    div_nonneg (by positivity) (le_of_lt hden)
  exact ⟨le_min (by norm_num) hratio, min_le_left _ _⟩

theorem overlapFraction_bounds (overlap denom : ℚ)
    (ho : 0 ≤ overlap) (hd : 0 < denom) :
    0 ≤ overlapFraction overlap denom ∧ overlapFraction overlap denom ≤ 1 := by
  dsimp [overlapFraction]
  have hden : 0 < max (1 / 10) denom := by positivity
  have hratio : 0 ≤ max 0 overlap / max (1 / 10) denom :=
    div_nonneg (by positivity) (le_of_lt hden)
  exact ⟨le_min (by norm_num) hratio, min_le_left _ _⟩

def weightedFive (w₁ w₂ w₃ w₄ w₅ x₁ x₂ x₃ x₄ x₅ : ℚ) : ℚ :=
  w₁*x₁ + w₂*x₂ + w₃*x₃ + w₄*x₄ + w₅*x₅

theorem weightedFive_bounds
    (w₁ w₂ w₃ w₄ w₅ x₁ x₂ x₃ x₄ x₅ : ℚ)
    (hw₁ : 0 ≤ w₁) (hw₂ : 0 ≤ w₂) (hw₃ : 0 ≤ w₃)
    (hw₄ : 0 ≤ w₄) (hw₅ : 0 ≤ w₅)
    (hws : w₁ + w₂ + w₃ + w₄ + w₅ = 1)
    (hx₁ : 0 ≤ x₁) (hx₁' : x₁ ≤ 1)
    (hx₂ : 0 ≤ x₂) (hx₂' : x₂ ≤ 1)
    (hx₃ : 0 ≤ x₃) (hx₃' : x₃ ≤ 1)
    (hx₄ : 0 ≤ x₄) (hx₄' : x₄ ≤ 1)
    (hx₅ : 0 ≤ x₅) (hx₅' : x₅ ≤ 1) :
    0 ≤ weightedFive w₁ w₂ w₃ w₄ w₅ x₁ x₂ x₃ x₄ x₅ ∧
      weightedFive w₁ w₂ w₃ w₄ w₅ x₁ x₂ x₃ x₄ x₅ ≤ 1 := by
  dsimp [weightedFive]
  constructor
  · positivity
  · nlinarith [mul_le_mul_of_nonneg_left hx₁' hw₁,
      mul_le_mul_of_nonneg_left hx₂' hw₂,
      mul_le_mul_of_nonneg_left hx₃' hw₃,
      mul_le_mul_of_nonneg_left hx₄' hw₄,
      mul_le_mul_of_nonneg_left hx₅' hw₅]

end MIKU.ThreatExact
