"""Docs Generator Package - Generate project documentation from index."""

def generate_all_docs(*args, **kwargs):
    from cortexcode.docs.generator import generate_all_docs as impl
    return impl(*args, **kwargs)


def generate_readme(*args, **kwargs):
    from cortexcode.docs.generator import generate_readme as impl
    return impl(*args, **kwargs)


def generate_api_docs(*args, **kwargs):
    from cortexcode.docs.generator import generate_api_docs as impl
    return impl(*args, **kwargs)


def generate_structure_docs(*args, **kwargs):
    from cortexcode.docs.generator import generate_structure_docs as impl
    return impl(*args, **kwargs)


def generate_flow_docs(*args, **kwargs):
    from cortexcode.docs.generator import generate_flow_docs as impl
    return impl(*args, **kwargs)


def generate_tech_docs(*args, **kwargs):
    from cortexcode.docs.generator import generate_tech_docs as impl
    return impl(*args, **kwargs)


def generate_insights_docs(*args, **kwargs):
    from cortexcode.docs.generator import generate_insights_docs as impl
    return impl(*args, **kwargs)


def generate_html_docs(*args, **kwargs):
    from cortexcode.docs.generator import generate_html_docs as impl
    return impl(*args, **kwargs)


def generate_all_diagrams(*args, **kwargs):
    from cortexcode.docs.diagrams import generate_all_diagrams as impl
    return impl(*args, **kwargs)


def generate_call_graph_diagram(*args, **kwargs):
    from cortexcode.docs.diagrams import generate_call_graph_diagram as impl
    return impl(*args, **kwargs)


def generate_class_diagram(*args, **kwargs):
    from cortexcode.docs.diagrams import generate_class_diagram as impl
    return impl(*args, **kwargs)


def generate_sequence_diagram(*args, **kwargs):
    from cortexcode.docs.diagrams import generate_sequence_diagram as impl
    return impl(*args, **kwargs)


def generate_architecture_diagram(*args, **kwargs):
    from cortexcode.docs.diagrams import generate_architecture_diagram as impl
    return impl(*args, **kwargs)


def generate_import_graph(*args, **kwargs):
    from cortexcode.docs.diagrams import generate_import_graph as impl
    return impl(*args, **kwargs)


def generate_dependency_graph(*args, **kwargs):
    from cortexcode.docs.diagrams import generate_dependency_graph as impl
    return impl(*args, **kwargs)


def save_diagrams(*args, **kwargs):
    from cortexcode.docs.diagrams import save_diagrams as impl
    return impl(*args, **kwargs)

__all__ = [
    "generate_all_docs",
    "generate_readme",
    "generate_api_docs",
    "generate_structure_docs",
    "generate_flow_docs",
    "generate_tech_docs",
    "generate_insights_docs",
    "generate_html_docs",
    "generate_all_diagrams",
    "generate_call_graph_diagram",
    "generate_class_diagram",
    "generate_sequence_diagram",
    "generate_architecture_diagram",
    "generate_import_graph",
    "generate_dependency_graph",
    "save_diagrams",
]
