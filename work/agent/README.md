# Refresh Signal Scout
Capstone-aligned weekly scout: content decline, refresh queue ranking, SEO signal context—not generic news.
Sources: arXiv (cs.IR, cs.LG, cs.CL), Google Search Central blog RSS, Search Engine Land RSS, Hugging Face papers API.
Output: markdown digest (max 5 items) under `work/agent/digests/` plus `index.md`.
Cadence: Monday 08:00 local; platform target Python + GitHub Actions.
Spec: `work/agent/spec.md` — job, tools, guardrails, platform, hours.
Evals: `work/agent/evals.md` — five cases including guardrails.
Instructions: `work/agent/agent_instructions.md` — single block for the agent.
This directory is design-only until the build phase; no scripts or workflow YAML yet.
Reader: capstone author, before weekly work in `work/notebooks/`.
