#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
apollo_root="${1:-${project_root}/../core-11.0}"

required=(
  "modules/planning/planning_base/testdata/garage_test/1_chassis.pb.txt"
  "modules/planning/planning_base/testdata/garage_test/1_localization.pb.txt"
  "modules/planning/planning_base/testdata/garage_test/1_prediction.pb.txt"
  "modules/planning/planning_base/testdata/garage_test/garage_routing.pb.txt"
  "modules/planning/planners/public_road/conf/planner_config.pb.txt"
  "modules/planning/tasks/speed_bounds_decider/proto/speed_bounds_decider.proto"
  "modules/planning/planning_base/proto/st_drivable_boundary.proto"
  ".aem/envroot/opt/apollo/neo/src/modules/common/data/vehicle_param.pb.txt"
  ".aem/envroot/opt/apollo/neo/src/modules/common/vehicle_model/conf/vehicle_model_config.pb.txt"
  "data/map_data/sunnyvale_big_loop/sim_map.bin"
  "data/map_data/sunnyvale_big_loop/base_map.bin"
  "data/map_data/sunnyvale_big_loop/routing_map.bin"
  "data/map_data/sunnyvale_big_loop/map.json"
  "data/map_data/sunnyvale_big_loop/default_end_way_point.txt"
  "dumps/planning.dag_external_command_process.dag.data"
  "dumps/planning.dag_external_command_process.dag.latency.data"
  "dumps/bvar.dreamview_plus.data"
  "dumps/bvar.dreamview_plus.latency.data"
)

missing=0
for relative in "${required[@]}"; do
  if [[ ! -f "${apollo_root}/${relative}" ]]; then
    echo "MISSING ${relative}" >&2
    missing=1
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  exit 1
fi

echo "Apollo fixture/runtime asset paths verified: ${#required[@]} files"
