Check these items against the lines cited for each. Answer strictly from the lines.

{% for it in items %}
Item {{ it.id }} ({{ it.kind }}): {{ it.text }}{% if it.owner %} | owner: {{ it.owner }}{% endif %}{% if it.deadline %} | deadline: {{ it.deadline }}{% endif %}
Lines:
{{ it.lines }}
{% endfor %}

For each item return {"id","verdict","owner_stated","deadline_stated"}.
Decision verdicts: "agreed" (the group settled it), "proposal_only" (only suggested or still open), "unsupported".
Task verdicts: "committed", "tentative" (maybe/if time/we'll see), "unsupported".
owner_stated: true only if a person is named as responsible in the lines. deadline_stated: true only if a time limit was spoken.
Return {"results":[...]}.
