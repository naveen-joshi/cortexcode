"""Report runner — orchestrate page generation with token accounting."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from cortexcode.ai_docs.llm_client import LLMClient, LLMProvider
from cortexcode.ai_docs.config import get_config
from cortexcode.ai_docs.doc_cache import get_prompt_hash, load_cached_response, save_cached_response
from cortexcode.ai_docs.page_generator import PAGE_GENERATORS, build_module_prompt
from cortexcode.knowledge.models import KnowledgePack, PageMeta, UsageRecord
from cortexcode.knowledge.usage import format_usage_cli, format_usage_table, save_usage_report


class ReportRunner:
    """Generate a full CodeWiki-style documentation set from a KnowledgePack."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        cache_enabled: bool = True,
    ):
        config = get_config()
        self.provider_name = provider or config.provider
        # Only use config model if the provider matches config's provider
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
        self.cache_enabled = cache_enabled
        self.usage_records: list[UsageRecord] = []

    def generate_wiki(
        self,
        pack: KnowledgePack,
        output_dir: Path,
        pages: list[str] | None = None,
        include_modules: bool = True,
        max_modules: int = 15,
        on_page_start: Any = None,
        on_page_done: Any = None,
    ) -> list[PageMeta]:
        """Generate the full documentation set.

        Args:
            pack: The KnowledgePack to generate docs from.
            output_dir: Directory to write output files.
            pages: Which top-level pages to generate (default: all).
            include_modules: Whether to generate per-module pages.
            max_modules: Max number of module pages to generate.
            on_page_start: Optional callback(page_id, title).
            on_page_done: Optional callback(page_id, status, usage_record).
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        pages_to_gen = pages or list(PAGE_GENERATORS.keys())
        results: list[PageMeta] = []

        # Generate top-level pages
        for page_id in pages_to_gen:
            gen_info = PAGE_GENERATORS.get(page_id)
            if not gen_info:
                continue

            title = gen_info["title"]
            output_file = gen_info["output_file"]
            prompt_builder = gen_info["prompt_builder"]

            if on_page_start:
                on_page_start(page_id, title)

            system_msg, user_msg = prompt_builder(pack)
            meta = self._generate_page(
                page_id=page_id,
                title=title,
                output_file=output_file,
                system_msg=system_msg,
                user_msg=user_msg,
                output_dir=output_dir,
            )
            results.append(meta)

            if on_page_done:
                on_page_done(page_id, meta.status, meta.usage)

        # Generate per-module pages
        if include_modules:
            modules_dir = output_dir / "modules"
            modules_dir.mkdir(exist_ok=True)

            # Pick top modules by symbol count
            top_modules = sorted(
                pack.file_summaries.items(),
                key=lambda x: -x[1].get("symbol_count", 0),
            )[:max_modules]

            for file_path, file_data in top_modules:
                if file_data.get("symbol_count", 0) < 2:
                    continue

                page_id = f"module_{file_path}"
                safe_name = file_path.replace("/", "_").replace("\\", "_").replace(".", "_")
                output_file = f"modules/{safe_name}.md"
                title = f"Module: {file_path}"

                if on_page_start:
                    on_page_start(page_id, title)

                system_msg, user_msg = build_module_prompt(pack, file_path, file_data)
                meta = self._generate_page(
                    page_id=page_id,
                    title=title,
                    output_file=output_file,
                    system_msg=system_msg,
                    user_msg=user_msg,
                    output_dir=output_dir,
                )
                results.append(meta)

                if on_page_done:
                    on_page_done(page_id, meta.status, meta.usage)

        # Save usage report
        save_usage_report(self.usage_records, output_dir / "generation-report.json")

        # Save usage table as markdown
        table_md = f"# Generation Report\n\n{format_usage_table(self.usage_records)}\n"
        (output_dir / "GENERATION_REPORT.md").write_text(table_md, encoding="utf-8")

        pack.pages = results
        pack.usage_records = self.usage_records
        return results

    def _generate_page(
        self,
        page_id: str,
        title: str,
        output_file: str,
        system_msg: str,
        user_msg: str,
        output_dir: Path,
    ) -> PageMeta:
        """Generate a single documentation page with caching and usage tracking."""
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ]

        meta = PageMeta(
            page_id=page_id,
            title=title,
            output_file=output_file,
        )

        # Check cache
        prompt_hash = get_prompt_hash(messages, page_id)
        if self.cache_enabled:
            cached = load_cached_response(prompt_hash)
            if cached:
                (output_dir / output_file).parent.mkdir(parents=True, exist_ok=True)
                (output_dir / output_file).write_text(cached, encoding="utf-8")
                usage = UsageRecord(
                    page_id=page_id,
                    provider=self.provider_name,
                    model=self.llm.model,
                    cached=True,
                )
                meta.usage = usage
                meta.status = "cached"
                self.usage_records.append(usage)
                return meta

        # Check if LLM is configured
        if not self.llm.is_configured():
            meta.status = "error"
            usage = UsageRecord(
                page_id=page_id,
                provider=self.provider_name,
                model=self.llm.model,
            )
            meta.usage = usage
            self.usage_records.append(usage)
            return meta

        try:
            response = self.llm.complete(
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            content = response.content
            usage_data = response.usage or {}

            usage = UsageRecord(
                page_id=page_id,
                provider=self.provider_name,
                model=response.model or self.llm.model,
                prompt_tokens=usage_data.get("prompt_tokens", usage_data.get("input_tokens", 0)),
                completion_tokens=usage_data.get("completion_tokens", usage_data.get("output_tokens", 0)),
                total_tokens=usage_data.get("total_tokens", 0),
                cached=False,
            )

            # Fallback: estimate total if not provided
            if usage.total_tokens == 0 and (usage.prompt_tokens or usage.completion_tokens):
                usage.total_tokens = usage.prompt_tokens + usage.completion_tokens

            (output_dir / output_file).parent.mkdir(parents=True, exist_ok=True)
            (output_dir / output_file).write_text(content, encoding="utf-8")

            if self.cache_enabled:
                save_cached_response(prompt_hash, content)

            meta.usage = usage
            meta.status = "generated"
            self.usage_records.append(usage)

        except Exception as e:
            meta.status = "error"
            usage = UsageRecord(
                page_id=page_id,
                provider=self.provider_name,
                model=self.llm.model,
            )
            meta.usage = usage
            self.usage_records.append(usage)
            # Write error placeholder
            (output_dir / output_file).parent.mkdir(parents=True, exist_ok=True)
            (output_dir / output_file).write_text(
                f"# {title}\n\n> Generation failed: {e}\n",
                encoding="utf-8",
            )

        return meta

    def get_usage_summary(self) -> str:
        """Get a formatted CLI usage summary."""
        return format_usage_cli(self.usage_records)
