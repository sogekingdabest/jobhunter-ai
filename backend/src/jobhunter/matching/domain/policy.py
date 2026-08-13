"""Versioned deterministic policy for structured candidate-to-job matching."""

import re
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from jobhunter.candidate.domain.competencies import LanguageLevel
from jobhunter.candidate.domain.profile import CandidateProfile, RemotePreference
from jobhunter.jobs.domain.offers import (
    JobFieldName,
    JobOffer,
    JobOfferField,
    JobRequirement,
    RemoteType,
    RequirementPriority,
    RequirementType,
    Seniority,
)
from jobhunter.matching.domain.assessments import (
    GOOD_MATCH_THRESHOLD,
    MAX_SCORE,
    STRONG_MATCH_THRESHOLD,
    GateStatus,
    MatchAssessment,
    MatchDimension,
    MatchDimensionName,
    MatchEvidence,
    MatchOutcome,
    MatchRecommendation,
    RequirementGate,
)
from jobhunter.matching.domain.taxonomy import SkillTaxonomy, normalize_term

POLICY_VERSION = "structured-v1"
DIMENSION_WEIGHTS = {
    MatchDimensionName.SKILLS: 0.35,
    MatchDimensionName.EXPERIENCE: 0.20,
    MatchDimensionName.SENIORITY: 0.15,
    MatchDimensionName.EDUCATION: 0.10,
    MatchDimensionName.LANGUAGES: 0.10,
    MatchDimensionName.LOCATION: 0.10,
}
LANGUAGE_LEVEL_RANK = {
    LanguageLevel.BASIC: 1,
    LanguageLevel.CONVERSATIONAL: 2,
    LanguageLevel.PROFESSIONAL: 3,
    LanguageLevel.FLUENT: 4,
    LanguageLevel.NATIVE: 5,
}
LANGUAGE_LEVEL_ALIASES = {
    "basic": 1,
    "basico": 1,
    "básico": 1,
    "a1": 1,
    "a2": 1,
    "conversational": 2,
    "conversacional": 2,
    "b1": 2,
    "professional": 3,
    "profesional": 3,
    "b2": 3,
    "fluent": 4,
    "fluido": 4,
    "c1": 4,
    "native": 5,
    "nativo": 5,
    "c2": 5,
}
DEGREE_LEVEL_ALIASES = {
    "secondary": 1,
    "bachillerato": 1,
    "vocational": 2,
    "formacion profesional": 2,
    "formación profesional": 2,
    "fp": 2,
    "associate": 2,
    "bachelor": 3,
    "bachelors": 3,
    "bsc": 3,
    "grado": 3,
    "licenciatura": 3,
    "ingenieria": 3,
    "ingeniería": 3,
    "master": 4,
    "masters": 4,
    "msc": 4,
    "maestria": 4,
    "maestría": 4,
    "doctorate": 5,
    "phd": 5,
    "doctorado": 5,
}
SENIORITY_RANK = {
    Seniority.INTERN: 1,
    Seniority.JUNIOR: 2,
    Seniority.MID: 3,
    Seniority.SENIOR: 4,
    Seniority.LEAD: 5,
    Seniority.MANAGER: 5,
}
SENIORITY_ALIASES = {
    "intern": Seniority.INTERN,
    "internship": Seniority.INTERN,
    "becario": Seniority.INTERN,
    "junior": Seniority.JUNIOR,
    "jr": Seniority.JUNIOR,
    "mid": Seniority.MID,
    "mid level": Seniority.MID,
    "intermediate": Seniority.MID,
    "senior": Seniority.SENIOR,
    "sr": Seniority.SENIOR,
    "lead": Seniority.LEAD,
    "principal": Seniority.LEAD,
    "manager": Seniority.MANAGER,
}
DURATION_PATTERN = re.compile(
    r"(?P<amount>\d+(?:[.,]\d+)?)\s*(?P<unit>years?|yrs?|años?|months?|mos?|meses?)",
    re.IGNORECASE,
)


