# AIOS Field Pressure Gate

Generated: 2026-07-01T18:34:04.206291Z
Source DB: `/Users/jakyeamos/projects/AIOS/data/aios.db`
DB copy: `/var/folders/r7/b6pc8f3d7mjgkqx_wps2p52r0000gn/T/aios-field-pressure-tmz8xmti/aios-field-pressure.db`
Overall: PASS
Score: 100/100

| Concern | Status | Summary |
| --- | --- | --- |
| daily-usage-pressure / daily-usage-pressure:route-volume | pass | 12/12 simulated daily objectives routed as expected. |
| daily-usage-pressure / daily-usage-pressure:managed-run:run-5011dd56-92ac-4a4d-9c26-d1dd5187bc0c | pass | Managed runtime completed. |
| daily-usage-pressure / daily-usage-pressure:managed-run:run-a4cdabf1-462e-493e-8be8-acdaa80df39f | pass | Managed runtime completed. |
| daily-usage-pressure / daily-usage-pressure:managed-run:run-aa350907-56e2-411d-8881-72204d6b0de7 | pass | Managed runtime completed. |
| daily-usage-pressure / daily-usage-pressure:artifact-volume | pass | 3/3 managed runs produced closeout artifacts. |
| operator-ux / operator-ux:file-coverage | pass | Operator route/component/server surfaces exist. |
| operator-ux / operator-ux:lint-typecheck | pass | Operator UI lint/typecheck exits cleanly. |
| operator-ux / operator-ux:surface-probes | pass | Operator surfaces expose searchable, drill-downable run state. |
| learning-value / learning-value:context-loop-replay | pass | Second-brain/context-loop replay produced a learning candidate. |
| learning-value / learning-value:session-save-writebacks | pass | Repeated synthetic session saves produced governed memory and skillification proposals. |
| failure-recovery / failure-recovery:ambiguous-objective | pass | Ambiguous objective blocks instead of guessing. |
| failure-recovery / failure-recovery:invalid-project | pass | Unknown explicit project fails cleanly. |
| failure-recovery / failure-recovery:missing-run-replay | pass | Daily-flow missing-run replay degrades to explicit missing provenance. |
| failure-recovery / failure-recovery:stale-schema-replay | pass | Daily-flow stale-schema replay reports missing evaluation evidence without crashing. |
| failure-recovery / failure-recovery:missing-managed-run | pass | Managed runtime missing-run preflight fails cleanly without traceback. |
| artifact-hygiene / artifact-hygiene:runtime-logs | pass | Managed runtime log directories are ignored by git. |
| artifact-hygiene / artifact-hygiene:dirty-tree-classification | pass | Dirty tree is classified into source changes and ignored runtime artifacts. |

## Interpretation

- Daily usage pressure is simulated through route volume plus managed-runtime subset execution.
- Operator UX is tested through route/component presence, UI lint/typecheck, and executable drill-downable JSON surfaces.
- Artifact hygiene is tested by requiring managed-runtime log directories to be git-ignored and classifying dirty-tree state into source changes versus ignored runtime artifacts.
- Learning value is simulated with context-loop replay and repeated session-save writeback proposals.
- Failure recovery is tested with ambiguous objectives, invalid projects, missing run replay, stale schema replay, and missing managed-run preflight.
