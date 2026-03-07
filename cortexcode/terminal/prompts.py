from typing import Sequence

from rich.prompt import Prompt


def choose_report_type(report_type: str | None, available_reports: Sequence[str]) -> str:
    if report_type:
        return report_type
    if not available_reports:
        return "overview"
    return Prompt.ask("Choose a report", choices=list(available_reports), default=available_reports[0])
