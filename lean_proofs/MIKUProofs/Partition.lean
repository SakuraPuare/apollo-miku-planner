import Mathlib

namespace MIKU.Partition

/-!
The key combinatorial reduction used by the lateral-band enumerator.  We do
not identify a Python float with a real number here: the statement is an
exact rational specification of the sorted interval geometry.
-/

def leftOf (u v x : ℚ) : Prop := v ≤ x
def rightOf (u v x : ℚ) : Prop := x ≤ u

theorem no_right_then_left
    {n : Nat} (u v : Fin n → ℚ) (x : ℚ) (dir : Fin n → Bool)
    (hordered : ∀ ⦃i j : Fin n⦄, i ≤ j → u i ≤ u j)
    (hpositive : ∀ i, u i < v i)
    (hsafe : ∀ i, (dir i = true → leftOf (u i) (v i) x) ∧
      (dir i = false → rightOf (u i) (v i) x)) :
    ∀ ⦃i j : Fin n⦄, i ≤ j → dir i = false → dir j = true → False := by
  intro i j hij hiright hjleft
  have hi := (hsafe i).2 hiright
  have hj := (hsafe j).1 hjleft
  have h_ij := hordered hij
  have hji := hpositive j
  dsimp [rightOf, leftOf] at hi hj
  linarith

theorem prefix_closed
    {n : Nat} (u v : Fin n → ℚ) (x : ℚ) (dir : Fin n → Bool)
    (hordered : ∀ ⦃i j : Fin n⦄, i ≤ j → u i ≤ u j)
    (hpositive : ∀ i, u i < v i)
    (hsafe : ∀ i, (dir i = true → leftOf (u i) (v i) x) ∧
      (dir i = false → rightOf (u i) (v i) x)) :
    ∀ ⦃i j : Fin n⦄, i ≤ j → dir j = true → dir i = true := by
  intro i j hij hj
  by_contra hi
  have hi' : dir i = false := by
    cases h : dir i with
    | false => simpa using h
    | true => exact False.elim (hi h)
  exact no_right_then_left u v x dir hordered hpositive hsafe hij hi' hj

theorem adjacent_direction_change
    {n : Nat} (u v : Fin n → ℚ) (x : ℚ) (dir : Fin n → Bool)
    (hordered : ∀ ⦃i j : Fin n⦄, i ≤ j → u i ≤ u j)
    (hpositive : ∀ i, u i < v i)
    (hsafe : ∀ i, (dir i = true → leftOf (u i) (v i) x) ∧
      (dir i = false → rightOf (u i) (v i) x)) :
    ∀ ⦃i j : Fin n⦄, i ≤ j → dir i = false → dir j = false := by
  intro i j hij hi
  by_contra hj
  have hj' : dir j = true := by
    cases h : dir j with
    | true => simpa using h
    | false => exact False.elim (hj h)
  exact no_right_then_left u v x dir hordered hpositive hsafe hij hi hj'

end MIKU.Partition
