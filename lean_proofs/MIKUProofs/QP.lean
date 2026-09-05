import Mathlib

namespace MIKU.QP

def inBox {n : Nat} (lo hi x : Fin n → ℚ) : Prop :=
  ∀ i, lo i ≤ x i ∧ x i ≤ hi i

theorem box_convex {n : Nat} (lo hi x y : Fin n → ℚ) (w : ℚ)
    (hx : inBox lo hi x) (hy : inBox lo hi y)
    (hw : 0 ≤ w) (hw' : w ≤ 1) :
    inBox lo hi (fun i => w * x i + (1 - w) * y i) := by
  intro i
  have hlow : lo i ≤ w * x i + (1 - w) * y i := by
    nlinarith [mul_nonneg hw (sub_nonneg.mpr ((hx i).1)),
      mul_nonneg (sub_nonneg.mpr hw') (sub_nonneg.mpr ((hy i).1))]
  have hupp : w * x i + (1 - w) * y i ≤ hi i := by
    nlinarith [mul_nonneg hw (sub_nonneg.mpr ((hx i).2)),
      mul_nonneg (sub_nonneg.mpr hw') (sub_nonneg.mpr ((hy i).2))]
  exact ⟨hlow, hupp⟩

theorem box_nonempty {n : Nat} (lo hi : Fin n → ℚ)
    (h : ∀ i, lo i ≤ hi i) :
    ∃ x : Fin n → ℚ, inBox lo hi x := by
  classical
  let x : Fin n → ℚ := fun i => (lo i + hi i) / 2
  refine ⟨x, ?_⟩
  intro i
  dsimp [x]
  constructor <;> linarith [h i]

def objective (target x : ℚ) : ℚ := (x - target)^2

theorem objective_nonnegative (target x : ℚ) : 0 ≤ objective target x := by
  dsimp [objective]
  positivity

theorem target_is_global_minimizer (target x : ℚ) :
    objective target target ≤ objective target x := by
  rw [show objective target target = 0 by simp [objective]]
  exact objective_nonnegative target x

theorem objective_strict_minimizer (target x : ℚ)
    (h : objective target x = objective target target) : x = target := by
  dsimp [objective] at h
  nlinarith [sq_nonneg (x - target)]

theorem quadratic_convex_on_box
    (target x y w : ℚ)
    (hw : 0 ≤ w) (hw' : w ≤ 1) :
    objective target (w * x + (1 - w) * y) ≤
      w * objective target x + (1 - w) * objective target y := by
  dsimp [objective]
  have hww : 0 ≤ w * (1 - w) := mul_nonneg hw (by linarith)
  nlinarith [mul_nonneg hww (sq_nonneg (x - y))]

theorem fixed_homotopy_box_feasible
    (lo hi target : ℚ) (ht : lo ≤ target) (ht' : target ≤ hi) :
    ∃ x, lo ≤ x ∧ x ≤ hi ∧ objective target x = objective target target := by
  exact ⟨target, ht, ht', rfl⟩

end MIKU.QP
