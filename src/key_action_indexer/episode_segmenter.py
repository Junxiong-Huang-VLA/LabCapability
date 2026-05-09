from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from .chinese_index import refresh_micro_row_chinese_index, refresh_segment_chinese_index
from .clip_extractor import extract_multiview_clips
from .description_builder import build_segment_description
from .evidence import apply_segment_evidence
from .micro_segmenter import micro_row_to_vector_metadata
from .schemas import (
    DetectedSegment,
    KeyActionSegment,
    SessionManifest,
    VideoSource,
    read_jsonl,
    to_json_dict,
    write_jsonl,
)
from .time_alignment import find_dialogue_for_segment, local_sec_to_global_time, parse_time
from .transcript import TranscriptUtterance
from .vector_index import VectorIndex
from .video_utils import get_video_duration_sec


EPISODE_SCHEMA_VERSION = "key_action_experiment_episode.v2"
SUMMARY_SCHEMA_VERSION = "key_action_episode_segmentation_summary.v1"


def rebuild_episode_segments_from_micro_evidence(
    *,
    manifest: SessionManifest,
    session_dir: str | Path,
    key_segments: list[KeyActionSegment],
    micro_rows: list[dict[str, Any]],
    yolo_frame_rows: list[dict[str, Any]] | None,
    utterances: list[TranscriptUtterance],
    detector_summary: dict[str, Any] | None = None,
    dry_run: bool = False,
    gap_sec: float = 7.0,
    pre_roll_sec: float = 2.0,
    post_roll_sec: float = 3.0,
    min_episode_duration_sec: float = 6.0,
    min_micro_evidence_count: int = 2,
) -> dict[str, Any]:
    """Rebuild parent key-action segments as true experiment episodes.

    The detector may return one coarse segment covering most of a long video.
    This pass treats YOLO-backed micro windows as the source of truth, clusters
    them into operation episodes, and rewrites all parent/micro/index artifacts.
    """

    session_root = Path(session_dir)
    metadata_dir = session_root / "metadata"
    episode_specs = _episode_specs_from_micros(
        manifest,
        micro_rows,
        gap_sec=gap_sec,
        pre_roll_sec=pre_roll_sec,
        post_roll_sec=post_roll_sec,
        min_episode_duration_sec=min_episode_duration_sec,
        min_micro_evidence_count=min_micro_evidence_count,
    )
    if not episode_specs:
        summary = {
            "schema_version": SUMMARY_SCHEMA_VERSION,
            "rebuilt": False,
            "reason": "insufficient_yolo_micro_evidence",
            "episode_count": 0,
            "micro_segment_count": len(micro_rows),
            "min_micro_evidence_count": min_micro_evidence_count,
        }
        _write_json(metadata_dir / "episode_segmentation_summary.json", summary)
        return summary

    source_duration_sec = _source_duration_sec(manifest, episode_specs, key_segments, micro_rows)
    episode_segments = [
        _detected_segment_from_spec(manifest, spec, index, source_duration_sec=source_duration_sec)
        for index, spec in enumerate(episode_specs, start=1)
    ]
    episode_key_segments: list[KeyActionSegment] = []
    for segment in episode_segments:
        key_segment = extract_multiview_clips(
            manifest=manifest,
            segment=segment,
            clips_dir=session_root / "clips" / "episodes",
            keyframes_dir=session_root / "keyframes" / "episodes",
            yolo_frame_rows=yolo_frame_rows,
            dry_run=dry_run,
        )
        dialogue = find_dialogue_for_segment(segment.global_start_time, segment.global_end_time, utterances)
        key_segment = build_segment_description(key_segment, dialogue)
        key_segment = apply_segment_evidence(key_segment)
        refresh_segment_chinese_index(key_segment)
        episode_key_segments.append(key_segment)

    remapped_micros, micro_map = _remap_micro_rows_to_episodes(manifest, micro_rows, episode_specs)
    _attach_micro_refs_to_parent_dicts(episode_key_segments, remapped_micros)
    for key_segment in episode_key_segments:
        refresh_segment_chinese_index(key_segment)

    segment_rows = _segment_dicts(episode_key_segments, episode_specs, source_duration_sec)
    remapped_micros = [refresh_micro_row_chinese_index(row) for row in remapped_micros]
    _attach_micro_refs_to_segment_rows(segment_rows, remapped_micros)
    episode_rows = _episode_rows(manifest, segment_rows, episode_specs, detector_summary or {}, source_duration_sec)

    write_jsonl(metadata_dir / "key_action_segments.jsonl", segment_rows)
    write_jsonl(metadata_dir / "micro_segments.jsonl", remapped_micros)
    write_jsonl(metadata_dir / "experiment_episodes.jsonl", episode_rows)
    write_jsonl(session_root / "cv_outputs" / "detected_segments.jsonl", episode_segments)

    segment_vectors = [_segment_vector_metadata_from_row(row) for row in segment_rows]
    micro_vectors = [micro_row_to_vector_metadata(row) for row in remapped_micros]
    combined_vectors = [*segment_vectors, *micro_vectors]
    write_jsonl(metadata_dir / "vector_metadata.jsonl", combined_vectors)
    write_jsonl(metadata_dir / "micro_vector_metadata.jsonl", micro_vectors)
    _rebuild_indexes(session_root, segment_vectors, micro_vectors, combined_vectors)
    _rewrite_parent_segment_artifacts(session_root, micro_map)
    focus_summary = _write_first_episode_focus(manifest, session_root, episode_rows, dry_run=dry_run)

    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "rebuilt": True,
        "source": "yolo_micro_hand_object_windows",
        "episode_count": len(episode_rows),
        "micro_segment_count": len(remapped_micros),
        "source_video_duration_sec": source_duration_sec,
        "gap_sec": gap_sec,
        "pre_roll_sec": pre_roll_sec,
        "post_roll_sec": post_roll_sec,
        "micro_parent_remap_count": len(micro_map),
        "episode_ids": [row.get("episode_id") for row in episode_rows],
        "focus": focus_summary,
    }
    _write_json(metadata_dir / "episode_segmentation_summary.json", summary)
    return summary


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _session_sec(manifest: SessionManifest, global_time: str | None) -> float | None:
    if not global_time:
        return None
    try:
        return (parse_time(str(global_time)) - parse_time(manifest.session_start_time)).total_seconds()
    except Exception:
        return None


