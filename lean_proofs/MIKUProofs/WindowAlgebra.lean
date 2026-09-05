import Mathlib

namespace MIKU.WindowAlgebra

structure Window where
  start : ℚ
  finish : ℚ
  ordered : start ≤ finish

def contains (w : Window) (t : ℚ) : Prop := w.start ≤ t ∧ t ≤ w.finish

def project (w : Window) (t : ℚ) : ℚ := min w.finish (max w.start t)

theorem project_mem (w : Window) (t : ℚ) : contains w (project w t) := by
  constructor
  · exact le_min w.ordered (le_max_left _ _)
  · exact min_le_left _ _

theorem project_eq_self {w : Window} {t : ℚ} (ht : contains w t) : project w t = t := by
  dsimp [project, contains] at *
  rw [max_eq_right ht.1, min_eq_right ht.2]

theorem project_left {w : Window} {t : ℚ} (ht : t ≤ w.start) : project w t = w.start := by
  dsimp [project]
  rw [max_eq_left ht, min_eq_right w.ordered]

theorem project_right {w : Window} {t : ℚ} (ht : w.finish ≤ t) : project w t = w.finish := by
  dsimp [project]
  rw [max_eq_right (le_trans w.ordered ht), min_eq_left ht]

theorem intersect_contains_iff
    (a b : Window) (t : ℚ) :
    (max a.start b.start ≤ t ∧ t ≤ min a.finish b.finish) ↔
      (contains a t ∧ contains b t) := by
  constructor
  · intro h
    constructor
    · exact ⟨le_trans (le_max_left _ _) h.1,
        le_trans h.2 (min_le_left _ _)⟩
    · exact ⟨le_trans (le_max_right _ _) h.1,
        le_trans h.2 (min_le_right _ _)⟩
  · rintro ⟨ha, hb⟩
    constructor
    · exact max_le ha.1 hb.1
    · exact le_min ha.2 hb.2

theorem intersect_nonempty_iff (a b : Window) :
    (max a.start b.start ≤ min a.finish b.finish) ↔
      ∃ t, contains a t ∧ contains b t := by
  constructor
  · intro h
    refine ⟨max a.start b.start, ?_⟩
    exact (intersect_contains_iff a b _).1 ⟨le_rfl, h⟩
  · rintro ⟨t, ha, hb⟩
    exact (max_le ha.1 hb.1).trans (le_min ha.2 hb.2)

theorem project_cases (w : Window) (t : ℚ) :
    t ≤ w.start ∨ contains w t ∨ w.finish ≤ t := by
  by_cases h₁ : t ≤ w.start
  · exact Or.inl h₁
  right
  by_cases h₂ : w.finish ≤ t
  · exact Or.inr h₂
  · exact Or.inl ⟨le_of_not_ge h₁, le_of_not_ge h₂⟩

end MIKU.WindowAlgebra
