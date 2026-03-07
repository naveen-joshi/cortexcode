"""Explainer — generate explanatory answers for natural language concept queries."""

from __future__ import annotations

from typing import Any, Optional

from cortexcode.ai_docs.llm_client import LLMClient, LLMProvider
from cortexcode.ai_docs.config import get_config
from cortexcode.ai_docs.page_generator import _format_snippet_block
from cortexcode.knowledge.concepts import find_concept_for_query
from cortexcode.knowledge.models import ConceptEntry, KnowledgePack, UsageRecord


def build_explanation_prompt(
    query: str,
    concepts: list[ConceptEntry],
    pack: KnowledgePack,
) -> tuple[str, str]:
    """Build a prompt to explain a concept in plain language."""
    concept_blocks = []
    for concept in concepts[:3]:
        lines = [f"### Concept: {concept.name.replace('_', ' ').title()}"]
        lines.append(f"Related symbols: {', '.join(f'`{s}`' for s in concept.related_symbols[:8])}")
        lines.append(f"Related files: {', '.join(f'`{f}`' for f in concept.related_files[:5])}")
        if concept.related_flows:
            for flow in concept.related_flows[:2]:
                lines.append(f"Call flow: {' → '.join(f'`{f}`' for f in flow)}")
        if concept.snippets:
            lines.append("")
            for snip in concept.snippets[:2]:
                lines.append(_format_snippet_block(snip))
        concept_blocks.append("\n".join(lines))

    # Also gather call graph context for mentioned symbols
    call_context = []
    for concept in concepts[:2]:
        for sym_name in concept.related_symbols[:5]:
            callees = pack.call_graph.get(sym_name, [])
            callers = [k for k, v in list(pack.call_graph.items())[:200] if sym_name in v]
            if callees or callers:
                parts = [f"**`{sym_name}`**"]
                if callers:
                    parts.append(f"called by: {', '.join(f'`{c}`' for c in callers[:4])}")
                if callees:
                    parts.append(f"calls: {', '.join(f'`{c}`' for c in callees[:4])}")
                call_context.append("- " + " | ".join(parts))

    system = (
        "You are a friendly technical explainer who makes complex software concepts "
        "understandable to non-technical people. When asked how something works, "
        "explain it step-by-step in plain language. Use analogies and everyday "
        "language. Include relevant code snippets as illustrations, but the "
        "explanation itself should be in prose, not code. Always explain WHAT "
        "something does, WHY it matters, and HOW it works at a high level."
    )

    user = f"""The user asks: "{query}"

Here is what I found in the codebase of **{pack.project_name}**:

{chr(10).join(concept_blocks) if concept_blocks else 'No specific concepts matched. Please provide a general answer based on the project structure.'}

## Call Graph Context
{chr(10).join(call_context) if call_context else 'No call graph data available for these symbols.'}

## Project Facts
- Languages: {', '.join(pack.languages)}
- Files: {pack.file_count}
- Symbols: {pack.symbol_count}

Please answer the user's question:
1. Start with a simple, one-paragraph summary a non-technical person can understand
2. Then explain step-by-step how it works in plain language
3. Include relevant code snippets as illustrations (not as the main content)
4. Mention which files are involved so the user can explore further
5. Suggest related concepts or follow-up questions"""

    return system, user


