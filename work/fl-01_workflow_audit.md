## Section 1 — Workflow audit table

| Task | Classification | One-line rationale |
|---|---|---|
| Debugging pandas / scikit-learn errors in internship notebooks | Collaborate with AI | AI proposes the fix fast, but I have to name the root cause myself or I hit the same error next week. |
| Writing commit messages and PR descriptions | Delegate to AI with review | AI drafts from the diff; I verify the message matches the actual change before pushing. |
| Reading ML research papers and long-form technical posts | Collaborate with AI | AI gives me the map; I interrogate the sections that matter to the capstone and skip the rest. |
| Live note-taking during internship sessions and mentor calls | Just me | The value is in choosing what to write down in real time — that judgment is the note. |
| Drafting LinkedIn posts about internship progress | Delegate to AI with review | AI builds structure from my bullet points; I inject the real story and cut anything that reads generated. |
| Planning the week (deadlines, study blocks, training, internship hours) | Collaborate with AI | AI proposes a schedule from my constraints; I renegotiate around energy and slippage. |
| Building practice sets for coursework and exam prep | Collaborate with AI | AI generates questions at my level; I work them and feed back what I got wrong. |
| Drafting capstone report sections | Collaborate with AI | AI drafts scaffolding and structure; I own every claim and every number. |
| Triaging and replying to routine email | Delegate to AI with review | AI drafts from context; I approve, edit, or discard before anything sends. |
| Generating boilerplate code (imports, plotting setup, file scaffolding) | Fully automate | Low-stakes, easy to spot when it's wrong, and free to regenerate. |
| Meal planning and grocery lists around a fixed budget | Delegate to AI with review | AI generates the plan against constraints; I adjust for taste and what's actually in the kitchen. |
| Responding to mentor feedback on my work | Just me | Relationship-driven — the reply needs my voice and my judgment, not a draft. |
| Brainstorming capstone angles and experiment ideas | Collaborate with AI | AI pushes breadth fast; I decide where to go deep. |
| Weekly internship reflection write-up | Collaborate with AI | AI supplies the structure and the prompts; I write the substance. |
| Running schedule and training log | Just me | Physical habit — tool-driven accountability here is noise, not signal. |

## Section 2 — Three target tasks (for FL-02 through FL-04)

**Target A — Drafting LinkedIn posts about internship progress**
Why this one: highest-leverage compounding task — every post is a permanent portfolio artifact a recruiter can find.
Done well means:
- Published within 48 hours of the milestone it documents.
- At least 120 words.
- Contains exactly one concrete artifact or number pulled from the work.
- Passes a read-aloud check: would I say this sentence out loud to a hiring manager?
- No AI cadence — no triple-clause lists, no em-dash padding, no "in today's landscape."

**Target B — Drafting capstone report sections**
Why this one: the single largest deliverable and the first thing a hiring manager will actually read.
Done well means:
- Drafted within 90 minutes of starting the section.
- Every claim carries a number sourced from a notebook in the repo.
- Language passes a "no proves / no causes / no guarantees" check.
- Each section ends with one explicit limitation sentence.
- Section can be skimmed in under two minutes and still land the point.

**Target C — Debugging pandas / scikit-learn errors in internship notebooks**
Why this one: recurring tax on every ML session — compounding small savings here is what buys the hours for A and B.
Done well means:
- Root cause named in one sentence before any code is changed.
- Fix committed with a message that states the cause, not just the change.
- Same error class does not recur within the same week.
- No fix accepted that I cannot explain out loud.

## Section 3 — Claude Project setup

**FlyRank ML Internship — Capstone Build** is a Claude Project whose purpose is a persistent working context for the internship so every session starts from the same goals, tone, and constraints.

```
Who I am
ML intern at FlyRank (Aug–Oct 2026), building a capstone on SEO content-refresh
prioritisation. CS background; comfortable in Python, pandas, scikit-learn.
Working across Colab notebooks and a public GitHub repo. Also a student and a
side-project builder.

Tone
Direct. No filler, no preamble, no "Great question." Short paragraphs and bullets
over walls of text. Disagree with me when I'm wrong, and say so plainly. Skip the
encouragement.

Current goals (next 8 weeks)
1. Ship a portfolio-grade capstone repo a hiring manager can read in 10 minutes.
2. Publish 8-10 LinkedIn posts documenting the build, each anchored to one concrete
   artifact.
3. Finish with a hire-ready ML narrative: what I built, why, and what it shows.

Hard rules
- Never invent numbers. If I ask for a figure you don't have, say so and ask.
- Flag uncertainty explicitly rather than smoothing it over.
- When I ask for a prompt, give me the prompt only — no meta-commentary.
- Prefer honest, modest language over impressive-sounding claims.
```

Evidence: `work/assets/fl-01_claude_project.png` (screenshot added manually — see repo assets)

## Section 4 — Evidence checklist

- [x] Workflow audit table (Section 1) in this document
- [ ] Claude Project screenshot at `work/assets/fl-01_claude_project.png`
- [ ] Claude, ChatGPT, and Anthropic Academy accounts created; enrolled in AI Fluency: Framework & Foundations (first module complete)
