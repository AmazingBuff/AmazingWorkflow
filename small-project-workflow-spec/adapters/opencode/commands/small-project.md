---
description: Start or continue the gated small-project delivery workflow
agent: small-project-orchestrator
subtask: false
---

Run the small-project workflow as the primary orchestrator. Treat the following
as the user's request or continuation context and preserve it verbatim where it
is needed for requirements and confirmation:

$ARGUMENTS

Load the workflow authority, establish or recover the iteration state, and
route only the next permitted phase. Do not bypass solution confirmation or
explicit user acceptance.
