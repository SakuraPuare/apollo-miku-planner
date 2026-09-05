import Mathlib

namespace MIKU.RobustSafety

def disjoint (a b : Set α) : Prop := ∀ ⦃x⦄, x ∈ a → x ∈ b → False

theorem subset_preserves_disjoint
    {α : Type} {ego robust truth : Set α}
    (hcontain : truth ⊆ robust)
    (hrobust : disjoint ego robust) :
    disjoint ego truth := by
  intro x hex hxt
  exact hrobust hex (hcontain hxt)

theorem robust_collision_exclusion
    {α : Type} (egoFootprint robustOccupancy trueOccupancy : Set α)
    (hcontain : trueOccupancy ⊆ robustOccupancy)
    (hcertificate : ∀ ⦃x⦄, x ∈ egoFootprint → x ∈ robustOccupancy → False) :
    ∀ ⦃x⦄, x ∈ egoFootprint → x ∈ trueOccupancy → False := by
  exact subset_preserves_disjoint hcontain hcertificate

end MIKU.RobustSafety
