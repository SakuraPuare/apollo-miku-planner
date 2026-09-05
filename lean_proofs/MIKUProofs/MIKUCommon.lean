import Mathlib

/- Shared Lean contracts for the MIKU papers.  These are intentionally small
   mathematical kernels: the surrounding numerical/QP implementation must
   satisfy these contracts before the theorems apply. -/
namespace MIKU.Common

def inflated (u v δ : ℚ) : ℚ × ℚ := (u - δ, v + δ)

theorem inflated_left_le (u v δ : ℚ) (hδ : 0 ≤ δ) :
    (inflated u v δ).1 ≤ u := by
  dsimp [inflated]
  linarith

theorem inflation_is_ordered (u v δ : ℚ) (hδ : 0 ≤ δ) (huv : u ≤ v) :
    (inflated u v δ).1 ≤ (inflated u v δ).2 := by
  dsimp [inflated]
  linarith

def threatDelta (base extra : ℚ) : ℚ := base + extra

theorem threat_delta_monotone (base extra : ℚ) (hextra : 0 ≤ extra) :
    base ≤ threatDelta base extra := by
  dsimp [threatDelta]
  linarith

def arrivalTime (s s₀ v : ℚ) : ℚ := (s - s₀) / v

theorem arrival_time_monotone (s₁ s₂ s₀ v : ℚ) (hv : 0 < v) (hs : s₁ ≤ s₂) :
    arrivalTime s₁ s₀ v ≤ arrivalTime s₂ s₀ v := by
  dsimp [arrivalTime]
  apply div_le_div_of_nonneg_right _ (le_of_lt hv)
  linarith

def corridorPoint (lower upper : ℚ) : ℚ := (lower + upper) / 2

theorem corridor_point_feasible (lower upper : ℚ) (h : lower ≤ upper) :
    lower ≤ corridorPoint lower upper ∧ corridorPoint lower upper ≤ upper := by
  dsimp [corridorPoint]
  constructor <;> linarith

theorem interval_convex
    (lower upper x y w : ℚ)
    (hx : lower ≤ x) (hx' : x ≤ upper)
    (hy : lower ≤ y) (hy' : y ≤ upper)
    (hw : 0 ≤ w) (hw' : w ≤ 1) :
    lower ≤ w * x + (1 - w) * y ∧
      w * x + (1 - w) * y ≤ upper := by
  constructor <;> nlinarith

theorem box_feasible_iff (lower upper : ℚ) :
    (∃ x : ℚ, lower ≤ x ∧ x ≤ upper) ↔ lower ≤ upper := by
  constructor
  · rintro ⟨x, hx, hx'⟩
    linarith
  · intro h
    exact ⟨(lower + upper) / 2, by constructor <;> linarith⟩

def beforeWindowWidth (horizonStart occupancyStart guard : ℚ) : ℚ :=
  occupancyStart - guard - horizonStart

def afterWindowWidth (occupancyEnd guard horizonEnd : ℚ) : ℚ :=
  horizonEnd - (occupancyEnd + guard)

theorem before_window_nonempty
    (horizonStart occupancyStart guard : ℚ)
    (h : horizonStart + guard ≤ occupancyStart) :
    0 ≤ beforeWindowWidth horizonStart occupancyStart guard := by
  dsimp [beforeWindowWidth]
  linarith

theorem after_window_nonempty
    (occupancyEnd guard horizonEnd : ℚ)
    (h : occupancyEnd + guard ≤ horizonEnd) :
    0 ≤ afterWindowWidth occupancyEnd guard horizonEnd := by
  dsimp [afterWindowWidth]
  linarith

def intervalsDisjoint (x₁ r₁ x₂ r₂ : ℚ) : Prop :=
  x₁ + r₁ ≤ x₂ - r₂ ∨ x₂ + r₂ ≤ x₁ - r₁

theorem separated_centres_are_safe
    (x₁ r₁ x₂ r₂ : ℚ) (h : intervalsDisjoint x₁ r₁ x₂ r₂) :
    ¬ (x₁ - r₁ < x₂ + r₂ ∧ x₂ - r₂ < x₁ + r₁) := by
  rcases h with h | h <;> intro hbad
  · linarith
  · linarith

def maxList : List ℚ → ℚ
  | [] => 0
  | x :: xs => max x (maxList xs)

theorem le_maxList {x : ℚ} : ∀ {xs : List ℚ}, x ∈ xs → x ≤ maxList xs := by
  intro xs hx
  induction xs with
  | nil => simp at hx
  | cons y ys ih =>
      simp only [List.mem_cons] at hx
      rcases hx with rfl | hx
      · exact le_max_left _ _
      · exact le_trans (ih hx) (le_max_right _ _)

end MIKU.Common
