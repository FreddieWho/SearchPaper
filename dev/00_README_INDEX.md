# SearchPaper Roadmap Document Set

This document set is designed to be submitted together to an agent `/goal` workflow. It is intentionally compact: one main roadmap, one executable goal prompt, one degradation/anti-loop policy, and one agent integration/skill specification.

## Files

1. `01_SearchPaper_Roadmap.md`
   - The main product and engineering roadmap.
   - Defines project scope, architecture, schema, source strategy, phased milestones, acceptance criteria, and non-goals.
   - Use this as the primary planning reference.

2. `02_Goal_Mode_Execution_Prompt.md`
   - A ready-to-submit `/goal` prompt.
   - Converts the roadmap into concrete implementation instructions.
   - Includes priorities, stopping rules, deliverables, and acceptance checks.

3. `03_Degradation_and_AntiLoop_Policy.md`
   - The most important risk-control document.
   - Defines multi-source API fallback, degraded-source handling, retry budgets, failure classification, and areas where agents tend to loop.
   - Use this to prevent `/goal` from wasting effort on unreliable public APIs or bikeshedding.

4. `04_Agent_Integration_and_Skill_Spec.md`
   - Defines the OpenCode/Codex/Claude integration strategy.
   - Specifies CLI-first, MCP adapter, skill behavior, installer contract, and minimal agent configuration rules.
   - Use this to make SearchPaper usable across major coding agents without tying the project to one wrapper.

## Execution Scope Clarification

`02_Goal_Mode_Execution_Prompt.md` is not a standalone substitute for the roadmap. It explicitly references the other documents and should be submitted last. The intended `/goal` scope is:

- complete all v0.2 foundation requirements;
- complete the feasible core v0.3 biomedical-signal and agent-hardening requirements;
- add only low-risk v0.4 extension hooks such as capabilities, export interfaces, and integration scaffolds;
- do not attempt v0.5 full-text/PDF parsing.

The degradation policy is binding. A source adapter may be marked degraded when live public APIs are unreliable, but the adapter contract, fixture-backed tests, source status, and documentation should still be implemented.

## Primary Design Principle

SearchPaper is not a research agent and not an evidence-evaluation engine. It is a literature-first infrastructure layer for agent-assisted research:

- search literature across open/free sources;
- normalize paper identifiers;
- merge duplicate records conservatively;
- preserve provenance and query trace;
- expose results through CLI, MCP, and agent skills;
- provide literature-backed signals without making scientific conclusions.

## Recommended Submission Order

Submit the files in this order:

1. `01_SearchPaper_Roadmap.md`
2. `03_Degradation_and_AntiLoop_Policy.md`
3. `04_Agent_Integration_and_Skill_Spec.md`
4. `02_Goal_Mode_Execution_Prompt.md`

The goal prompt should be submitted last because it references the roadmap and policies.
