import Mathlib

namespace MIKU.LinearQP

def linForm {n : Nat} (a x : Fin n → ℚ) : ℚ :=
  ∑ i, a i * x i

def halfspace {n : Nat} (a : Fin n → ℚ) (b : ℚ) : Set (Fin n → ℚ) :=
  {x | linForm a x ≤ b}

theorem linForm_combo {n : Nat} (a x y : Fin n → ℚ) (α β : ℚ) :
    linForm a (α • x + β • y) = α * linForm a x + β * linForm a y := by
  dsimp [linForm]
  calc
    (∑ i, a i * (α * x i + β * y i)) =
        ∑ i, (α * (a i * x i) + β * (a i * y i)) := by
          apply Finset.sum_congr rfl
          intro i hi
          ring
    _ = (∑ i, α * (a i * x i)) + (∑ i, β * (a i * y i)) :=
      Finset.sum_add_distrib
    _ = α * (∑ i, a i * x i) + β * (∑ i, a i * y i) := by
      rw [Finset.mul_sum, Finset.mul_sum]

theorem halfspace_convex {n : Nat} (a : Fin n → ℚ) (b : ℚ) :
    Convex ℚ (halfspace a b) := by
  intro x hx y hy α β hα hβ hab
  dsimp [halfspace] at hx hy ⊢
  rw [linForm_combo]
  have hx' := mul_le_mul_of_nonneg_left hx hα
  have hy' := mul_le_mul_of_nonneg_left hy hβ
  calc
    α * linForm a x + β * linForm a y ≤ α * b + β * b := add_le_add hx' hy'
    _ = b := by rw [← add_mul, hab, one_mul]

theorem finite_intersection_convex {n m : Nat}
    (A : Fin m → Fin n → ℚ) (b : Fin m → ℚ) :
    Convex ℚ {x : Fin n → ℚ | ∀ j, linForm (A j) x ≤ b j} := by
  intro x hx y hy α β hα hβ hab
  intro j
  exact (halfspace_convex (A j) (b j)) (hx j) (hy j) hα hβ hab

theorem box_and_linear_convex {n m : Nat}
    (lower upper : Fin n → ℚ) (A : Fin m → Fin n → ℚ) (b : Fin m → ℚ)
    (hlo : ∀ i, lower i ≤ upper i) :
    Convex ℚ {x : Fin n → ℚ |
      (∀ i, lower i ≤ x i ∧ x i ≤ upper i) ∧
      (∀ j, linForm (A j) x ≤ b j)} := by
  have hbox : Convex ℚ {x : Fin n → ℚ | ∀ i, lower i ≤ x i ∧ x i ≤ upper i} := by
    intro x hx y hy α β hα hβ hab
    intro i
    simp only [Pi.add_apply, Pi.smul_apply, smul_eq_mul]
    have hαxlo := mul_nonneg hα (sub_nonneg.mpr (hx i).1)
    have hβylo := mul_nonneg hβ (sub_nonneg.mpr (hy i).1)
    have hαxhi := mul_nonneg hα (sub_nonneg.mpr ((hx i).2))
    have hβyhi := mul_nonneg hβ (sub_nonneg.mpr ((hy i).2))
    constructor
    · have hsumlo : 0 ≤ α * (x i - lower i) + β * (y i - lower i) :=
        add_nonneg hαxlo hβylo
      have heq : α * x i + β * y i = lower i +
          α * (x i - lower i) + β * (y i - lower i) := by
        calc
          α * x i + β * y i = (α + β) * lower i +
              α * (x i - lower i) + β * (y i - lower i) := by ring
          _ = lower i + α * (x i - lower i) + β * (y i - lower i) := by rw [hab]; ring
      rw [heq]
      linarith
    · have hsumhi : 0 ≤ α * (upper i - x i) + β * (upper i - y i) :=
        add_nonneg hαxhi hβyhi
      have heq : α * x i + β * y i +
          α * (upper i - x i) + β * (upper i - y i) = upper i := by
        calc
          α * x i + β * y i + α * (upper i - x i) +
              β * (upper i - y i) = (α + β) * upper i := by ring
          _ = upper i := by rw [hab]; ring
      linarith
  intro x hx y hy α β hα hβ hab
  constructor
  · exact hbox hx.1 hy.1 hα hβ hab
  · exact finite_intersection_convex A b hx.2 hy.2 hα hβ hab

end MIKU.LinearQP
