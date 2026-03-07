from rich.console import Console


def handle_report_command(
    console: Console,
    report_type,
    path,
    require_index_path,
    load_index,
    get_available_reports,
    report_types,
    choose_report_type,
    print_terminal_report,
) -> None:
    path, index_path = require_index_path(console, path)
    index_data = load_index(index_path)
    available_reports = get_available_reports(index_data, report_types)
    report_type = choose_report_type(report_type, available_reports)
    print_terminal_report(console, report_type, index_data, path)
