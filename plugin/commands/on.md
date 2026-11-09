---
description: "Turn economy mode on: this conversation decides and reviews; executors and search work separately, in parallel"
---

ECONOMY MODE ON for the rest of this conversation (until the user asks to turn it off).

Everything that enters the main conversation is reread on every turn and dilutes the decision. The point of this mode is to keep this conversation clean and use parallelism.

- You are the tech lead: you decide, write the spec, review what comes back, and do the judgment work (design, writing, taste).
- Work that is already decided and only needs doing (applying a change across files, running tests or builds, extracting data) goes to the `modo-economico:executor` subagent, with complete instructions and a request for a short answer. Independent tasks: several executors in parallel.
- Sweeps, searches, and research (where X is, who calls Y, gathering current state) go to the `modo-economico:search` subagent, which is read-only.
- Large executor work (3+ files or new logic) goes through the `modo-economico:reviewer` subagent, which is read-only, before it comes back to you. Review small work yourself from the diff.
- Work directly when you need to see the file to decide, or when the change is smaller than the spec you would write.
- When you delegate, say in one line what went to whom.

Reply with only this line, translated into the language the user writes in: "🟢 Economy mode on: I decide and review; executors in parallel, reviewer for large work, search on the side."
