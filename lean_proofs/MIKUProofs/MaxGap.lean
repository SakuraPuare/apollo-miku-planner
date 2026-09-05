import Mathlib

namespace MIKU.MaxGap

def values {n : Nat} (gap : Fin (n + 1) → ℚ) : Finset ℚ :=
  Finset.univ.image gap

theorem values_nonempty {n : Nat} (gap : Fin (n + 1) → ℚ) :
    (values gap).Nonempty := by
  classical
  exact ⟨gap 0, Finset.mem_image.mpr ⟨0, Finset.mem_univ _, rfl⟩⟩

def bestValue {n : Nat} (gap : Fin (n + 1) → ℚ) : ℚ :=
  (values gap).max' (values_nonempty gap)

theorem bestValue_upper_bound {n : Nat} (gap : Fin (n + 1) → ℚ)
    (p : Fin (n + 1)) : gap p ≤ bestValue gap := by
  apply Finset.le_max'
  exact Finset.mem_image.mpr ⟨p, Finset.mem_univ _, rfl⟩

theorem bestValue_attained {n : Nat} (gap : Fin (n + 1) → ℚ) :
    ∃ p : Fin (n + 1), gap p = bestValue gap := by
  classical
  have hm := Finset.max'_mem (values gap) (values_nonempty gap)
  rcases Finset.mem_image.mp hm with ⟨p, hp, hpg⟩
  exact ⟨p, hpg⟩

theorem scan_is_optimal {n : Nat} (gap : Fin (n + 1) → ℚ)
    {p : Fin (n + 1)} (hp : gap p = bestValue gap) :
    ∀ q : Fin (n + 1), gap q ≤ gap p := by
  intro q
  rw [hp]
  exact bestValue_upper_bound gap q

end MIKU.MaxGap
