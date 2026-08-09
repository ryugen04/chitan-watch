from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from .master_diff import MasterRowChange
from .models import ArtifactType, CrawlerRunStatus, EvidenceLevel, Severity
from .run_state import ArtifactRunChange, CrawlerRunEvaluation


@dataclass(frozen=True)
class ChangeEvidence:
    type: str
    evidence_level: EvidenceLevel
    source_url: str
    description: str
    snapshot_id: str | None = None
    field: str | None = None
    before: Any = None
    after: Any = None


@dataclass(frozen=True)
class ChangeInterpretation:
    headline: str
    summary: str
    likely_impact: tuple[str, ...]
    recommended_action: str
    confidence: EvidenceLevel
    evidence_level: EvidenceLevel
    generated_by: str = "deterministic"
    needs_review: bool = False


@dataclass(frozen=True)
class ChangeEventCandidate:
    id: str
    jurisdiction: dict[str, str]
    program: dict[str, str]
    detected_at: str
    effective_from: str | None
    severity: Severity
    change_categories: tuple[str, ...]
    summary: str
    vendor_impacts: tuple[str, ...]
    evidence: tuple[ChangeEvidence, ...]
    source_run_status: CrawlerRunStatus
    interpretation: ChangeInterpretation
    review_required: bool = False
    source_context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ChangeEventBundle:
    run_id: str
    source_id: str
    generated_at: str
    events: tuple[ChangeEventCandidate, ...] = ()