class StructuredMatchingPolicy:
    """Score explicit facts only; ambiguous mandatory requirements require review."""

    def __init__(self, taxonomy: SkillTaxonomy | None = None) -> None:
        self._taxonomy = taxonomy or SkillTaxonomy()

    def assess(
        self,
        candidate: CandidateProfile,
        offer: JobOffer,
        *,
        assessed_at: datetime | None = None,
    ) -> MatchAssessment:
        now = assessed_at or datetime.now(UTC)
        evidence = self._collect_evidence(candidate, offer, now.date())
        dimensions = self._dimensions(evidence)
        gates = self._gates(offer, evidence)
        score = self._overall_score(dimensions)
        recommendation = self._recommendation(score, gates)
        return MatchAssessment(
            id=uuid4(),
            candidate_profile_id=candidate.id,
            job_offer_id=offer.id,
            policy_version=POLICY_VERSION,
            taxonomy_version=self._taxonomy.version,
            candidate_updated_at=candidate.updated_at,
            job_content_fingerprint=offer.content_fingerprint,
            job_normalization_version=offer.normalization_version,
            score=score,
            recommendation=recommendation,
            dimensions=dimensions,
            gates=gates,
            assessed_at=now,
        )

    def _collect_evidence(
        self, candidate: CandidateProfile, offer: JobOffer, as_of: date
    ) -> tuple[MatchEvidence, ...]:
        evidence: list[MatchEvidence] = []
        handlers = {
            RequirementType.SKILL: self._skill_evidence,
            RequirementType.EXPERIENCE: self._experience_evidence,
            RequirementType.EDUCATION: self._education_evidence,
            RequirementType.LANGUAGE: self._language_evidence,
            RequirementType.LOCATION: self._location_requirement_evidence,
        }
        for requirement in offer.requirements:
            handler = handlers.get(requirement.requirement_type)
            if handler is not None:
                evidence.append(handler(candidate, requirement, as_of))

        seniority_field = self._field(offer, JobFieldName.SENIORITY)
        if seniority_field is not None:
            evidence.append(self._seniority_evidence(candidate, seniority_field))
        location_field = self._field(offer, JobFieldName.LOCATION)
        if location_field is not None:
            evidence.append(self._location_field_evidence(candidate, location_field))
        remote_field = self._field(offer, JobFieldName.REMOTE_TYPE)
        if remote_field is not None:
            evidence.append(self._remote_evidence(candidate, remote_field))
        return tuple(evidence)

    def _skill_evidence(
        self, candidate: CandidateProfile, requirement: JobRequirement, _: date
    ) -> MatchEvidence:
        required = self._taxonomy.canonicalize(requirement.normalized_value)
        matches = tuple(
            item.id
            for item in candidate.competencies
            if self._taxonomy.canonicalize(item.name) == required
        )
        return self._evidence(
            MatchDimensionName.SKILLS,
            requirement,
            outcome=MatchOutcome.MATCHED if matches else MatchOutcome.MISSING,
            score=100 if matches else 0,
            code="skill_alias_match" if matches else "skill_not_declared",
            candidate_ids=matches,
            candidate_values=tuple(
                item.name for item in candidate.competencies if item.id in matches
            ),
        )

    def _experience_evidence(
        self, candidate: CandidateProfile, requirement: JobRequirement, as_of: date
    ) -> MatchEvidence:
        required_months = _parse_duration_months(requirement.normalized_value)
        if required_months is None:
            return self._unknown(
                MatchDimensionName.EXPERIENCE, requirement, "experience_duration_unknown"
            )
        skill = self._taxonomy.find_in(requirement.normalized_value)
        months: int
        candidate_ids: tuple[UUID, ...]
        if skill is not None:
            matching = tuple(
                item
                for item in candidate.competencies
                if self._taxonomy.canonicalize(item.name) == skill
            )
            known = [item for item in matching if item.months_experience is not None]
            if not matching:
                months, candidate_ids = 0, ()
            elif not known:
                return self._unknown(
                    MatchDimensionName.EXPERIENCE,
                    requirement,
                    "candidate_skill_duration_unknown",
                    tuple(item.id for item in matching),
                    tuple(item.name for item in matching),
                )
            else:
                months = max(item.months_experience or 0 for item in known)
                candidate_ids = tuple(item.id for item in known)
        else:
            if not _is_general_experience(requirement.normalized_value):
                return self._unknown(
                    MatchDimensionName.EXPERIENCE,
                    requirement,
                    "experience_scope_unknown",
                )
            total_months = _total_work_months(candidate, as_of)
            if total_months is None:
                return self._unknown(
                    MatchDimensionName.EXPERIENCE,
                    requirement,
                    "candidate_experience_duration_unknown",
                    tuple(item.id for item in candidate.work_experiences),
                    tuple(item.title for item in candidate.work_experiences),
                )
            months = total_months
            candidate_ids = tuple(item.id for item in candidate.work_experiences)
        return self._ratio_evidence(
            MatchDimensionName.EXPERIENCE,
            requirement,
            months,
            required_months,
            candidate_ids,
            (f"{months} months",),
            "experience_requirement_met",
            "experience_requirement_partial",
            "experience_requirement_missing",
        )

    def _education_evidence(
        self, candidate: CandidateProfile, requirement: JobRequirement, _: date
    ) -> MatchEvidence:
        required = _find_rank(requirement.normalized_value, DEGREE_LEVEL_ALIASES)
        if required is None:
            return self._unknown(
                MatchDimensionName.EDUCATION, requirement, "education_level_unknown"
            )
        ranked = [
            (
                item,
                _find_rank(
                    f"{item.qualification} {item.field_of_study or ''}", DEGREE_LEVEL_ALIASES
                ),
            )
            for item in candidate.education
        ]
        known = [(item, rank) for item, rank in ranked if rank is not None]
        candidate_ids: tuple[UUID, ...]
        if not candidate.education:
            best, candidate_ids = 0, ()
        elif not known:
            return self._unknown(
                MatchDimensionName.EDUCATION,
                requirement,
                "candidate_education_level_unknown",
                tuple(item.id for item in candidate.education),
            )
        else:
            best = max(rank for _, rank in known if rank is not None)
            candidate_ids = tuple(item.id for item, rank in known if rank == best)
        return self._ratio_evidence(
            MatchDimensionName.EDUCATION,
            requirement,
            best,
            required,
            candidate_ids,
            tuple(item.qualification for item, rank in known if rank == best),
            "education_requirement_met",
            "education_requirement_partial",
            "education_requirement_missing",
        )

    def _language_evidence(
        self, candidate: CandidateProfile, requirement: JobRequirement, _: date
    ) -> MatchEvidence:
        normalized = normalize_term(requirement.normalized_value)
        matched_language = next(
            (
                item
                for item in candidate.languages
                if f" {normalize_term(item.language)} " in f" {normalized} "
            ),
            None,
        )
        required_level = _find_rank(normalized, LANGUAGE_LEVEL_ALIASES)
        if matched_language is None:
            language_name = _language_name(normalized)
            if language_name is None:
                return self._unknown(
                    MatchDimensionName.LANGUAGES, requirement, "language_name_unknown"
                )
            return self._evidence(
                MatchDimensionName.LANGUAGES,
                requirement,
                outcome=MatchOutcome.MISSING,
                score=0,
                code="language_not_declared",
            )
        if required_level is None:
            return self._evidence(
                MatchDimensionName.LANGUAGES,
                requirement,
                outcome=MatchOutcome.MATCHED,
                score=100,
                code="language_declared",
                candidate_ids=(matched_language.id,),
                candidate_values=(f"{matched_language.language}: {matched_language.level.value}",),
            )
        return self._ratio_evidence(
            MatchDimensionName.LANGUAGES,
            requirement,
            LANGUAGE_LEVEL_RANK[matched_language.level],
            required_level,
            (matched_language.id,),
            (f"{matched_language.language}: {matched_language.level.value}",),
            "language_level_met",
            "language_level_partial",
            "language_not_declared",
        )

    def _location_requirement_evidence(
        self, candidate: CandidateProfile, requirement: JobRequirement, _: date
    ) -> MatchEvidence:
        candidate_locations = {
            normalize_term(value): candidate.id
            for value in (candidate.location, *candidate.preferred_locations)
            if value
        }
        required = normalize_term(requirement.normalized_value)
        candidate_id = candidate_locations.get(required)
        return self._evidence(
            MatchDimensionName.LOCATION,
            requirement,
            outcome=MatchOutcome.MATCHED if candidate_id else MatchOutcome.MISSING,
            score=100 if candidate_id else 0,
            code="location_exact_match" if candidate_id else "location_not_preferred",
            candidate_ids=(candidate_id,) if candidate_id else (),
            candidate_values=(requirement.normalized_value,) if candidate_id else (),
        )

    def _seniority_evidence(
        self, candidate: CandidateProfile, field: JobOfferField
    ) -> MatchEvidence:
        candidate_values = (
            (candidate.id, candidate.headline),
            *((item.id, item.title) for item in candidate.work_experiences),
        )
        ranked = [
            (item_id, _find_seniority(value))
            for item_id, value in candidate_values
            if value is not None
        ]
        known = [(item_id, value) for item_id, value in ranked if value is not None]
        if not known:
            return self._unknown_field(
                MatchDimensionName.SENIORITY,
                field,
                "candidate_seniority_unknown",
                tuple(value for _, value in candidate_values if value),
            )
        candidate_id, best = max(known, key=lambda item: SENIORITY_RANK[item[1]])
        candidate_title = next(
            value for item_id, value in candidate_values if item_id == candidate_id and value
        )
        required = Seniority(field.value)
        return self._ratio_field_evidence(
            MatchDimensionName.SENIORITY,
            field,
            SENIORITY_RANK[best],
            SENIORITY_RANK[required],
            (candidate_id,),
            (candidate_title,),
            "seniority_requirement_met",
            "seniority_requirement_partial",
        )

    def _location_field_evidence(
        self, candidate: CandidateProfile, field: JobOfferField
    ) -> MatchEvidence:
        candidate_locations = {
            normalize_term(value)
            for value in (candidate.location, *candidate.preferred_locations)
            if value
        }
        matched = normalize_term(field.value) in candidate_locations
        return self._field_evidence(
            MatchDimensionName.LOCATION,
            field,
            MatchOutcome.MATCHED if matched else MatchOutcome.MISSING,
            100 if matched else 0,
            "location_exact_match" if matched else "offer_location_not_preferred",
            (candidate.id,) if matched else (),
            (field.value,) if matched else (),
        )

    def _remote_evidence(self, candidate: CandidateProfile, field: JobOfferField) -> MatchEvidence:
        preference = candidate.remote_preference
        if preference is None:
            return self._unknown_field(
                MatchDimensionName.LOCATION, field, "remote_preference_unknown"
            )
        score = _remote_score(preference, RemoteType(field.value))
        outcome = (
            MatchOutcome.MATCHED
            if score == MAX_SCORE
            else MatchOutcome.PARTIAL
            if score
            else MatchOutcome.MISSING
        )
        return self._field_evidence(
            MatchDimensionName.LOCATION,
            field,
            outcome,
            score,
            "remote_preference_met"
            if score == MAX_SCORE
            else "remote_preference_partial"
            if score
            else "remote_preference_mismatch",
            (candidate.id,),
            (preference.value,),
        )

    def _dimensions(self, evidence: tuple[MatchEvidence, ...]) -> tuple[MatchDimension, ...]:
        grouped: defaultdict[MatchDimensionName, list[MatchEvidence]] = defaultdict(list)
        for item in evidence:
            grouped[item.dimension].append(item)
        return tuple(
            MatchDimension(
                id=uuid4(),
                name=name,
                score=_average(item.score for item in items),
                weight=DIMENSION_WEIGHTS[name],
                evidence=tuple(items),
            )
            for name, items in grouped.items()
        )

    def _gates(
        self, offer: JobOffer, evidence: tuple[MatchEvidence, ...]
    ) -> tuple[RequirementGate, ...]:
        by_requirement = {item.job_requirement_id: item for item in evidence}
        gates: list[RequirementGate] = []
        for requirement in offer.requirements:
            if requirement.priority is not RequirementPriority.REQUIRED:
                continue
            item = by_requirement.get(requirement.id)
            if item is None or item.outcome is MatchOutcome.UNKNOWN:
                status, code = GateStatus.NEEDS_REVIEW, "mandatory_requirement_not_deterministic"
            elif item.outcome is MatchOutcome.MATCHED:
                status, code = GateStatus.PASSED, "mandatory_requirement_met"
            else:
                status, code = GateStatus.FAILED, "mandatory_requirement_not_met"
            gates.append(RequirementGate(uuid4(), requirement.id, status, code))
        return tuple(gates)

    @staticmethod
    def _overall_score(dimensions: tuple[MatchDimension, ...]) -> float:
        active = tuple(item for item in dimensions if item.score is not None)
        if not active:
            return 0
        total_weight = sum(item.weight for item in active)
        return round(sum((item.score or 0) * item.weight for item in active) / total_weight, 2)

    @staticmethod
    def _recommendation(score: float, gates: tuple[RequirementGate, ...]) -> MatchRecommendation:
        if any(item.status is GateStatus.FAILED for item in gates):
            return MatchRecommendation.BLOCKED
        if any(item.status is GateStatus.NEEDS_REVIEW for item in gates):
            return MatchRecommendation.NEEDS_REVIEW
        if score >= STRONG_MATCH_THRESHOLD:
            return MatchRecommendation.STRONG_MATCH
        if score >= GOOD_MATCH_THRESHOLD:
            return MatchRecommendation.GOOD_MATCH
        return MatchRecommendation.WEAK_MATCH

    @staticmethod
    def _field(offer: JobOffer, name: JobFieldName) -> JobOfferField | None:
        return next((item for item in offer.fields if item.name is name), None)

    @staticmethod
    def _evidence(  # noqa: PLR0913
        dimension: MatchDimensionName,
        requirement: JobRequirement,
        *,
        outcome: MatchOutcome,
        score: float,
        code: str,
        candidate_ids: tuple[UUID, ...] = (),
        candidate_values: tuple[str, ...] = (),
    ) -> MatchEvidence:
        return MatchEvidence(
            id=uuid4(),
            dimension=dimension,
            outcome=outcome,
            score=score,
            explanation_code=code,
            job_value=requirement.normalized_value,
            candidate_fact_ids=candidate_ids,
            candidate_values=candidate_values,
            job_requirement_id=requirement.id,
        )

    @staticmethod
    def _unknown(
        dimension: MatchDimensionName,
        requirement: JobRequirement,
        code: str,
        candidate_ids: tuple[UUID, ...] = (),
        candidate_values: tuple[str, ...] = (),
    ) -> MatchEvidence:
        return MatchEvidence(
            id=uuid4(),
            dimension=dimension,
            outcome=MatchOutcome.UNKNOWN,
            score=None,
            explanation_code=code,
            job_value=requirement.normalized_value,
            candidate_fact_ids=candidate_ids,
            candidate_values=candidate_values,
            job_requirement_id=requirement.id,
        )

    @staticmethod
    def _field_evidence(  # noqa: PLR0913, PLR0917
        dimension: MatchDimensionName,
        field: JobOfferField,
        outcome: MatchOutcome,
        score: float,
        code: str,
        candidate_ids: tuple[UUID, ...] = (),
        candidate_values: tuple[str, ...] = (),
    ) -> MatchEvidence:
        return MatchEvidence(
            id=uuid4(),
            dimension=dimension,
            outcome=outcome,
            score=score,
            explanation_code=code,
            job_value=field.value,
            candidate_fact_ids=candidate_ids,
            candidate_values=candidate_values,
            job_field_id=field.id,
        )

    @staticmethod
    def _unknown_field(
        dimension: MatchDimensionName,
        field: JobOfferField,
        code: str,
        candidate_values: tuple[str, ...] = (),
    ) -> MatchEvidence:
        return MatchEvidence(
            id=uuid4(),
            dimension=dimension,
            outcome=MatchOutcome.UNKNOWN,
            score=None,
            explanation_code=code,
            job_value=field.value,
            candidate_values=candidate_values,
            job_field_id=field.id,
        )

    def _ratio_evidence(  # noqa: PLR0913, PLR0917
        self,
        dimension: MatchDimensionName,
        requirement: JobRequirement,
        actual: int,
        required: int,
        candidate_ids: tuple[UUID, ...],
        candidate_values: tuple[str, ...],
        met_code: str,
        partial_code: str,
        missing_code: str,
    ) -> MatchEvidence:
        outcome, score, code = _ratio(actual, required, met_code, partial_code, missing_code)
        return self._evidence(
            dimension,
            requirement,
            outcome=outcome,
            score=score,
            code=code,
            candidate_ids=candidate_ids,
            candidate_values=candidate_values,
        )

    def _ratio_field_evidence(  # noqa: PLR0913, PLR0917
        self,
        dimension: MatchDimensionName,
        field: JobOfferField,
        actual: int,
        required: int,
        candidate_ids: tuple[UUID, ...],
        candidate_values: tuple[str, ...],
        met_code: str,
        partial_code: str,
    ) -> MatchEvidence:
        outcome, score, code = _ratio(actual, required, met_code, partial_code, partial_code)
        return self._field_evidence(
            dimension,
            field,
            outcome,
            score,
            code,
            candidate_ids,
            candidate_values,
        )


