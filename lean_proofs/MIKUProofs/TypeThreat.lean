import Mathlib

namespace MIKU.TypeThreat

inductive ObjectType
  | ped | bike | vehicle | unknownMovable | static | cone
  deriving DecidableEq

def typeScore : ObjectType → ℚ
  | .ped => 1
  | .bike => 1
  | .vehicle => 7 / 10
  | .unknownMovable => 1 / 2
  | .static => 3 / 10
  | .cone => 3 / 20

theorem typeScore_bounds (k : ObjectType) :
    0 ≤ typeScore k ∧ typeScore k ≤ 1 := by
  cases k <;> norm_num [typeScore]

theorem typeScore_ped_max (k : ObjectType) : typeScore k ≤ typeScore .ped := by
  cases k <;> norm_num [typeScore]

end MIKU.TypeThreat
