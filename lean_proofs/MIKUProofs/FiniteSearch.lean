import Mathlib

namespace MIKU.FiniteSearch

structure Candidate where
  spatial : Nat
  temporal : Nat
  objective : Nat
deriving DecidableEq

def choose (a b : Candidate) : Candidate :=
  if a.objective ≤ b.objective then a else b

theorem choose_mem (a b : Candidate) : choose a b = a ∨ choose a b = b := by
  by_cases h : a.objective ≤ b.objective <;> simp [choose, h]

theorem choose_le_left (a b : Candidate) :
    (choose a b).objective ≤ a.objective := by
  by_cases h : a.objective ≤ b.objective
  · simp [choose, h]
  · simp [choose, h]
    exact Nat.le_of_lt (Nat.lt_of_not_ge h)

theorem choose_le_right (a b : Candidate) :
    (choose a b).objective ≤ b.objective := by
  by_cases h : a.objective ≤ b.objective
  · simp [choose, h]
  · simp [choose, h]

def best (seed : Candidate) : List Candidate → Candidate
  | [] => seed
  | x :: xs => best (choose seed x) xs

theorem best_le_seed (seed : Candidate) :
    ∀ xs : List Candidate, (best seed xs).objective ≤ seed.objective := by
  intro xs
  induction xs generalizing seed with
  | nil => simp [best]
  | cons x xs ih =>
      exact le_trans (ih (choose seed x)) (choose_le_left seed x)

theorem best_le_head (seed x : Candidate) (xs : List Candidate) :
    (best (choose seed x) xs).objective ≤ x.objective := by
  exact le_trans (best_le_seed (choose seed x) xs) (choose_le_right seed x)

theorem best_le_member (seed : Candidate) :
    ∀ {xs : List Candidate} {x : Candidate}, x ∈ xs →
      (best seed xs).objective ≤ x.objective := by
  intro xs
  induction xs generalizing seed with
  | nil => intro x hx; simp at hx
  | cons y ys ih =>
      intro x hx
      simp only [best]
      simp only [List.mem_cons] at hx
      rcases hx with rfl | hx
      · exact best_le_head _ _ _
      · exact ih (choose seed y) hx

theorem exhaustive_minimum (seed : Candidate) (xs : List Candidate) :
    ∀ x ∈ seed :: xs, (best seed xs).objective ≤ x.objective := by
  intro x hx
  simp only [List.mem_cons] at hx
  rcases hx with hseed | hx
  · subst x
    exact best_le_seed seed xs
  · exact best_le_member seed hx

theorem selected_candidate_is_in_domain (seed : Candidate) (xs : List Candidate) :
    best seed xs = seed ∨ best seed xs ∈ xs := by
  induction xs generalizing seed with
  | nil => simp [best]
  | cons x xs ih =>
      have hrec := ih (choose seed x)
      rcases hrec with hrec | hrec
      · rcases choose_mem seed x with hchoose | hchoose
        · left; simpa [best, hchoose] using hrec
        · right
          have heq : best seed (x :: xs) = x := by
            simpa [best, hchoose] using hrec
          rw [heq]
          simp
      · right
        simpa [best] using (List.mem_cons_of_mem x hrec)

end MIKU.FiniteSearch
