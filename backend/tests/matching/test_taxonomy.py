"""Controlled taxonomy tests."""

import pytest

from jobhunter.matching.domain.taxonomy import SkillTaxonomy, normalize_term


def test_taxonomy_matches_aliases_and_preserves_unknown_exact_terms() -> None:
    taxonomy = SkillTaxonomy()

    assert taxonomy.canonicalize("  JS ") == "javascript"
    assert taxonomy.canonicalize("FastAPI") == "fastapi"
    assert taxonomy.find_in("At least 3 years using Node.js") == "node.js"
    assert taxonomy.find_in("General backend experience") is None
    assert normalize_term("  Amazon-Web   Services ") == "amazon web services"


def test_taxonomy_rejects_empty_terms_and_accepts_custom_version() -> None:
    taxonomy = SkillTaxonomy(version="custom-v1", aliases={"Py": "Python"})

    assert taxonomy.version == "custom-v1"
    assert taxonomy.canonicalize("PY") == "python"
    with pytest.raises(ValueError, match="empty_skill_taxonomy_term"):
        SkillTaxonomy(aliases={"": "python"})
