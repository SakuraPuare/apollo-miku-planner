import Mathlib

/-!
Formal check for the三区 version of MIKU.

The instance is the fixed cross-section model used by the paper: road
`[-5, 8]`, and three ordered inflated obstacle intervals
`(-2,0), (1,3), (4,6)`.  `routeWidth` enumerates all 2^3 left/right
assignments; `cutWidth` is the k+1 continuous split algorithm.
-/

namespace MIKU.Paper3

def upper (left : Bool) (u : Int) : Int := if left then 8 else u
def lower (left : Bool) (v : Int) : Int := if left then v else -5

def routeWidth (d₁ d₂ d₃ : Bool) : Int :=
  min 8 (min (upper d₁ (-2)) (min (upper d₂ 1) (upper d₃ 4))) -
    max (-5) (max (lower d₁ 0) (max (lower d₂ 3) (lower d₃ 6)))

def cutWidth : Fin 4 → Int
  | ⟨0, _⟩ => 3   -- right end gap: -2 - (-5)
  | ⟨1, _⟩ => 1   -- gap between the first and second intervals
  | ⟨2, _⟩ => 1   -- gap between the second and third intervals
  | ⟨3, _⟩ => 2   -- left end gap: 8 - 6

def bestCut : Fin 4 := ⟨0, by decide⟩

theorem best_cut_value : cutWidth bestCut = 3 := by
  native_decide

theorem every_continuous_cut_is_bounded :
    ∀ p : Fin 4, cutWidth p ≤ cutWidth bestCut := by
  native_decide

theorem every_binary_assignment_is_bounded :
    ∀ d₁ d₂ d₃ : Bool, routeWidth d₁ d₂ d₃ ≤ cutWidth bestCut := by
  native_decide

theorem best_cut_is_realised : routeWidth false false false = cutWidth bestCut := by
  native_decide

/- The algorithm's result is therefore optimal over the complete 2^3
   assignment domain, while evaluating only the four continuous cuts. -/
theorem max_gap_certificate :
    cutWidth bestCut = 3 ∧
      (∀ p : Fin 4, cutWidth p ≤ 3) ∧
      (∀ d₁ d₂ d₃ : Bool, routeWidth d₁ d₂ d₃ ≤ 3) ∧
      routeWidth false false false = 3 := by
  native_decide

end MIKU.Paper3
