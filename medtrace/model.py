"""Requirements and risks, loaded from YAML kept in the product repository.

requirements.yml
    requirements:
      - id: SRS-003
        title: Report missing data as absent, with the reason
        text: When the sensor gives a valid rate for less than ...
        verification: test        # test | inspection | analysis
        derived_from: [UN-01]     # optional, user need or system requirement ids

risks.yml
    acceptability: {max_score: 6}  # severity x probability, 1..5 each
    risks:
      - id: HAZ-001
        hazard: Heart rate value that does not reflect the patient
        situation: Value stored while the sensor was off
        harm: Deterioration recognised late
        severity: 4
        probability: 3              # before controls
        controls: [SRS-003, SRS-004]
        residual_probability: 1     # after controls
        external_controls: []       # controls outside the software, with text
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

VERIFICATION_METHODS = {"test", "inspection", "analysis"}


@dataclass(frozen=True)
class Requirement:
    id: str
    title: str
    text: str = ""
    verification: str = "test"
    derived_from: tuple[str, ...] = ()
    justification: str = ""  # required when verification is not "test"


@dataclass(frozen=True)
class Risk:
    id: str
    hazard: str
    situation: str
    harm: str
    severity: int
    probability: int
    controls: tuple[str, ...] = ()
    external_controls: tuple[str, ...] = ()
    residual_probability: int | None = None

    @property
    def initial_score(self) -> int:
        return self.severity * self.probability

    @property
    def residual_score(self) -> int:
        p = self.residual_probability if self.residual_probability is not None else self.probability
        return self.severity * p


@dataclass
class Spec:
    requirements: list[Requirement] = field(default_factory=list)
    risks: list[Risk] = field(default_factory=list)
    max_risk_score: int = 6
    problems: list[str] = field(default_factory=list)  # load-time errors

    def requirement(self, rid: str) -> Requirement | None:
        return next((r for r in self.requirements if r.id == rid), None)


def _as_tuple(v) -> tuple[str, ...]:
    if v is None:
        return ()
    return tuple(v) if isinstance(v, list) else (v,)


def load(req_path: Path, risk_path: Path | None) -> Spec:
    spec = Spec()
    data = yaml.safe_load(req_path.read_text()) or {}
    for i, r in enumerate(data.get("requirements", [])):
        try:
            req = Requirement(
                id=str(r["id"]),
                title=str(r["title"]),
                text=str(r.get("text", "")).strip(),
                verification=str(r.get("verification", "test")),
                derived_from=_as_tuple(r.get("derived_from")),
                justification=str(r.get("justification", "")).strip(),
            )
        except KeyError as e:
            spec.problems.append(f"{req_path.name}: requirement #{i + 1} has no {e.args[0]}")
            continue
        if req.verification not in VERIFICATION_METHODS:
            spec.problems.append(f"{req.id}: verification must be one of {sorted(VERIFICATION_METHODS)}")
        spec.requirements.append(req)

    if risk_path and risk_path.exists():
        data = yaml.safe_load(risk_path.read_text()) or {}
        spec.max_risk_score = int((data.get("acceptability") or {}).get("max_score", spec.max_risk_score))
        for i, r in enumerate(data.get("risks", [])):
            try:
                risk = Risk(
                    id=str(r["id"]),
                    hazard=str(r["hazard"]),
                    situation=str(r["situation"]),
                    harm=str(r["harm"]),
                    severity=int(r["severity"]),
                    probability=int(r["probability"]),
                    controls=_as_tuple(r.get("controls")),
                    external_controls=_as_tuple(r.get("external_controls")),
                    residual_probability=r.get("residual_probability"),
                )
            except KeyError as e:
                spec.problems.append(f"{risk_path.name}: risk #{i + 1} has no {e.args[0]}")
                continue
            for name, v in (
                ("severity", risk.severity),
                ("probability", risk.probability),
                ("residual_probability", risk.residual_probability),
            ):
                if v is not None and not 1 <= v <= 5:
                    spec.problems.append(f"{risk.id}: {name} must be 1..5")
            spec.risks.append(risk)
    return spec
