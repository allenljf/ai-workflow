from dataclasses import dataclass
from typing import Protocol
from .prompt import EnrichRequest
@dataclass
class ProviderResult:
    payload: dict
    input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    request_id: str | None
    # output_tokens is total completion usage, inclusive of reasoning, never added twice.
class ProviderError(Exception):
    """Sanitized failure; caller must retain reservations for ambiguous charge."""
class EnrichmentProvider(Protocol):
    def generate(self,request: EnrichRequest) -> ProviderResult:...