def _parse_duration_months(value: str) -> int | None:
    match = DURATION_PATTERN.search(value)
    if match is None:
        return None
    amount = float(match.group("amount").replace(",", "."))
    unit = match.group("unit").casefold()
    months = amount if unit.startswith(("month", "mo", "mes")) else amount * 12
    return max(1, round(months))


def _total_work_months(candidate: CandidateProfile, as_of: date) -> int | None:
    if not candidate.work_experiences:
        return 0
    intervals: set[int] = set()
    for item in candidate.work_experiences:
        if item.start_date is None:
            return None
        end = item.end_date or as_of
        start_index = item.start_date.year * 12 + item.start_date.month
        end_index = end.year * 12 + end.month
        intervals.update(range(start_index, end_index + 1))
    return len(intervals)


def _is_general_experience(value: str) -> bool:
    normalized = f" {normalize_term(value)} "
    markers = (
        " professional experience ",
        " work experience ",
        " overall experience ",
        " relevant experience ",
        " experiencia profesional ",
        " experiencia laboral ",
        " experiencia total ",
    )
    return any(marker in normalized for marker in markers)


def _find_rank(value: str, aliases: dict[str, int]) -> int | None:
    normalized = f" {normalize_term(value)} "
    ranks = [rank for alias, rank in aliases.items() if f" {normalize_term(alias)} " in normalized]
    return max(ranks) if ranks else None


