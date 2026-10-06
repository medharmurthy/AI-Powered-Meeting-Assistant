Find the action items.

A TASK is work someone committed to ("I'll do X"), was asked to do and accepted, or that the group clearly agreed must be done.
Owner: set only when a person is named as responsible (addressed by name and accepted, or named as taking it). Never infer an owner from role or seniority. If a speaker says "I'll do it" and no name is available, owner is null. 
Deadline: copy the words used ("by Thursday", "before the audit on the 15th"). Do not compute calendar dates. If none was said, null.
NOT a task: an idea, "maybe someone could", "if you have time", "we'll see". Put those in possible_tasks.

Return {"actions":[{"task","owner","deadline","segment_ids","quote"}],"possible_tasks":[{"text","segment_ids"}]}.
task: start with a verb, say what is to be done. quote: short exact quote from a cited line, or null.

Examples
"Dan, can you write the module?" "Yes, I'll have it done by Thursday." -> task owner "Dan", deadline "by Thursday".
"Someone has to rotate the credentials before the audit on the 15th." (nobody volunteers) -> task, owner null, deadline "before the audit on the 15th".
"Maybe Dan could look at the dashboards if he has time." "We'll see." -> possible_tasks, not an action.
