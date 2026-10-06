Find the decisions, and separately the things discussed but not settled.

A DECISION is something the group explicitly agreed, confirmed or settled ("let's go with", "agreed", "it's decided", a proposal followed by confirmation or no objection plus acknowledgement). Negative decisions count ("we will not upgrade this quarter").
NOT a decision: a suggestion, an idea, a question, a preference of one person, something put off ("let's revisit next sprint"), or a statement of fact.

Return {"decisions":[{"text","rationale","segment_ids","quote"}],"unresolved":[{"kind","text","segment_ids"}]}.
- rationale: the reason given in the meeting, or null.
- quote: a short exact quote (at most 20 words) from a cited line, or null.
- unresolved.kind: "proposal" (suggested, not agreed), "question" (asked, not answered), or "deferred" (explicitly postponed).

Examples
"Any objections to Redis?" "None." "Then it's decided: Redis." -> decision.
"I'd suggest moving everything to gRPC." "I don't want to decide that today." -> unresolved, kind "deferred".