def _language_name(value: str) -> str | None:
    known = (
        "english",
        "inglés",
        "ingles",
        "spanish",
        "español",
        "espanol",
        "french",
        "francés",
        "german",
        "alemán",
    )
    return next((name for name in known if f" {normalize_term(name)} " in f" {value} "), None)


def _find_seniority(value: str) -> Seniority | None:
    normalized = f" {normalize_term(value)} "
    return next(
        (seniority for alias, seniority in SENIORITY_ALIASES.items() if f" {alias} " in normalized),
        None,
    )


def _remote_score(preference: RemotePreference, offer_type: RemoteType) -> float:
    if preference is RemotePreference.FLEXIBLE or preference.value == offer_type.value:
        return 100
    if (preference, offer_type) in {
        (RemotePreference.HYBRID, RemoteType.ONSITE),
        (RemotePreference.ONSITE, RemoteType.HYBRID),
    }:
        return 50
    return 0


def _ratio(
    actual: int, required: int, met_code: str, partial_code: str, missing_code: str
) -> tuple[MatchOutcome, float, str]:
    if actual >= required:
        return MatchOutcome.MATCHED, 100, met_code
    if actual > 0:
        return MatchOutcome.PARTIAL, round(actual / required * 100, 2), partial_code
    return MatchOutcome.MISSING, 0, missing_code


def _average(values: Iterable[float | None]) -> float | None:
    scored = [value for value in values if isinstance(value, (int, float))]
    return None if not scored else round(sum(scored) / len(scored), 2)
