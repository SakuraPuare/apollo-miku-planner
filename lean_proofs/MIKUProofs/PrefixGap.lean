import Mathlib

namespace MIKU.PrefixGap

def prefixMax (seed : ℚ) : List ℚ → List ℚ
  | [] => []
  | x :: xs =>
      let m := max seed x
      m :: prefixMax m xs

theorem prefixMax_length (seed : ℚ) (xs : List ℚ) :
    (prefixMax seed xs).length = xs.length := by
  induction xs generalizing seed with
  | nil => rfl
  | cons x xs ih => simp [prefixMax, ih]

theorem prefixMax_head_ge (seed x : ℚ) (xs : List ℚ) :
    x ≤ (prefixMax seed (x :: xs)).head! := by
  simp [prefixMax]

theorem prefixMax_all_ge_seed (seed : ℚ) (xs : List ℚ) :
    ∀ y ∈ prefixMax seed xs, seed ≤ y := by
  induction xs generalizing seed with
  | nil => simp [prefixMax]
  | cons x xs ih =>
      intro y hy
      simp only [prefixMax, List.mem_cons] at hy
      rcases hy with rfl | hy
      · exact le_max_left _ _
      · exact le_trans (le_max_left _ _) (ih (max seed x) y hy)

theorem prefixMax_covers_input (seed : ℚ) (xs : List ℚ) :
    ∀ y ∈ xs, ∃ z ∈ prefixMax seed xs, y ≤ z := by
  induction xs generalizing seed with
  | nil => simp
  | cons x xs ih =>
      intro y hy
      simp only [List.mem_cons] at hy
      rcases hy with hxy | hy
      · subst y
        exact ⟨max seed x, by simp [prefixMax], le_max_right _ _⟩
      · obtain ⟨z, hz, hyz⟩ := ih (max seed x) y hy
        exact ⟨z, by simp [prefixMax, hz], hyz⟩

def gap (lower upper : ℚ) : ℚ := upper - lower

theorem gap_monotone_upper (lower upper₁ upper₂ : ℚ)
    (h : upper₁ ≤ upper₂) : gap lower upper₁ ≤ gap lower upper₂ := by
  dsimp [gap]
  linarith

theorem gap_antitone_lower (lower₁ lower₂ upper : ℚ)
    (h : lower₁ ≤ lower₂) : gap lower₂ upper ≤ gap lower₁ upper := by
  dsimp [gap]
  linarith

end MIKU.PrefixGap
