"""`pack` 1단계 `acl_recheck` — 반환 직전 ACL 재검증(원칙(a): 주체·가시성·등급·유효기간).

역할: `RankedSet(postprocessed).results[]`의 `acl`(payload 역평탄화, `Acl1`) 또는 회수 힌트
(`revocation_hints`, Valkey `aclrev:{tenant_id}:{document_id}` 대역)로 `SecurityContext` 기준
허용/거부 주체, `visible_set`, `classification_max` 서열, `embargo_until`/`expires_at`을 다시
판정한다. 실패 항목은 `omitted{acl_denied}`로 빠지고, 통과 항목마다 `ContextItem.acl`(Acl2)
증적을 만든다.
설계 근거: 04-pipelines/17 §3.2(요약), 바이블 §9.1(pack 내부 고정 순서 1번째), 계약
`contracts/context_pack.AclRecheckReport`/`PackOmittedEntry`, `contracts/common_types.Acl2`.
구성: `RevocationHint` — 힌트 값 모양(이 문서 제안); `apply` — 재검증 실행.
불변식·주의: `retrieval`은 계층상 `rag_platform.security`를 import할 수 없다(import-linter
`layers`) — 이 모듈은 §10.2 (a) 예측을 자체 재현할 뿐 실제 Cedar 정책 엔진을 호출하지 않는다.
거부가 허용보다 항상 우선한다(`Acl.deny_principals`).
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types
from rag_platform.contracts.context_pack import AclRecheckReport, PackOmittedEntry

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rag_platform.contracts.common_types import Acl1, RankedResult, SecurityContext

__all__ = ["RevocationHint", "apply"]

_CLASSIFICATION_ORDER: tuple[common_types.Classification, ...] = tuple(common_types.Classification)


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


@dataclass(frozen=True)
class RevocationHint:
    """Valkey `aclrev:{tenant_id}:{document_id}` 힌트 값(문서 §3.2).

    `acl_hash`가 payload와 다르면 이 값으로 재판정한다. `deleted=True`면 무조건 거부.
    """

    acl_hash: str
    allow: Sequence[str]
    deny: Sequence[str]
    visibility: common_types.Visibility
    classification: common_types.Classification
    embargo_until: str | None = None
    expires_at: str | None = None
    deleted: bool = False


def _denied_by(principals: Sequence[str], deny: Sequence[str]) -> bool:
    """거부 목록 판정(§10.1) — `deny` 항목이 `tenant:*`(잠금)이거나 호출자 주체 중 하나면 거부."""
    return any(d == "tenant:*" or d in principals for d in deny)


def _allowed_by(principals: Sequence[str], allow: Sequence[str]) -> bool:
    """허용 목록 판정 — 리터럴 멤버십만 본다(§10.2(a) `acl_allow ANY :principals`).

    `tenant:*`를 무조건 일치시키지 않는다 — 그러면 OR 결합(`_evaluate`)에서 `visible_set`이 이
    `visibility`를 제외한 service 전용 주체에게까지 allow 목록을 통해 새어 들어간다(리뷰 지적).
    """
    return any(a in principals for a in allow)


def _within_classification(
    classification: common_types.Classification, classification_max: common_types.Classification
) -> bool:
    return _CLASSIFICATION_ORDER.index(classification) <= _CLASSIFICATION_ORDER.index(classification_max)


def _evaluate(
    *,
    allow: Sequence[str],
    deny: Sequence[str],
    visibility: common_types.Visibility,
    classification: common_types.Classification,
    embargo_until: str | None,
    expires_at: str | None,
    security: SecurityContext,
) -> bool:
    """바이블 §10.2(a)를 그대로 재현한다: 거부 우선, 그 다음 `(visible_set 포함 OR allow 일치)`.

    §10.1: `visibility=public`은 allow 검사를 생략(항상 이 OR 조건을 만족)하고, `tenant`은 인증된
    사용자 주체 전원(= `visible_set`에 포함), `restricted`는 `allow`에 포함된 주체만. 세 값 모두
    `deny`가 항상 우선하고, embargo/expires/classification은 별도로 계속 검사한다.
    """
    principals = [_root(p) for p in security.principals]
    if _denied_by(principals, deny):
        return False
    if visibility not in security.visible_set and not _allowed_by(principals, allow):
        return False
    if not _within_classification(classification, security.classification_max):
        return False
    as_of = _root(security.as_of)
    if embargo_until is not None and as_of < embargo_until:
        return False
    return not (expires_at is not None and as_of >= expires_at)


def _deny(r: RankedResult) -> PackOmittedEntry:
    return PackOmittedEntry(
        chunk_id=r.chunk_id,
        collection_id=r.collection_id,
        document_id=r.document_id,
        reason=common_types.OmitReason.acl_denied,
    )


def _acl2(
    classification: common_types.Classification, *, source: common_types.AclCheckSource, checked_at: str
) -> common_types.Acl2:
    return common_types.Acl2(classification=classification, checked=True, checked_at=checked_at, source=source)


def apply(
    candidates: Sequence[RankedResult],
    security: SecurityContext,
    *,
    revocation_hints: Mapping[str, RevocationHint] | None = None,
) -> tuple[list[RankedResult], list[PackOmittedEntry], AclRecheckReport, dict[str, common_types.Acl2]]:
    """문서 §3.2 `acl_recheck(candidates, security_context, ctx)`의 구현."""
    revocation_hints = revocation_hints or {}
    as_of = _root(security.as_of)
    passed: list[RankedResult] = []
    denied: list[PackOmittedEntry] = []
    acl2_by_chunk_id: dict[str, common_types.Acl2] = {}
    hint_hits = 0

    for r in candidates:
        acl: Acl1 | None = r.acl
        hint = revocation_hints.get(_root(r.document_id))
        hint_typed: RevocationHint | None = hint  # type: ignore[assignment]
        hash_differs = hint_typed is not None and (acl is None or hint_typed.acl_hash != _root(acl.acl_hash))
        if hint_typed is not None and hint_typed.deleted:
            # 삭제는 ACL을 바꾸지 않으므로 acl_hash가 payload와 같아도 무조건 거부한다(E9, §9.1
            # "deleted=True면 무조건 거부" — 문서 §3.2 골든 시나리오 "삭제 → 전파 전 질의 → 미반환").
            if hash_differs:
                hint_hits += 1
            denied.append(_deny(r))
            continue
        if hash_differs:
            hint_hits += 1
            ok = _evaluate(
                allow=hint_typed.allow,
                deny=hint_typed.deny,
                visibility=hint_typed.visibility,
                classification=hint_typed.classification,
                embargo_until=hint_typed.embargo_until,
                expires_at=hint_typed.expires_at,
                security=security,
            )
            if ok:
                passed.append(r)
                acl2_by_chunk_id[_root(r.chunk_id)] = _acl2(
                    hint_typed.classification, source=common_types.AclCheckSource.revocation_hint, checked_at=as_of
                )
            else:
                denied.append(_deny(r))
            continue
        if acl is None:
            denied.append(_deny(r))
            continue
        ok = _evaluate(
            allow=[_root(a) for a in acl.allow],
            deny=[_root(d) for d in acl.deny],
            visibility=acl.visibility,
            classification=acl.classification,
            embargo_until=_root(acl.embargo_until) if acl.embargo_until is not None else None,
            expires_at=_root(acl.expires_at) if acl.expires_at is not None else None,
            security=security,
        )
        if ok:
            passed.append(r)
            acl2_by_chunk_id[_root(r.chunk_id)] = _acl2(
                acl.classification, source=common_types.AclCheckSource.payload, checked_at=as_of
            )
        else:
            denied.append(_deny(r))

    report = AclRecheckReport(checked=len(candidates), denied=len(denied), hint_hits=hint_hits)
    return passed, denied, report, acl2_by_chunk_id
