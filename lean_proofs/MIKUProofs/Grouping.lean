import Mathlib

namespace MIKU.Grouping

structure Interval where
  start : ℕ
  finish : ℕ
  ordered : start ≤ finish

def flatten (groups : List (List Interval)) : List Interval := List.flatten groups

def scanFrom (frontier : ℕ) (current : List Interval) : List Interval → List (List Interval)
  | [] => [current]
  | x :: xs =>
      if x.start > frontier then
        current :: scanFrom x.finish [x] xs
      else
        scanFrom (max frontier x.finish) (current ++ [x]) xs

def scanGroups (xs : List Interval) : List (List Interval) :=
  match xs with
  | [] => []
  | x :: rest => scanFrom x.finish [x] rest

theorem scanFrom_flatten
    (frontier : ℕ) (current rest : List Interval) :
    flatten (scanFrom frontier current rest) = current ++ rest := by
  induction rest generalizing frontier current with
  | nil => simp [scanFrom, flatten]
  | cons x xs ih =>
      by_cases h : x.start > frontier
      · simp [scanFrom, h, flatten]
        change flatten (scanFrom x.finish [x] xs) = x :: xs
        rw [ih]
        simp
      · simp [scanFrom, h, flatten]
        change flatten (scanFrom (max frontier x.finish) (current ++ [x]) xs) =
          current ++ x :: xs
        rw [ih]
        simp [List.append_assoc]

theorem scanGroups_flatten (xs : List Interval) :
    flatten (scanGroups xs) = xs := by
  cases xs with
  | nil => rfl
  | cons x rest =>
      simpa [scanGroups] using scanFrom_flatten x.finish [x] rest

theorem scanFrom_nonempty
    (frontier : ℕ) (current : List Interval) (rest : List Interval)
    (hcurrent : current ≠ []) :
    ∀ group ∈ scanFrom frontier current rest, group ≠ [] := by
  induction rest generalizing frontier current with
  | nil =>
      intro group hg
      simp [scanFrom] at hg
      simpa [hg] using hcurrent
  | cons x xs ih =>
      by_cases h : x.start > frontier
      · intro group hg
        simp [scanFrom, h] at hg
        rcases hg with rfl | hg
        · exact hcurrent
        · exact ih (frontier := x.finish) (current := [x]) (by simp) group hg
      · intro group hg
        simp [scanFrom, h] at hg
        exact ih (frontier := max frontier x.finish)
          (current := current ++ [x]) (by simp) group hg

theorem scanGroups_nonempty (xs : List Interval) :
    ∀ group ∈ scanGroups xs, group ≠ [] := by
  cases xs with
  | nil => simp [scanGroups]
  | cons x rest =>
      exact scanFrom_nonempty x.finish [x] rest (by simp)

theorem scanGroups_preserves_membership (xs : List Interval) :
    ∀ x, x ∈ xs ↔ x ∈ flatten (scanGroups xs) := by
  intro x
  rw [scanGroups_flatten]

theorem new_group_boundary_safe
    (frontier next : ℕ) (current rest : List Interval)
    (hbound : ∀ i ∈ current, i.finish ≤ frontier)
    (hnext : frontier < next) :
    (∀ i ∈ current, i.finish < next) ∧
      (scanFrom frontier current (⟨next, next, le_rfl⟩ :: rest) =
        current :: scanFrom next [⟨next, next, le_rfl⟩] rest) := by
  constructor
  · intro i hi
    exact lt_of_le_of_lt (hbound i hi) hnext
  · simp [scanFrom, hnext]

end MIKU.Grouping