def _micro_interval(manifest: SessionManifest, row: Mapping[str, Any]) -> tuple[float, float] | None:
    start = _safe_float(row.get("start_sec"))
    end = _safe_float(row.get("end_sec"))
    if start is None:
        start = _session_sec(manifest, str(row.get("global_start_time") or ""))
    if end is None:
        end = _session_sec(manifest, str(row.get("global_end_time") or ""))
    if start is None or end is None or end <= start:
        return None
    return max(0.0, float(start)), max(0.0, float(end))


def _micro_primary_object(row: Mapping[str, Any]) -> str:
    interaction = row.get("interaction") if isinstance(row.get("interaction"), Mapping) else {}
    return str(row.get("primary_object") or interaction.get("primary_object") or "").strip()


def _micro_has_physical_evidence(row: Mapping[str, Any]) -> bool:
    if _micro_primary_object(row):
        return True
    interaction = row.get("interaction") if isinstance(row.get("interaction"), Mapping) else {}
    if interaction.get("detected_objects"):
        return True
    return bool(row.get("yolo_evidence"))


def _episode_specs_from_micros(
    manifest: SessionManifest,
    micro_rows: list[dict[str, Any]],
    *,
    gap_sec: float,
    pre_roll_sec: float,
    post_roll_sec: float,
    min_episode_duration_sec: float,
    min_micro_evidence_count: int,
) -> list[dict[str, Any]]:
    candidates = []
    for row in micro_rows:
        if not isinstance(row, dict) or not _micro_has_physical_evidence(row):
            continue
        interval = _micro_interval(manifest, row)
        if interval is None:
            continue
        candidates.append(
            {
                "row": row,
                "start": interval[0],
                "end": interval[1],
                "primary_object": _micro_primary_object(row),
                "micro_segment_id": row.get("micro_segment_id"),
            }
        )
    candidates.sort(key=lambda item: (float(item["start"]), float(item["end"])))
    if len(candidates) < max(1, min_micro_evidence_count):
        return []

    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_end = 0.0
    for item in candidates:
        start = float(item["start"])
        end = float(item["end"])
        if current and start - current_end > gap_sec:
            clusters.append(current)
            current = []
        current.append(item)
        current_end = max(current_end, end)
    if current:
        clusters.append(current)

    specs: list[dict[str, Any]] = []
    source_duration = _duration_from_videos(manifest)
    for cluster in clusters:
        raw_start = min(float(item["start"]) for item in cluster)
        raw_end = max(float(item["end"]) for item in cluster)
        start = max(0.0, raw_start - max(0.0, pre_roll_sec))
        end = raw_end + max(0.0, post_roll_sec)
        if source_duration:
            end = min(float(source_duration), end)
        if end - start < min_episode_duration_sec:
            deficit = min_episode_duration_sec - (end - start)
            start = max(0.0, start - deficit / 2.0)
            end = end + deficit / 2.0
            if source_duration:
                end = min(float(source_duration), end)
        objects = Counter(str(item.get("primary_object") or "") for item in cluster if item.get("primary_object"))
        specs.append(
            {
                "start_sec": round(start, 6),
                "end_sec": round(max(end, start + 0.1), 6),
                "true_start_sec": round(raw_start, 6),
                "true_end_sec": round(raw_end, 6),
                "duration_sec": round(max(end - start, 0.1), 6),
                "micro_segment_ids": [str(item.get("micro_segment_id")) for item in cluster if item.get("micro_segment_id")],
                "primary_objects": dict(objects),
                "anchor_micro_segment_id": cluster[0].get("micro_segment_id"),
                "anchor_primary_object": cluster[0].get("primary_object"),
            }
        )

    return _merge_overlapping_episode_specs(specs, source_duration)


