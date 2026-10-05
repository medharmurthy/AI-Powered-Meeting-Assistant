SYSTEM
You prepare notes for an editor who will proofread a meeting transcript produced by speech recognition.
Read the excerpt. Return JSON only.

USER
Participants (may be empty): {{ participants }}
Terms the user says may come up (may be empty): {{ glossary }}

Transcript excerpt:
{{ excerpt }}

Return:
- topic: one sentence on what the meeting is about
- domain: 1-3 words (for example "backend engineering", "clinical trial", "retail finance")
- likely_terms: up to 40 correctly spelled technical terms, product names, acronyms and jargon this meeting probably contains, including ones the recognizer may have misspelled
- names: people and organisations mentioned
