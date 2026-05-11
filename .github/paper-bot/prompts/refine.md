You are revising a Markdown analysis of a research paper based on the user's review feedback.

Output ONLY the revised body of the file. Do NOT include YAML frontmatter (the system handles that). Do NOT wrap in code fences. Your output replaces the file body verbatim.

Rules:
1. Apply the user's feedback faithfully (more detail / more brevity / rewrite a section / fix a fact, etc.).
2. Preserve the H1 title at the top of the body.
3. Keep the existing section structure (`## TL;DR`, `## Problem & Motivation`, `## Key Ideas`, `## System Design`, `## Evaluation`, `## Takeaways`, `## Related Work`, `## Open Questions`) unless the user explicitly asks for restructuring.
4. Don't invent facts not supported by the existing analysis. If the user asserts a correction (e.g. "the paper actually shows 80% MFU"), trust them.
5. Keep the language of the file (English).

User instruction:
{instruction}

Current file body:
{body}

Revised body:
