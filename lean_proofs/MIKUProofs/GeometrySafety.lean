import Mathlib

namespace MIKU.GeometrySafety

structure Interval where
  u : ℚ
  v : ℚ
  ordered : u ≤ v

def minFold (seed : ℚ) : List ℚ → ℚ
  | [] => seed
  | x :: xs => min x (minFold seed xs)

def maxFold (seed : ℚ) : List ℚ → ℚ
  | [] => seed
  | x :: xs => max x (maxFold seed xs)

theorem minFold_le_seed (seed : ℚ) (xs : List ℚ) : minFold seed xs ≤ seed := by
  induction xs generalizing seed with
  | nil => exact le_rfl
  | cons x xs ih => exact le_trans (min_le_right _ _) (ih seed)

theorem maxFold_seed_le (seed : ℚ) (xs : List ℚ) : seed ≤ maxFold seed xs := by
  induction xs generalizing seed with
  | nil => exact le_rfl
  | cons x xs ih => exact le_max_of_le_right (ih seed)

theorem minFold_le_mem (seed : ℚ) :
    ∀ {xs : List ℚ} {x : ℚ}, x ∈ xs → minFold seed xs ≤ x := by
  intro xs
  induction xs generalizing seed with
  | nil => intro x hx; simp at hx
  | cons y ys ih =>
      intro x hx
      simp only [List.mem_cons] at hx
      rcases hx with rfl | hx
      · exact min_le_left _ _
      · exact le_trans (min_le_right _ _) (ih seed hx)

theorem maxFold_mem_le (seed : ℚ) :
    ∀ {xs : List ℚ} {x : ℚ}, x ∈ xs → x ≤ maxFold seed xs := by
  intro xs
  induction xs generalizing seed with
  | nil => intro x hx; simp at hx
  | cons y ys ih =>
      intro x hx
      simp only [List.mem_cons] at hx
      rcases hx with rfl | hx
      · exact le_max_left _ _
      · exact le_trans (ih seed hx) (le_max_right _ _)

def upper (roadUpper : ℚ) (xs : List (Interval × Bool)) : ℚ :=
  minFold roadUpper (xs.map (fun p => if p.2 then roadUpper else p.1.u))

def lower (roadLower : ℚ) (xs : List (Interval × Bool)) : ℚ :=
  maxFold roadLower (xs.map (fun p => if p.2 then p.1.v else roadLower))

theorem upper_le_bound
    (roadUpper : ℚ) {xs : List (Interval × Bool)} {p : Interval × Bool}
    (hp : p ∈ xs) : upper roadUpper xs ≤ (if p.2 then roadUpper else p.1.u) := by
  rw [upper]
  apply minFold_le_mem roadUpper
  exact List.mem_map_of_mem hp

theorem bound_le_lower
    (roadLower : ℚ) {xs : List (Interval × Bool)} {p : Interval × Bool}
    (hp : p ∈ xs) : (if p.2 then p.1.v else roadLower) ≤ lower roadLower xs := by
  rw [lower]
  apply maxFold_mem_le roadLower
  exact List.mem_map_of_mem hp

theorem route_band_excludes_open_obstacles
    (roadLower roadUpper x : ℚ)
    {xs : List (Interval × Bool)}
    (hband : lower roadLower xs ≤ x ∧ x ≤ upper roadUpper xs) :
    ∀ p ∈ xs, ¬ (p.1.u < x ∧ x < p.1.v) := by
  intro p hp hcollision
  by_cases hleft : p.2
  · have hlower := bound_le_lower roadLower hp
    simp [hleft] at hlower
    linarith [hband.1, hcollision.2]
  · have hupper := upper_le_bound roadUpper hp
    simp [hleft] at hupper
    linarith [hband.2, hcollision.1]

theorem positive_width_has_point
    (roadLower roadUpper : ℚ)
    (xs : List (Interval × Bool))
    (hwidth : lower roadLower xs < upper roadUpper xs) :
    ∃ x, lower roadLower xs ≤ x ∧ x ≤ upper roadUpper xs := by
  exact ⟨(lower roadLower xs + upper roadUpper xs) / 2, by constructor <;> linarith⟩

end MIKU.GeometrySafety