def _merge_overlapping_episode_specs(specs: list[dict[str, Any]], source_duration: float | None) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for spec in sorted(specs, key=lambda item: float(item["start_sec"])):
        if not merged or float(spec["start_sec"]) > float(merged[-1]["end_sec"]) + 0.25:
            merged.append(dict(spec))
            continue
        target = merged[-1]
        target["end_sec"] = round(max(float(target["end_sec"]), float(spec["end_sec"])), 6)
        if source_duration:
            target["end_sec"] = round(min(float(source_duration), float(target["end_sec"])), 6)
        target["true_end_sec"] = round(max(float(target["true_end_sec"]), float(spec["true_end_sec"])), 6)
        target["duration_sec"] = round(float(target["end_sec"]) - float(target["start_sec"]), 6)
        target["micro_segment_ids"] = [*target.get("micro_segment_ids", []), *spec.get("micro_segment_ids", [])]
        objects = Counter(target.get("primary_objects") or {})
        objects.update(spec.get("primary_objects") or {})
        target["primary_objects"] = dict(objects)
    return merged


def _duration_from_videos(manifest: SessionManifest) -> float | None:
    durations: list[float] = []
    for source in manifest.videos.all_sources().values():
        try:
            durations.append(float(get_video_duration_sec(source.path)))
        except Exception:
            continue
    return max(durations) if durations else None


def _source_duration_sec(
    manifest: SessionManifest,
    episode_specs: list[dict[str, Any]],
    key_segments: list[KeyActionSegment],
    micro_rows: list[dict[str, Any]],
) -> float:
    duration = _duration_from_videos(manifest)
    if duration and duration > 0:
        return round(float(duration), 6)
    ends: list[float] = []
    ends.extend(float(spec.get("end_sec") or 0.0) for spec in episode_specs)
    for segment in key_segments:
        cv = getattr(segment, "cv_detection", None)
        ends.append(float(getattr(cv, "end_sec", 0.0) or 0.0))
    for row in micro_rows:
        interval = _micro_interval(manifest, row)
        if interval:
            ends.append(interval[1])
    return round(max(ends, default=0.0), 6)