class Explainer:
    """Generate explanatory answers for natural language queries about a codebase."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.5,
        max_tokens: int = 4096,
    ):
        config = get_config()
        self.provider_name = provider or config.provider
        resolved_model = model
        if not resolved_model and self.provider_name == config.provider:
            resolved_model = config.model
        self.llm = LLMClient(
            provider=LLMProvider(self.provider_name),
            api_key=api_key,
            model=resolved_model,
        )
        self.temperature = temperature
        self.max_tokens = max_tokens

    def explain(
        self,
        query: str,
        pack: KnowledgePack,
    ) -> tuple[str, UsageRecord | None]:
        """Answer a natural language query about the codebase.

        Returns:
            (answer_text, usage_record) — usage_record may be None if LLM is not configured.
        """
        # Find relevant concepts
        matching_concepts = find_concept_for_query(pack.concepts, query)

        if not matching_concepts:
            # Fallback: try to find symbols matching query words
            return self._fallback_explain(query, pack)

        system_msg, user_msg = build_explanation_prompt(query, matching_concepts, pack)
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        if not self.llm.is_configured():
            return (
                f"No API key configured for {self.provider_name}. "
                f"Run: cortexcode config set {self.provider_name}_api_key <your-key>",
                None,
            )

        try:
            response = self.llm.complete(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            usage_data = response.usage or {}
            usage = UsageRecord(
                page_id=f"explain_{query[:50]}",
                provider=self.provider_name,
                model=response.model or self.llm.model,
                prompt_tokens=usage_data.get("prompt_tokens", usage_data.get("input_tokens", 0)),
                completion_tokens=usage_data.get("completion_tokens", usage_data.get("output_tokens", 0)),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            if usage.total_tokens == 0 and (usage.prompt_tokens or usage.completion_tokens):
                usage.total_tokens = usage.prompt_tokens + usage.completion_tokens

            return response.content, usage

        except Exception as e:
            return f"Error generating explanation: {e}", None

    def _fallback_explain(
        self,
        query: str,
        pack: KnowledgePack,
    ) -> tuple[str, UsageRecord | None]:
        """Fallback when no concepts match — search symbols directly."""
        import re
        query_words = set(re.split(r"\W+", query.lower())) - {"how", "does", "work", "the", "in", "what", "is", "a", "an"}

        matched_symbols: list[dict[str, Any]] = []
        for name, sym in pack.symbol_index.items():
            name_lower = name.lower()
            for qw in query_words:
                if len(qw) > 2 and qw in name_lower:
                    matched_symbols.append(sym)
                    break

        if not matched_symbols:
            return (
                f"I couldn't find specific code related to \"{query}\" in this project. "
                f"The project **{pack.project_name}** has {pack.file_count} files and "
                f"{pack.symbol_count} symbols across {', '.join(pack.languages)}. "
                f"Try browsing the project overview or architecture pages for a general understanding.",
                None,
            )

        # Build a lightweight explanation from matched symbols
        sym_lines = []
        for sym in matched_symbols[:10]:
            name = sym.get("name", "?")
            stype = sym.get("type", "?")
            fp = sym.get("file", "?")
            doc = sym.get("doc", "")
            line = f"- **`{name}`** ({stype}) in `{fp}`"
            if doc:
                line += f" — {doc[:100]}"
            sym_lines.append(line)

        system = (
            "You are a friendly technical explainer. The user asked a question about "
            "a codebase. I found some matching symbols. Explain what these symbols do "
            "and how they relate to the user's question in plain language."
        )
        user = f"""The user asks: "{query}"

Here are matching symbols from **{pack.project_name}**:

{chr(10).join(sym_lines)}

Please explain:
1. What these symbols do in plain language
2. How they might relate to the user's question
3. Suggest which files to look at for more details"""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        if not self.llm.is_configured():
            return "\n".join(sym_lines), None

        try:
            response = self.llm.complete(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
            usage_data = response.usage or {}
            usage = UsageRecord(
                page_id=f"explain_{query[:50]}",
                provider=self.provider_name,
                model=response.model or self.llm.model,
                prompt_tokens=usage_data.get("prompt_tokens", usage_data.get("input_tokens", 0)),
                completion_tokens=usage_data.get("completion_tokens", usage_data.get("output_tokens", 0)),
                total_tokens=usage_data.get("total_tokens", 0),
            )
            return response.content, usage
        except Exception as e:
            return f"Error: {e}\n\nMatching symbols:\n" + "\n".join(sym_lines), None
