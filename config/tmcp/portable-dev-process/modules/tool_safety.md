# Module: Tool Safety

Module ID: `@module:tool_safety`

Use the least-powerful tool that can answer the request. Prefer read-only inspection before mutation. Request approval for network, GUI, dependency install, remote, destructive, or outside-repo writes according to the host agent runtime.

Record commands that materially influenced the answer. Do not hide command failures.