def _detected_segment_from_spec(
    manifest: SessionManifest,
    spec: dict[str, Any],
    index: int,
    *,
    source_duration_sec: float,
) -> DetectedSegment:
    start_sec = float(spec["start_sec"])
    end_sec = min(float(source_duration_sec), float(spec["end_sec"])) if source_duration_sec else float(spec["end_sec"])
    global_start = local_sec_to_global_time(VideoSource("session", "session", manifest.session_start_time), start_sec)
    global_end = local_sec_to_global_time(VideoSource("session", "session", manifest.session_start_time), end_sec)
    object_counts = dict(spec.get("primary_objects") or {})
    support_count = len(spec.get("micro_segment_ids") or [])
    return DetectedSegment(
        segment_id=f"episode_{index:06d}",
        start_sec=start_sec,
        end_sec=end_sec,
        duration_sec=round(end_sec - start_sec, 6),
        global_start_time=global_start.isoformat(),
        global_end_time=global_end.isoformat(),
        avg_motion_score=0.0,
        avg_active_score=1.0 if support_count else 0.0,
        start_reason="yolo_micro_physical_evidence_start",
        end_reason="yolo_micro_physical_evidence_end",
        review_required=False,
        detector_backend="yolo_episode",
        detector_source_view="multiview",
        yolo_label_counts=object_counts,
        yolo_interaction_count=support_count,
        boundary_confidence=1.0 if support_count else 0.0,
        boundary_support_count=support_count,
        boundary_source="micro_hand_object_episode_window",
    )


def _segment_interval(row: Mapping[str, Any]) -> tuple[float, float] | None:
    cv = row.get("cv_detection") if isinstance(row.get("cv_detection"), Mapping) else {}
    start = _safe_float(cv.get("start_sec"), _safe_float(row.get("start_sec")))
    end = _safe_float(cv.get("end_sec"), _safe_float(row.get("end_sec")))
    if start is None or end is None or end <= start:
        return None
    return float(start), float(end)


def _best_episode_for_micro(interval: tuple[float, float], specs: list[dict[str, Any]]) -> int | None:
    start, end = interval
    best_index: int | None = None
    best_overlap = 0.0
    for index, spec in enumerate(specs):
        ep_start = float(spec["start_sec"])
        ep_end = float(spec["end_sec"])
        overlap = max(0.0, min(end, ep_end) - max(start, ep_start))
        if overlap > best_overlap:
            best_overlap = overlap
            best_index = index
    if best_index is not None and best_overlap > 0.0:
        return best_index
    for index, spec in enumerate(specs):
        if float(spec["start_sec"]) <= start <= float(spec["end_sec"]):
            return index
    return None


