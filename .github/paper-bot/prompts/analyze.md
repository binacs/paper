You are producing a structured analysis of a research paper for an English-language personal index maintained by an AI Infrastructure engineer. Return ONLY a single JSON object with the keys below. All values are strings (use Markdown bullets / paragraphs inside strings). All output must be in English.

Required keys:

- `system_slug`: kebab-case folder name. If the paper introduces a named system (e.g. Borg, DistServe, Sarathi-Serve), use that name kebab-cased and prefix with org if known (e.g. `bytedance-godel`, `google-borg`). If no clear system, return `misc`.
- `tldr`: 1–2 sentences capturing the main contribution.
- `problem`: What problem the paper addresses, including motivating constraints (1–2 short paragraphs).
- `key_ideas`: The core technical ideas as a bullet list (use `-` bullets, one per line).
- `system_design`: How the system is structured: components, control flow, data flow. Bullets or short paragraphs.
- `evaluation`: How the paper validates its claims: workloads, baselines, headline numbers from the abstract.
- `takeaways`: Insights worth remembering as bullet points.
- `related_work`: Position vs. closely related systems mentioned in the abstract.
- `open_questions`: Limitations or follow-up directions worth tracking.

Rules:

1. Be specific where the abstract supports it; do NOT invent details that are not in the abstract. If a section cannot be filled, set it to "" (empty string).
2. Do not echo the abstract verbatim — paraphrase.
3. Output ONLY the JSON object — no leading prose, no trailing prose, no markdown fence.
4. Keep the entire JSON under ~1500 tokens.

Title: {title}
Authors: {authors}
Venue: {venue} ({year}, {citation_count} citations)

Abstract:
{abstract}

JSON:
