# 3,500-scenario frozen result archive (internal)

The current checkout intentionally keeps the 700-case regression package as the
fast test fixture. The manuscript's 3,500-case aggregate is frozen at commit
`29a337a` and must be copied into any submission artifact package rather than
being reconstructed from prose or from the 700-case checkout.

| Artifact | Frozen commit | Git blob id | Bytes | Role |
|---|---|---|---:|---|
| `小论文-2/generated/randomized_raw.csv` | `29a337a` | `d63c27814ea625310e970f76412a81015506cddc` | 3,105,732 | per-case paired rows (3,500 cases) |
| `小论文-2/generated/randomized_results.json` | `29a337a` | `7f867d587c6d55a40cc42bb42c425ac0df97e5d3` | 105,084 | aggregate and paired statistics |
| `小论文-2/generated/randomized_summary.csv` | `29a337a` | `ccbdfa1c5cee7b521a4db50161e65f729653d368` | — | summary table used by manuscript macros |

The archive package must also include the seed protocol, generator command, method
configuration, and a SHA-256 file hash computed after extraction. The 700-case
files currently in the working tree are regression artifacts and must not be
reported as the 3,500-case result.