def _stable_id(prefix: str, value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{prefix}_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _value(fields: dict[str, dict[str, Any]], item: str, side: str) -> str | None:
    raw = fields.get(item, {}).get(side)
    if raw in (None, ""):
        return None
    return str(raw)


def _identity_jurisdiction(identity: dict[str, str]) -> dict[str, str]:
    return {
        "prefecture_code": identity.get("prefecture_code", ""),
        "municipality_code": identity.get("municipality_code", ""),
    }


def _program(identity: dict[str, str], fields: dict[str, dict[str, Any]], side: str) -> dict[str, str]:
    return {
        "name": _value(fields, "item_1", side) or "地単公費マスター",
        "public_funding_number": identity.get("public_funding_number", ""),
        "classification": identity.get("program_subdivision_code", ""),
    }


def _field_evidence(change: MasterRowChange, source_url: str, snapshot_id: str | None) -> tuple[ChangeEvidence, ...]:
    evidence: list[ChangeEvidence] = []
    for field, delta in sorted(change.fields.items()):
        before = delta.get("before")
        after = delta.get("after")
        if before == "" and after == "":
            continue
        evidence.append(
            ChangeEvidence(
                type="master_field_diff",
                evidence_level=EvidenceLevel.CONFIRMED,
                source_url=source_url,
                snapshot_id=snapshot_id,
                field=field,
                before=before,
                after=after,
                description=f"{field} changed in positional master diff",
            )
        )
    return tuple(evidence)


def _severity_for_row_change(change: MasterRowChange) -> Severity:
    if change.type == "row_ambiguous":
        return Severity.HIGH
    if change.type in {"row_added", "row_removed"}:
        return Severity.MEDIUM
    changed_fields = set(change.fields)
    if changed_fields & {"item_10", "item_11"}:
        return Severity.HIGH
    if changed_fields & {"item_1", "item_8", "item_9"}:
        return Severity.MEDIUM
    return Severity.LOW


def _category_for_row_change(change: MasterRowChange) -> tuple[str, ...]:
    if change.type == "row_added":
        return ("master-row-added",)
    if change.type == "row_removed":
        return ("master-row-removed",)
    if change.type == "row_ambiguous":
        return ("admin-review", "ambiguous-master-row-match")
    categories = ["master-row-modified"]
    if any(field in change.fields for field in ("item_10", "item_11")):
        categories.append("validity-period")
    if "item_1" in change.fields:
        categories.append("program-name")
    return tuple(categories)


def _impacts_for(change: MasterRowChange, severity: Severity) -> tuple[str, ...]:
    impacts = ["master-import"]
    if severity in {Severity.HIGH, Severity.CRITICAL}:
        impacts.extend(["eligibility-determination", "patient-registration"])
    if change.type == "row_ambiguous":
        impacts.append("admin-review")
    return tuple(dict.fromkeys(impacts))


def _place_label(identity: dict[str, str]) -> str:
    prefecture = identity.get("prefecture_code") or "都道府県未特定"
    municipality = identity.get("municipality_code") or ""
    return f"{prefecture}-{municipality}" if municipality else prefecture


def _evidence_level(evidence: tuple[ChangeEvidence, ...]) -> EvidenceLevel:
    if not evidence:
        return EvidenceLevel.UNRESOLVED
    levels = {item.evidence_level for item in evidence}
    if EvidenceLevel.UNRESOLVED in levels:
        return EvidenceLevel.UNRESOLVED
    if EvidenceLevel.INFERRED in levels:
        return EvidenceLevel.INFERRED
    if EvidenceLevel.CORROBORATED in levels:
        return EvidenceLevel.CORROBORATED
    return EvidenceLevel.CONFIRMED


def _row_change_label(change_type: str) -> str:
    return {
        "row_added": "追加",
        "row_removed": "削除",
        "row_modified": "変更",
        "row_ambiguous": "要確認の差分",
    }.get(change_type, "変更")


def _field_labels(fields: dict[str, dict[str, Any]]) -> tuple[str, ...]:
    labels = {
        "item_1": "制度名",
        "item_8": "公費負担者番号",
        "item_9": "制度区分",
        "item_10": "開始日",
        "item_11": "終了日",
    }
    values = [labels.get(field, "その他項目") for field in sorted(fields)]
    return tuple(dict.fromkeys(values))


def interpretation_for_master_change(
    change: MasterRowChange,
    program: dict[str, str],
    effective_from: str | None,
    severity: Severity,
    evidence: tuple[ChangeEvidence, ...],
) -> ChangeInterpretation:
    place = _place_label(change.identity)
    program_name = program.get("name") or "地単公費マスター"
    change_label = _row_change_label(change.type)
    fields = _field_labels(change.fields)
    field_text = "、".join(fields) if fields else "行全体"
    if change.type == "row_ambiguous":
        return ChangeInterpretation(
            headline=f"{place} の {program_name} に確認が必要な差分があります",
            summary="同じ業務キーに複数候補があり、システムだけでは変更前後の対応を安全に確定できません。",
            likely_impact=("自動取り込み前に担当者レビューが必要です。", "マスター更新の判断を保留してください。"),
            recommended_action="詳細画面で候補行と公式ソースを確認し、対応関係を人手で確定してください。",
            confidence=EvidenceLevel.UNRESOLVED,
            evidence_level=_evidence_level(evidence),
            needs_review=True,
        )
    impact = ["レセコン・請求システムの地単公費マスター更新確認が必要な可能性があります。"]
    if severity in {Severity.HIGH, Severity.CRITICAL}:
        impact.append("資格確認、患者登録、請求判定に影響する可能性があります。")
    elif change.type in {"row_added", "row_removed"}:
        impact.append("対象制度の有効/無効扱いを運用前に確認してください。")
    if effective_from:
        impact.append(f"施行日または適用開始日は {effective_from} として検知されています。")
    return ChangeInterpretation(
        headline=f"{place} の {program_name} が{change_label}されています",
        summary=f"公式マスターの{field_text}に{change_label}を検知しました。",
        likely_impact=tuple(impact),
        recommended_action="公式ソースの詳細と差分項目を確認し、利用中のマスター更新手順に沿って反映可否を判断してください。",
        confidence=EvidenceLevel.CONFIRMED,
        evidence_level=_evidence_level(evidence),
        needs_review=False,
    )


def _artifact_kind_label(artifact_type: ArtifactType) -> str:
    return {
        ArtifactType.MASTER_CSV: "地単公費マスター CSV",
        ArtifactType.MASTER_EXCEL: "地単公費マスター Excel",
        ArtifactType.SCHEMA: "項目一覧",
        ArtifactType.INPUT_GUIDE: "入力要領",
        ArtifactType.MANUAL: "操作マニュアル",
        ArtifactType.EXAMPLES: "入力例",
        ArtifactType.FAQ: "FAQ",
        ArtifactType.MHLW_DOCUMENT: "厚労省資料",
        ArtifactType.HTML: "公式ページ",
        ArtifactType.OTHER: "公式資料",
    }.get(artifact_type, "公式資料")


SOURCE_LAYER_LABELS = {
    "master-latest-data": "地単公費マスター最新データ",
    "master-registration-operation": "登録・運用資料",
    "policy-faq": "制度背景・説明会・FAQ",
    "reference-portal": "公費負担医療制度マスター入口",
    "site-news-health": "公式サイト更新情報の補助確認",
    "municipality-policy-context": "自治体制度文脈",
    "municipality-policy-seed": "自治体制度ページ seed",
    "policy-context": "制度・政策文脈",
    "pmh-online-qualification": "PMH/オンライン資格確認",
    "master-publication": "地単公費マスター公開",
    "claim-processing": "審査支払・請求運用",
    "municipality-policy": "自治体個別制度",
    "source-health": "ソース管理",
}

CURRENT_NOTIFICATION_SOURCE_LAYERS = {
    "master-latest-data",
    "master-registration-operation",
    "policy-faq",
    "reference-portal",
    "site-news-health",
    "municipality-policy-context",
}


SOURCE_OWNER_LABELS = {
    "ssk": "社会保険診療報酬支払基金",
    "mhlw": "厚生労働省",
    "digital-agency": "デジタル庁",
    "shinryohoshu": "診療報酬情報提供サービス",
    "municipality": "自治体公式サイト",
    "kokuho": "国保中央会/国保連系情報",
    "unknown": "公式ソース",
}


def _source_layer_label(value: str | None) -> str:
    return SOURCE_LAYER_LABELS.get(value or "", value or "公式ソース")


def _source_owner_label(value: str | None) -> str:
    return SOURCE_OWNER_LABELS.get(value or "", value or "公式ソース")


def event_in_current_notification_scope(event: dict[str, Any]) -> bool:
    layers: set[str] = set()
    source_context = event.get("source_context") if isinstance(event.get("source_context"), dict) else {}
    if source_context.get("source_layer"):
        layers.add(str(source_context["source_layer"]))
    for category in event.get("change_categories") or ():
        category_text = str(category)
        if category_text.startswith("source-layer:"):
            layers.add(category_text.removeprefix("source-layer:"))
    return not layers or all(layer in CURRENT_NOTIFICATION_SOURCE_LAYERS for layer in layers)


def _artifact_change_in_current_notification_scope(change: ArtifactRunChange) -> bool:
    return not change.source_layer or change.source_layer in CURRENT_NOTIFICATION_SOURCE_LAYERS


def _source_context(change: ArtifactRunChange) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "source_group": change.source_group,
            "source_layer": change.source_layer,
            "source_owner": change.source_owner,
            "source_role": change.source_role,
            "jurisdiction_scope": change.jurisdiction_scope,
            "monitor_mode": change.monitor_mode,
            "notify_policy": change.notify_policy,
            "review_policy": change.review_policy,
        }.items()
        if value
    }


