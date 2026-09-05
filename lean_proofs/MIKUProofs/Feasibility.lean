import Mathlib

namespace MIKU.Feasibility

def roadPoint (lo hi x : ℚ) : Prop := lo ≤ x ∧ x ≤ hi

def forbidden (u v x : ℚ) : Prop := u ≤ x ∧ x ≤ v

def outside (u v x : ℚ) : Prop := x < u ∨ v < x

theorem full_projection_cover_is_infeasible
    (lo hi u v : ℚ)
    (hcover : ∀ x, roadPoint lo hi x → forbidden u v x) :
    ¬ ∃ x, roadPoint lo hi x ∧ outside u v x := by
  rintro ⟨x, hxroad, hxout⟩
  rcases hxout with hx | hx
  · have hforb := hcover x hxroad
    linarith [hforb.1]
  · have hforb := hcover x hxroad
    linarith [hforb.2]

theorem corridor_restores_feasibility
    {α : Type} (original : α → Prop)
    (x : α) (hx : original x) :
    ∃ y : α, original y := by
  exact ⟨x, hx⟩

theorem corridor_subset_safe
    (lo hi l u : ℚ) (hlo : lo ≤ l) (hhi : u ≤ hi) :
    ∀ y, l ≤ y → y ≤ u → lo ≤ y ∧ y ≤ hi := by
  intro y hyl hyu
  constructor <;> linarith

end MIKU.Feasibility
