import Mathlib

namespace MIKU.Certificates

theorem child_bound_admissible
    (parent child cost : ℚ)
    (hparent : parent ≤ child)
    (hcost : child ≤ cost) : parent ≤ cost := by
  exact le_trans hparent hcost

theorem branch_gap_nonnegative (incumbent openLower : ℚ)
    (h : openLower ≤ incumbent) : 0 ≤ incumbent - openLower := by
  linarith

theorem branch_gap_certificate
    {α : Type} [Fintype α] [DecidableEq α] (evaluated pending : Finset α)
    (cost : α → ℚ) (incumbent openLower tolerance : ℚ)
    (hpart : evaluated ∪ pending = Finset.univ)
    (hdisj : Disjoint evaluated pending)
    (heval : ∀ x ∈ evaluated, incumbent ≤ cost x)
    (hopen : ∀ x ∈ pending, openLower ≤ cost x)
    (hgap : incumbent - openLower ≤ tolerance)
    (htol : 0 ≤ tolerance) :
    ∀ x : α, incumbent ≤ cost x + tolerance := by
  intro x
  have hx : x ∈ evaluated ∪ pending := by
    rw [hpart]
    exact Finset.mem_univ x
  simp only [Finset.mem_union] at hx
  rcases hx with hx | hx
  · linarith [heval x hx]
  · linarith [hopen x hx]

theorem zero_gap_implies_global_minimum
    {α : Type} [Fintype α] [DecidableEq α] (evaluated pending : Finset α)
    (cost : α → ℚ) (incumbent openLower : ℚ)
    (hpart : evaluated ∪ pending = Finset.univ)
    (hdisj : Disjoint evaluated pending)
    (heval : ∀ x ∈ evaluated, incumbent ≤ cost x)
    (hopen : ∀ x ∈ pending, openLower ≤ cost x)
    (hinc : incumbent = openLower) :
    ∀ x : α, incumbent ≤ cost x := by
  intro x
  have h := branch_gap_certificate evaluated pending cost incumbent openLower 0
    hpart hdisj heval hopen (by linarith [hinc]) (by norm_num) x
  simpa using h

end MIKU.Certificates