def _artifact_likely_impact(change: ArtifactRunChange) -> tuple[str, ...]:
    layer = change.source_layer or ""
    if layer == "master-latest-data":
        if change.artifact_type == ArtifactType.MASTER_CSV:
            return ("最新データの基準日、CSV ファイル名、ファイル差分、行差分を確認し、現物給付の患者負担金計算に関係する変更か検証が必要です。",)
        if change.artifact_type == ArtifactType.MASTER_EXCEL:
            return ("人が確認する Excel 版の更新です。CSV と同じ基準日の確定事業一覧か、ファイル名・サイズ・内容差分を確認してください。",)
        return ("地単公費マスター最新データの入口やリンク構成が変わった可能性があります。",)
    if layer == "master-registration-operation":
        return ("自治体の新規登録・変更・廃止、変更6か月前の月末までの登録対応、項目定義、入力要領、FAQ、検証前提に関する運用資料が変わった可能性があります。",)
    if layer == "policy-faq":
        return ("厚労省の説明会資料、FAQ、対象範囲、現物給付化や自治体向け依頼内容が変わった可能性があります。",)
    if layer == "reference-portal":
        return ("診療報酬情報提供サービス側の公費負担医療制度マスター入口や、支払基金ページへの導線が変わった可能性があります。",)
    if layer == "site-news-health":
        return ("支払基金トップ更新情報の補助確認です。本命は titansys ページ側で、トップ掲載有無だけでは更新有無を確定しません。",)
    if layer == "municipality-policy-context":
        return ("自治体の制度ページにある対象者、受給者証、自己負担、現物給付、償還払い、申請、更新日などの文脈が変わった可能性があります。支払基金マスター本体の更新とは分けて確認してください。",)
    if layer == "municipality-policy-seed":
        return ("自治体個別制度の文脈確認用 seed です。RSS 通知ではなく Source Health で取得状態を確認し、マスター掲載内容の補助理解に使います。",)
    if layer == "pmh-online-qualification":
        return ("マイナンバーカードによる医療費助成資格確認、PMH 参加自治体、制度関連マスタ、医療機関導入状況の確認が必要な可能性があります。",)
    if layer == "municipality-policy":
        return ("自治体個別の制度説明、受給者証、自己負担、対象年齢、現物給付/償還払いの扱いが変わった可能性があります。",)
    if layer == "claim-processing":
        return ("審査支払機関への委託状況や請求運用の確認が必要な可能性があります。",)
    if layer == "master-publication" and change.artifact_type == ArtifactType.MASTER_EXCEL:
        return ("CSV と同等または補完的な公式マスターとして、CSV との差異確認が必要な可能性があります。",)
    if change.artifact_type == ArtifactType.SCHEMA:
        return ("項目定義の変更により、CSV パーサや差分解釈の見直しが必要な可能性があります。",)
    if change.artifact_type in {ArtifactType.INPUT_GUIDE, ArtifactType.MANUAL, ArtifactType.EXAMPLES, ArtifactType.FAQ}:
        return ("登録・運用ルールやレビュー観点が変わった可能性があります。",)
    if change.artifact_type == ArtifactType.MHLW_DOCUMENT:
        return ("制度運用や現物給付化の政策文脈が更新された可能性があります。",)
    if change.artifact_type == ArtifactType.HTML:
        return ("公式ページの掲載内容やリンク構成が変わった可能性があります。",)
    return ("地単公費関連の公式資料が更新された可能性があります。",)