def _remap_micro_rows_to_episodes(
    manifest: SessionManifest,
    micro_rows: list[dict[str, Any]],
    specs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    remapped: list[dict[str, Any]] = []
    micro_map: dict[str, str] = {}
    display_order_by_episode: Counter[str] = Counter()
    for row in sorted(micro_rows, key=lambda item: _micro_interval(manifest, item) or (0.0, 0.0)):
        interval = _micro_interval(manifest, row)
        if interval is None:
            continue
        episode_index = _best_episode_for_micro(interval, specs)
        if episode_index is None:
            continue
        episode_id = f"episode_{episode_index + 1:06d}"
        display_order_by_episode[episode_id] += 1
        item = dict(row)
        old_parent = str(item.get("parent_segment_id") or item.get("segment_id") or "")
        if item.get("micro_segment_id"):
            micro_map[str(item["micro_segment_id"])] = episode_id
        item["parent_segment_id"] = episode_id
        item["segment_id"] = episode_id
        item["episode_id"] = episode_id
        item["source_parent_segment_id"] = old_parent
        item["display_order"] = int(display_order_by_episode[episode_id])
        item["display_id"] = f"micro_{display_order_by_episode[episode_id]:03d}"
        _remap_micro_asset_bindings(item, episode_id)
        remapped.append(item)
    return remapped, micro_map


def _remap_micro_asset_bindings(row: dict[str, Any], episode_id: str) -> None:
    bindings = []
    for binding in row.get("asset_bindings") or []:
        if isinstance(binding, dict):
            item = dict(binding)
            item["parent_segment_id"] = episode_id
            item["segment_id"] = episode_id
            item["episode_id"] = episode_id
            bindings.append(item)
    row["asset_bindings"] = bindings


def _micro_ref(row: Mapping[str, Any]) -> dict[str, Any]:
    interaction = row.get("interaction") if isinstance(row.get("interaction"), Mapping) else {}
    keyframes = row.get("keyframes") if isinstance(row.get("keyframes"), Mapping) else {}
    first_person = row.get("first_person") if isinstance(row.get("first_person"), Mapping) else {}
    third_person = row.get("third_person") if isinstance(row.get("third_person"), Mapping) else {}
    quality = row.get("quality") if isinstance(row.get("quality"), Mapping) else {}
    evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
    return {
        "micro_segment_id": row.get("micro_segment_id"),
        "display_order": row.get("display_order"),
        "display_id": row.get("display_id"),
        "primary_object": interaction.get("primary_object") or row.get("primary_object"),
        "interaction_type": interaction.get("interaction_type") or row.get("interaction_type"),
        "global_start_time": row.get("global_start_time"),
        "global_end_time": row.get("global_end_time"),
        "duration_sec": row.get("duration_sec"),
        "max_interaction_score": interaction.get("max_interaction_score"),
        "confidence": quality.get("confidence") if isinstance(quality, Mapping) else None,
        "peak_keyframe": keyframes.get("peak_frame"),
        "first_person_clip": first_person.get("clip_path"),
        "third_person_clip": third_person.get("clip_path"),
        "manual_corrected": row.get("manual_corrected", False),
        "dialogue_context_available": row.get("dialogue_context_available", False),
        "dialogue_match_window_sec": row.get("dialogue_match_window_sec"),
        "dialogue_keywords": row.get("dialogue_keywords", []),
        "evidence_level": evidence.get("evidence_level") or row.get("evidence_level"),
        "evidence": evidence,
        "asset_bindings": row.get("asset_bindings", []),
        "yolo_evidence": row.get("yolo_evidence", []),
        "class_threshold": row.get("class_threshold", {}),
        "merged_from_micro_segment_ids": row.get("merged_from_micro_segment_ids", []),
        "merge_reason": row.get("merge_reason"),
    }


def _attach_micro_refs_to_parent_dicts(key_segments: list[KeyActionSegment], micro_rows: list[dict[str, Any]]) -> None:
    refs_by_parent: dict[str, list[dict[str, Any]]] = {}
    for row in micro_rows:
        refs_by_parent.setdefault(str(row.get("parent_segment_id") or ""), []).append(_micro_ref(row))
    for segment in key_segments:
        segment.micro_segments = sorted(
            refs_by_parent.get(segment.segment_id, []),
            key=lambda item: int(item.get("display_order") or 0),
        )


def _attach_micro_refs_to_segment_rows(segment_rows: list[dict[str, Any]], micro_rows: list[dict[str, Any]]) -> None:
    refs_by_parent: dict[str, list[dict[str, Any]]] = {}
    for row in micro_rows:
        refs_by_parent.setdefault(str(row.get("parent_segment_id") or ""), []).append(_micro_ref(row))
    for row in segment_rows:
        row["micro_segments"] = sorted(
            refs_by_parent.get(str(row.get("segment_id") or ""), []),
            key=lambda item: int(item.get("display_order") or 0),
        )


def _segment_dicts(
    key_segments: list[KeyActionSegment],
    specs: list[dict[str, Any]],
    source_duration_sec: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, key_segment in enumerate(key_segments):
        row = to_json_dict(key_segment)
        spec = specs[index]
        row["episode_id"] = key_segment.segment_id
        row["parent_kind"] = "experiment_episode"
        row["source_video_duration_sec"] = source_duration_sec
        row["episode_segmentation"] = {
            "schema_version": EPISODE_SCHEMA_VERSION,
            "source": "yolo_micro_hand_object_windows",
            "true_start_sec": spec.get("true_start_sec"),
            "true_end_sec": spec.get("true_end_sec"),
            "anchor_micro_segment_id": spec.get("anchor_micro_segment_id"),
            "anchor_primary_object": spec.get("anchor_primary_object"),
            "micro_segment_ids": spec.get("micro_segment_ids", []),
            "primary_objects": spec.get("primary_objects", {}),
        }
        rows.append(row)
    return rows


def _episode_rows(
    manifest: SessionManifest,
    segment_rows: list[dict[str, Any]],
    specs: list[dict[str, Any]],
    detector_summary: Mapping[str, Any],
    source_duration_sec: float,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, segment in enumerate(segment_rows, start=1):
        cv = segment.get("cv_detection") if isinstance(segment.get("cv_detection"), Mapping) else {}
        spec = specs[index - 1]
        rows.append(
            {
                "schema_version": EPISODE_SCHEMA_VERSION,
                "session_id": manifest.session_id,
                "episode_id": f"episode_{index:06d}",
                "segment_id": segment.get("segment_id"),
                "global_start_time": segment.get("global_start_time"),
                "global_end_time": segment.get("global_end_time"),
                "session_start_sec": cv.get("start_sec"),
                "session_end_sec": cv.get("end_sec"),
                "true_start_sec": spec.get("true_start_sec"),
                "true_end_sec": spec.get("true_end_sec"),
                "duration_sec": segment.get("duration_sec"),
                "source_video_duration_sec": source_duration_sec,
                "detector_backend": "yolo_episode",
                "detector_source_view": "multiview",
                "start_reason": cv.get("start_reason"),
                "end_reason": cv.get("end_reason"),
                "boundary_source": "micro_hand_object_episode_window",
                "view_alignment": dict(detector_summary.get("view_alignment") or {}),
                "micro_segment_ids": spec.get("micro_segment_ids", []),
                "primary_objects": spec.get("primary_objects", {}),
                "clips_by_view": {
                    "third_person": segment.get("third_person"),
                    "first_person": segment.get("first_person"),
                },
                "interpretation": "true_experiment_episode_from_yolo_micro_evidence",
            }
        )
    return rows


def _segment_vector_metadata_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    text = row.get("text_description") if isinstance(row.get("text_description"), Mapping) else {}
    index_info = row.get("index") if isinstance(row.get("index"), Mapping) else {}
    third = row.get("third_person") if isinstance(row.get("third_person"), Mapping) else {}
    first = row.get("first_person") if isinstance(row.get("first_person"), Mapping) else {}
    evidence = row.get("evidence") if isinstance(row.get("evidence"), Mapping) else {}
    micro_refs = [item for item in row.get("micro_segments") or [] if isinstance(item, Mapping)]
    primary_object = next((str(item.get("primary_object")) for item in micro_refs if item.get("primary_object")), None)
    interaction_type = next((str(item.get("interaction_type")) for item in micro_refs if item.get("interaction_type")), None)
    detected_objects = sorted(
        {
            str(value)
            for item in micro_refs
            for value in [item.get("primary_object"), *(item.get("evidence", {}).get("detected_objects", []) if isinstance(item.get("evidence"), Mapping) else [])]
            if value
        }
    )
    return {
        "index_level": "segment",
        "embedding_id": index_info.get("embedding_id") or f"emb_{row.get('segment_id')}",
        "segment_id": row.get("segment_id"),
        "session_id": row.get("session_id"),
        "index_text": index_info.get("index_text") or text.get("summary") or "",
        "global_start_time": row.get("global_start_time"),
        "global_end_time": row.get("global_end_time"),
        "third_person_clip": third.get("clip_path"),
        "first_person_clip": first.get("clip_path"),
        "related_dialogue": row.get("dialogue_context", []),
        "action_type": text.get("action_type"),
        "interaction_keyframes": row.get("interaction_keyframes", []),
        "interaction_events": row.get("interaction_events", []),
        "yolo_interactions": row.get("yolo_interactions", []),
        "asset_bindings": row.get("asset_bindings", []),
        "primary_object": primary_object,
        "interaction_type": interaction_type,
        "detected_objects": detected_objects,
        "evidence": evidence,
        "evidence_level": evidence.get("evidence_level"),
        "evidence_reasons": evidence.get("evidence_reasons", []),
        "limitations": evidence.get("limitations", []),
        "dialogue_context_available": bool(row.get("dialogue_context")),
        "dialogue_match_window_sec": row.get("dialogue_match_window_sec"),
        "dialogue_keywords": row.get("dialogue_keywords", []),
        "source_video_duration_sec": row.get("source_video_duration_sec"),
    }


def _rebuild_indexes(
    session_root: Path,
    segment_vectors: list[dict[str, Any]],
    micro_vectors: list[dict[str, Any]],
    combined_vectors: list[dict[str, Any]],
) -> None:
    index_root = session_root / "index"
    index = VectorIndex()
    index.build([str(item.get("index_text") or "") for item in combined_vectors], combined_vectors)
    index.save(index_root)
    write_jsonl(index_root / "docstore.jsonl", combined_vectors)
    segment_index = VectorIndex()
    segment_index.build([str(item.get("index_text") or "") for item in segment_vectors], segment_vectors)
    segment_index.save(index_root / "segments")
    micro_index = VectorIndex()
    micro_index.build([str(item.get("index_text") or "") for item in micro_vectors], micro_vectors)
    micro_index.save(index_root / "micro_segments")


def _rewrite_parent_segment_artifacts(session_root: Path, micro_map: dict[str, str]) -> None:
    for relative_path in (
        "metadata/model_observation_events.jsonl",
        "metadata/advanced_vision_evidence.jsonl",
        "metadata/video_understanding.jsonl",
        "metadata/unified_multimodal_timeline.jsonl",
    ):
        path = session_root / relative_path
        if not path.exists():
            continue
        try:
            rows = read_jsonl(path)
        except Exception:
            continue
        changed = False
        for row in rows:
            if not isinstance(row, dict):
                continue
            micro_id = str(row.get("micro_segment_id") or "")
            episode_id = micro_map.get(micro_id)
            if not episode_id:
                continue
            old_segment_id = str(row.get("segment_id") or row.get("parent_segment_id") or "")
            row["source_parent_segment_id"] = old_segment_id
            row["segment_id"] = episode_id
            row["parent_segment_id"] = episode_id
            row["episode_id"] = episode_id
            changed = True
        if changed:
            write_jsonl(path, rows)


def _write_first_episode_focus(
    manifest: SessionManifest,
    session_root: Path,
    episode_rows: list[dict[str, Any]],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if not episode_rows:
        summary = {"available": False, "reason": "no_episode"}
        _write_json(session_root / "metadata" / "experiment_focus_clips.json", summary)
        return summary
    first = episode_rows[0]
    window = {
        "schema_version": "experiment_focus_window.v1",
        "detected": True,
        "source": "first_true_experiment_episode",
        "episode_count": len(episode_rows),
        "episode_id": first.get("episode_id"),
        "segment_id": first.get("segment_id"),
        "start_sec": first.get("session_start_sec"),
        "true_start_sec": first.get("true_start_sec"),
        "end_sec": first.get("session_end_sec"),
        "duration_sec": first.get("duration_sec"),
        "global_start_time": first.get("global_start_time"),
        "global_end_time": first.get("global_end_time"),
        "anchor": {
            "source": "yolo_micro_episode",
            "episode_id": first.get("episode_id"),
            "segment_id": first.get("segment_id"),
            "primary_objects": first.get("primary_objects", {}),
        },
        "included_segment_ids": [first.get("segment_id")],
        "segment_count": 1,
    }
    _write_json(session_root / "metadata" / "experiment_focus_window.json", window)
    clip_rows = []
    clips_by_view = first.get("clips_by_view") if isinstance(first.get("clips_by_view"), Mapping) else {}
    for view, source in manifest.videos.all_sources().items():
        ref = clips_by_view.get(view)
        if not isinstance(ref, Mapping):
            continue
        clip_rows.append(
            {
                "view": view,
                "video_path": source.path,
                "clip_path": ref.get("clip_path"),
                "local_start_sec": ref.get("local_start_sec"),
                "local_end_sec": ref.get("local_end_sec"),
                "time_start_sec": first.get("session_start_sec"),
                "time_end_sec": first.get("session_end_sec"),
                "global_start_time": first.get("global_start_time"),
                "global_end_time": first.get("global_end_time"),
                "episode_id": first.get("episode_id"),
                "segment_id": first.get("segment_id"),
            }
        )
    summary = {
        "schema_version": "experiment_focus_clips.v1",
        "available": bool(clip_rows),
        "source": "first_true_experiment_episode",
        "window": window,
        "clips": clip_rows,
        "clips_by_view": {row["view"]: row for row in clip_rows},
    }
    _write_json(session_root / "metadata" / "experiment_focus_clips.json", summary)
    return summary


__all__ = ["rebuild_episode_segments_from_micro_evidence"]
