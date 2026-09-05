import Mathlib

namespace MIKU.Scanline

structure Interval where
  start : ℕ
  finish : ℕ
  ordered : start ≤ finish

def overlaps (a b : Interval) : Prop :=
  a.start ≤ b.finish ∧ b.start ≤ a.finish

def frontier : ℕ → List Interval → ℕ
  | f, [] => f
  | f, x :: xs => frontier (max f x.finish) xs

theorem frontier_seed_le (f : ℕ) (xs : List Interval) :
    f ≤ frontier f xs := by
  induction xs generalizing f with
  | nil => exact le_rfl
  | cons x xs ih =>
      exact le_trans (le_max_left _ _) (ih (max f x.finish))

theorem frontier_spec (f : ℕ) (xs : List Interval) :
    ∀ i ∈ xs, i.finish ≤ frontier f xs := by
  induction xs generalizing f with
  | nil => simp
  | cons x xs ih =>
      intro i hi
      simp only [List.mem_cons] at hi
      rcases hi with rfl | hi
      · exact le_trans (le_max_right _ _) (frontier_seed_le _ _)
      · exact ih (max f x.finish) i hi

theorem frontier_monotone (f₁ f₂ : ℕ) (h : f₁ ≤ f₂) (xs : List Interval) :
    frontier f₁ xs ≤ frontier f₂ xs := by
  induction xs generalizing f₁ f₂ with
  | nil => exact h
  | cons x xs ih =>
      apply ih
      exact max_le_max h le_rfl

theorem overlaps_symm (a b : Interval) : overlaps a b ↔ overlaps b a := by
  constructor <;> intro h <;> exact ⟨h.2, h.1⟩

theorem disjoint_after_frontier
    (frontier next : ℕ)
    (hnext : frontier < next)
    {seen : Interval → Prop}
    (hseen : ∀ i, seen i → i.finish ≤ frontier) :
    ∀ i, seen i → ¬ overlaps i ⟨next, next, le_rfl⟩ := by
  intro i hi hov
  dsimp [overlaps] at hov
  have hi' := hseen i hi
  omega

theorem sorted_next_disjoint
    (frontier next : ℕ) (hnext : frontier < next)
    {seen : List Interval} (hseen : ∀ i ∈ seen, i.finish ≤ frontier) :
    ∀ i ∈ seen, ¬ overlaps i ⟨next, next, le_rfl⟩ := by
  intro i hi
  exact disjoint_after_frontier frontier next hnext (fun j hj => hseen j hj) i hi

theorem frontier_covers_seen
    (seed : ℕ) (seen : List Interval) :
    ∀ i ∈ seen, i.finish ≤ frontier seed seen := by
  exact frontier_spec seed seen

theorem scan_boundary_is_safe
    (seed next : ℕ) (seen : List Interval)
    (hnext : frontier seed seen < next) :
    ∀ i ∈ seen, ¬ overlaps i ⟨next, next, le_rfl⟩ := by
  apply sorted_next_disjoint (frontier seed seen) next hnext
  exact frontier_covers_seen seed seen

theorem frontier_update_preserves_bound
    (frontier next : ℕ) (i : Interval) (h : i.finish ≤ frontier) :
    i.finish ≤ max frontier next ∧ next ≤ max frontier next := by
  constructor
  · exact le_max_of_le_left h
  · exact le_max_of_le_right le_rfl

theorem append_interval_keeps_coverage
    (frontier : ℕ) {xs : List Interval}
    (hxs : ∀ i ∈ xs, i.finish ≤ frontier)
    (x : Interval) :
    ∀ i ∈ xs ++ [x], i.finish ≤ max frontier x.finish := by
  intro i hi
  simp only [List.mem_append, List.mem_singleton] at hi
  rcases hi with hi | rfl
  · exact le_trans (hxs i hi) (le_max_left _ _)
  · exact le_max_right _ _

end MIKU.Scanline