def interpretation_for_artifact_change(change: ArtifactRunChange, evidence: tuple[ChangeEvidence, ...], severity: Severity) -> ChangeInterpretation:
    action = {
        "added": "公開資料を検知しました",
        "changed": "公開資料の更新を検知しました",
        "removed": "公開資料の削除を検知しました",
        "failed": "公開資料の確認に失敗しました",
    }.get(change.state, f"公開資料の状態を検知しました（{change.state}）")
    kind = _artifact_kind_label(change.artifact_type)
    if change.state == "failed":
        return ChangeInterpretation(
            headline=f"{change.title} の取得確認に失敗しました",
            summary="公式ソースの取得または検証でエラーが発生しました。監視状態の確認が必要です。",
            likely_impact=("この回の変更有無は確定できません。", "通知や自動更新判断を保留してください。"),
            recommended_action="公式ページへのアクセス可否とワークフローログを確認してください。",
            confidence=EvidenceLevel.UNRESOLVED,
            evidence_level=_evidence_level(evidence),
            needs_review=True,
        )
    layer = _source_layer_label(change.source_layer)
    owner = _source_owner_label(change.source_owner)
    return ChangeInterpretation(
        headline=f"{layer}: {kind} {change.title} の{action}",
        summary=f"{owner} の {layer} レイヤーで監視している公式ソースの状態変化です。",
        likely_impact=_artifact_likely_impact(change),
        recommended_action="詳細ページから公式ソース、ソース層、基準日、ファイル名、ファイル差分、CSV 行差分を確認し、現物給付マスター更新・登録運用資料・説明会/FAQ更新のどれに当たるかを切り分けてください。",
        confidence=EvidenceLevel.CONFIRMED,
        evidence_level=_evidence_level(evidence),
        needs_review=change.review_policy == "required",
    )


def event_from_master_change(run: CrawlerRunEvaluation, change: MasterRowChange, source_url: str, snapshot_id: str | None) -> ChangeEventCandidate:
    side = "after" if change.type != "row_removed" else "before"
    severity = _severity_for_row_change(change)
    categories = _category_for_row_change(change)
    evidence = _field_evidence(change, source_url, snapshot_id)
    if change.type == "row_ambiguous":
        evidence = (
            ChangeEvidence(
                type="ambiguous_master_match",
                evidence_level=EvidenceLevel.UNRESOLVED,
                source_url=source_url,
                snapshot_id=snapshot_id,
                description=change.reason or "Business identity requires Admin Review",
            ),
        )
    if not evidence:
        evidence = (
            ChangeEvidence(
                type="master_row_diff",
                evidence_level=EvidenceLevel.CONFIRMED,
                source_url=source_url,
                snapshot_id=snapshot_id,
                description=f"{change.type} detected in positional master diff",
            ),
        )
    program = _program(change.identity, change.fields, side)
    effective_from = _value(change.fields, "item_10", "after") or _value(change.fields, "item_10", side)
    summary = f"{program['name']} の地単公費マスター差分: {change.type}"
    interpretation = interpretation_for_master_change(change, program, effective_from, severity, evidence)
    return ChangeEventCandidate(
        id=_stable_id("chg", {"type": change.type, "identity": change.identity, "before": change.before_row_hash, "after": change.after_row_hash}),
        jurisdiction=_identity_jurisdiction(change.identity),
        program=program,
        detected_at=run.evaluated_at,
        effective_from=effective_from,
        severity=severity,
        change_categories=categories,
        summary=summary,
        vendor_impacts=_impacts_for(change, severity),
        evidence=evidence,
        source_run_status=run.status,
        interpretation=interpretation,
        review_required=change.type == "row_ambiguous",
    )


