#pragma once

#include <memory>
#include "cyber/plugin_manager/plugin_manager.h"

/* 添加了相应的头文件*/
#include "modules/common/status/status.h"
#include "modules/planning/planning_interface_base/traffic_rules_base/traffic_rule.h"

namespace apollo {
namespace planning {

class RegionSpeedLimit : public TrafficRule {
    /* 声明成员函数*/
public:
    bool Init(const std::string& name, const std::shared_ptr<DependencyInjector>& injector) override;
    virtual ~RegionSpeedLimit() = default;

    common::Status ApplyRule(Frame* const frame, ReferenceLineInfo* const reference_line_info);

    void Reset() override {}
};

CYBER_PLUGIN_MANAGER_REGISTER_PLUGIN(apollo::planning::RegionSpeedLimit, TrafficRule)

}  // namespace planning
}  // namespace apollo
