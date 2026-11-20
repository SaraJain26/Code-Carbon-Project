# Uploaded code execution

Code-Carbon runs uploaded Python files through static parsing, analysis, and AST transformation by default. It does not execute uploaded code unless the server operator explicitly sets `ENABLE_EXECUTION=true` (also accepts `1`, `yes`, `on`, or `enabled`). The default is `false`.

When execution is disabled, the API returns `execution_status: "not_executed"` and the dashboard displays **Not executed (static analysis only)**. Project analysis is also static-only.

When opted in, measurement uses `SandboxedRuntimeExecutor`. Its Python audit hooks and socket/process-spawn blocks are defense-in-depth only. They are not a security boundary or an OS isolation mechanism and must not be treated as safe containment for hostile code. Do not enable execution for untrusted uploads in a shared or production environment without a separate OS/container isolation layer.