def _severity_for_artifact_change(change: ArtifactRunChange) -> Severity:
    if change.state == "failed":
        return Severity.HIGH
    if change.artifact_type in {ArtifactType.SCHEMA, ArtifactType.INPUT_GUIDE} and change.state in {"added", "changed", "removed"}:
        return Severity.MEDIUM
    return Severity.INFO if change.state == "unchanged" else Severity.LOW


def _category_for_artifact_change(change: ArtifactRunChange) -> tuple[str, ...]:
    categories = [f"artifact-{change.state}", f"artifact-type:{change.artifact_type.value}"]
    if change.artifact_type in {ArtifactType.SCHEMA, ArtifactType.INPUT_GUIDE, ArtifactType.MANUAL, ArtifactType.EXAMPLES, ArtifactType.FAQ, ArtifactType.MHLW_DOCUMENT, ArtifactType.OTHER, ArtifactType.HTML}:
        categories.append("document-update")
    if change.source_group:
        categories.append(f"source-group:{change.source_group}")
    if change.source_layer:
        categories.append(f"source-layer:{change.source_layer}")
    if change.source_owner:
        categories.append(f"source-owner:{change.source_owner}")
    if change.source_role:
        categories.append(f"source-role:{change.source_role}")
    return tuple(categories)


def event_from_artifact_change(run: CrawlerRunEvaluation, change: ArtifactRunChange) -> ChangeEventCandidate:
    severity = _severity_for_artifact_change(change)
    summary = f"Artifact {change.title} is {change.state}"
    evidence = (
        ChangeEvidence(
            type="artifact_snapshot",
            evidence_level=EvidenceLevel.CONFIRMED if change.state != "failed" else EvidenceLevel.UNRESOLVED,
            source_url=change.canonical_url,
            snapshot_id=change.current_snapshot_id,
            description=change.error or f"Artifact state is {change.state}; layer={change.source_layer or 'unknown'}; owner={change.source_owner or 'unknown'}; monitor={change.monitor_mode or 'file_hash'}; notify={change.notify_policy or 'always'}",
            before=change.previous_sha256,
            after=change.current_sha256,
        ),
    )
    interpretation = interpretation_for_artifact_change(change, evidence, severity)
    return ChangeEventCandidate(
        id=_stable_id("chg", {"artifact_id": change.artifact_id, "state": change.state, "sha": change.current_sha256, "error": change.error}),
        jurisdiction={"prefecture_code": "", "municipality_code": ""},
        program={"name": change.title, "classification": change.artifact_type.value, "public_funding_number": ""},
        detected_at=run.evaluated_at,
        effective_from=None,
        severity=severity,
        change_categories=_category_for_artifact_change(change),
        summary=summary,
        vendor_impacts=("source-monitoring",) if change.state == "failed" else ("source-monitoring", "document-review"),
        evidence=evidence,
        source_run_status=run.status,
        interpretation=interpretation,
        review_required=change.state == "failed" or change.review_policy == "required",
        source_context=_source_context(change),
    )


def build_change_event_bundle(run_id: str, run: CrawlerRunEvaluation) -> ChangeEventBundle:
    events: list[ChangeEventCandidate] = []
    master_snapshot_id = None
    source_url = "local://master-diff"
    master_diff_has_events = bool(run.master_diff and run.master_diff.diff and run.master_diff.diff.has_changes)
    if run.master_diff and run.master_diff.diff:
        source_url = run.master_diff.new_source
        for change in run.master_diff.diff.changes:
            events.append(event_from_master_change(run, change, source_url=source_url, snapshot_id=master_snapshot_id))
    for change in run.artifact_changes:
        if change.state == "unchanged":
            continue
        if change.notify_policy in {"health_only", "never"} and change.state != "failed":
            continue
        if not _artifact_change_in_current_notification_scope(change):
            continue
        if master_diff_has_events and change.artifact_type == ArtifactType.MASTER_CSV and change.state == "changed":
            continue
        events.append(event_from_artifact_change(run, change))
    if run.status in {CrawlerRunStatus.FAILED, CrawlerRunStatus.PARTIAL_FAILURE, CrawlerRunStatus.SCHEMA_BREAK} and not events:
        events.extend(event_from_artifact_change(run, change) for change in run.artifact_changes if change.state == "failed")
    return ChangeEventBundle(run_id=run_id, source_id=run.source_id, generated_at=run.evaluated_at, events=tuple(events))


def flatten_events(bundles: Iterable[ChangeEventBundle]) -> tuple[ChangeEventCandidate, ...]:
    events: list[ChangeEventCandidate] = []
    for bundle in bundles:
        events.extend(bundle.events)
    return tuple(events)
