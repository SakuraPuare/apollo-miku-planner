import Mathlib

namespace MIKU.LayeredSearch

structure Band where
  label : Nat
  centre : ℚ
  width : ℚ
  deriving DecidableEq

def paths : List (List Band) → List (List Band)
  | [] => [[]]
  | layer :: rest =>
      List.flatMap (fun b => (paths rest).map (List.cons b)) layer

theorem paths_nil : paths [] = [[]] := rfl

theorem paths_member_length :
    ∀ {layers : List (List Band)} {choice : List Band},
      choice ∈ paths layers → choice.length = layers.length := by
  intro layers
  induction layers with
  | nil =>
      intro choice h
      simp [paths] at h
      simpa using h
  | cons layer rest ih =>
      intro choice h
      simp only [paths] at h
      rcases List.mem_flatMap.mp h with ⟨b, hb, hmap⟩
      rcases List.mem_map.mp hmap with ⟨tail, htail, heq⟩
      have hchoice : choice = b :: tail := heq.symm
      subst choice
      simp only [List.length_cons]
      have ht := ih htail
      omega

theorem paths_nonempty_of_nonempty_layers :
    ∀ layers : List (List Band),
      (∀ layer ∈ layers, layer ≠ []) → ∃ p, p ∈ paths layers := by
  intro layers
  induction layers with
  | nil =>
      intro _
      exact ⟨[], by simp [paths]⟩
  | cons layer rest ih =>
      intro hnonempty
      have hl : layer ≠ [] := hnonempty layer (by simp)
      have hrest : ∀ l ∈ rest, l ≠ [] := by
        intro l hlm
        exact hnonempty l (by simp [hlm])
      obtain ⟨b, hb⟩ := List.exists_mem_of_ne_nil layer hl
      obtain ⟨tail, htail⟩ := ih hrest
      refine ⟨b :: tail, ?_⟩
      simp only [paths, List.mem_flatMap]
      refine ⟨b, hb, ?_⟩
      exact List.mem_map.mpr ⟨tail, htail, rfl⟩

theorem paths_empty_layer (layer : List Band) (rest : List (List Band))
    (h : layer = []) : paths (layer :: rest) = [] := by
  subst layer
  simp [paths]

end MIKU.LayeredSearch
