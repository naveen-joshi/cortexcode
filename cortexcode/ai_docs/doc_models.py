from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class DocOutput:
    """Output from AI documentation generation."""
    overview: Optional[str] = None
    api_docs: Optional[str] = None
    architecture: Optional[str] = None
    flows: Optional[str] = None
    module_docs: Optional[Dict[str, str]] = None
