# Apollo 11.0 build attempt (internal)

## Environment

- AEM environment: `11.0.0_pkg`
- Image: `registry.baidubce.com/apollo/apollo-env-gpu:11.0`
- Container: `apollo_neo_dev_11.0.0_pkg`
- Workspace: `/apollo_workspace` mapped to `/home/kent/core-11.0`
- Bazel: 5.2.0
- Apollo source commit: `57460908954e3188f640a813d26180e862d62a5f`

## Command

```text
docker exec -u kent apollo_neo_dev_11.0.0_pkg bash -lc \
  'cd /apollo_workspace && bazel --bazelrc=/dev/null build \
   //modules/planning/planning_component:libplanning_component.so \
   --noshow_progress --verbose_failures'
```

The `bazel-extend-tools` directory is present inside the 11.0 image. The build
analyzed 127 packages and 51,641 targets, then failed while compiling
`modules/planning/planning_component/navi_planning.cc`:

```text
fatal error: third_party/var/bvar/bvar.h: No such file or directory
```

The failure is therefore a concrete dependency/source-overlay failure, not a
successful native build. No generated shared library or new runtime replay is
used in the manuscript. The exact command and error are retained so the build
can be resumed after the missing bvar source/package is restored.

