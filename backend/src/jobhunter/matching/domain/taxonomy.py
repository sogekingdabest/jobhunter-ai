"""Small, explicit and versioned taxonomies used by deterministic matching."""

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

TOKEN_SEPARATOR = re.compile(r"[^\w+#.]+", re.UNICODE)


def normalize_term(value: str) -> str:
    """Normalize comparison syntax without inventing semantic equivalence."""

    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    return " ".join(TOKEN_SEPARATOR.sub(" ", normalized).split())


DEFAULT_SKILL_ALIASES = {
    "amazon web services": "aws",
    "aws": "aws",
    "c sharp": "c#",
    "c#": "c#",
    "docker": "docker",
    "dotnet": ".net",
    ".net": ".net",
    "git": "git",
    "javascript": "javascript",
    "js": "javascript",
    "k8s": "kubernetes",
    "kubernetes": "kubernetes",
    "node": "node.js",
    "node.js": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "py": "python",
    "python": "python",
    "react": "react",
    "spring boot": "spring boot",
    "sql": "sql",
    "typescript": "typescript",
    "ts": "typescript",
}


@dataclass(frozen=True, slots=True)
class SkillTaxonomy:
    """Controlled aliases; unknown terms only match their exact normalized form."""

    version: str = "skills-v1"
    aliases: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        source = self.aliases or DEFAULT_SKILL_ALIASES
        normalized = {
            normalize_term(alias): normalize_term(canonical) for alias, canonical in source.items()
        }
        if any(not alias or not canonical for alias, canonical in normalized.items()):
            raise ValueError("empty_skill_taxonomy_term")
        object.__setattr__(self, "aliases", MappingProxyType(normalized))

    def canonicalize(self, value: str) -> str:
        normalized = normalize_term(value)
        aliases = self.aliases or {}
        return aliases.get(normalized, normalized)

    def find_in(self, value: str) -> str | None:
        """Find the longest known alias as a complete token sequence."""

        normalized = f" {normalize_term(value)} "
        aliases = self.aliases or {}
        matches = (
            (alias, canonical) for alias, canonical in aliases.items() if f" {alias} " in normalized
        )
        found = sorted(matches, key=lambda item: len(item[0]), reverse=True)
        return found[0][1] if found else None
