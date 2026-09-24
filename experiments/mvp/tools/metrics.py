"""Reference metric implementations for E0 boundary verification."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def _validate_binary_inputs(y_true: Sequence[int], y_score: Sequence[float], threshold: float) -> None:
    if not y_true:
        raise ValueError("binary metrics require at least one observation")
    if len(y_true) != len(y_score):
        raise ValueError("y_true and y_score must have equal length")
    if any(label not in (0, 1) for label in y_true):
        raise ValueError("y_true values must be 0 or 1")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if any(not math.isfinite(score) or not 0 <= score <= 1 for score in y_score):
        raise ValueError("y_score values must be finite and between 0 and 1")


def _roc_auc(y_true: Sequence[int], y_score: Sequence[float]) -> float | None:
    positive_scores = [score for label, score in zip(y_true, y_score) if label == 1]
    negative_scores = [score for label, score in zip(y_true, y_score) if label == 0]
    if not positive_scores or not negative_scores:
        return None
    favorable_pairs = 0.0
    for positive in positive_scores:
        for negative in negative_scores:
            if positive > negative:
                favorable_pairs += 1.0
            elif positive == negative:
                favorable_pairs += 0.5
    return favorable_pairs / (len(positive_scores) * len(negative_scores))


def _eer(y_true: Sequence[int], y_score: Sequence[float]) -> float | None:
    positives = sum(y_true)
    negatives = len(y_true) - positives
    if positives == 0 or negatives == 0:
        return None

    points: list[tuple[float, float]] = [(0.0, 1.0)]
    tp = fp = 0
    grouped: dict[float, list[int]] = {}
    for label, score in zip(y_true, y_score):
        grouped.setdefault(score, []).append(label)
    for score in sorted(grouped, reverse=True):
        labels = grouped[score]
        tp += sum(labels)
        fp += len(labels) - sum(labels)
        fpr = fp / negatives
        fnr = 1.0 - tp / positives
        points.append((fpr, fnr))

    for current, following in zip(points, points[1:]):
        current_delta = current[1] - current[0]
        following_delta = following[1] - following[0]
        if current_delta == 0:
            return (current[0] + current[1]) / 2
        if following_delta == 0:
            return (following[0] + following[1]) / 2
        if current_delta * following_delta < 0:
            fraction = current_delta / (current_delta - following_delta)
            fpr = current[0] + fraction * (following[0] - current[0])
            fnr = current[1] + fraction * (following[1] - current[1])
            return (fpr + fnr) / 2
    raise RuntimeError("ROC curve did not cross the EER line")


def binary_metrics(
    y_true: Sequence[int], y_score: Sequence[float], *, threshold: float = 0.5
) -> dict[str, Any]:
    _validate_binary_inputs(y_true, y_score, threshold)
    predictions = [1 if score >= threshold else 0 for score in y_score]
    tp = sum(label == 1 and prediction == 1 for label, prediction in zip(y_true, predictions))
    tn = sum(label == 0 and prediction == 0 for label, prediction in zip(y_true, predictions))
    fp = sum(label == 0 and prediction == 1 for label, prediction in zip(y_true, predictions))
    fn = sum(label == 1 and prediction == 0 for label, prediction in zip(y_true, predictions))

    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    specificity = _safe_ratio(tn, tn + fp)
    balanced_accuracy = (
        (recall + specificity) / 2 if recall is not None and specificity is not None else None
    )
    return {
        "confusion": {"tp": tp, "tn": tn, "fp": fp, "fn": fn},
        "accuracy": (tp + tn) / len(y_true),
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": _safe_ratio(2 * tp, 2 * tp + fp + fn),
        "balanced_accuracy": balanced_accuracy,
        "roc_auc": _roc_auc(y_true, y_score),
        "eer": _eer(y_true, y_score),
    }


def latency_summary(durations_sec: Sequence[float]) -> dict[str, float | int]:
    """Summarize non-negative per-sample durations using linear percentiles."""

    if not durations_sec:
        raise ValueError("latency metrics require at least one duration")
    if any(not math.isfinite(value) or value < 0 for value in durations_sec):
        raise ValueError("latency durations must be finite and non-negative")
    ordered = sorted(durations_sec)

    def percentile(quantile: float) -> float:
        position = (len(ordered) - 1) * quantile
        lower_index = math.floor(position)
        upper_index = math.ceil(position)
        if lower_index == upper_index:
            return ordered[lower_index]
        fraction = position - lower_index
        return ordered[lower_index] + fraction * (ordered[upper_index] - ordered[lower_index])

    total = sum(ordered)
    return {
        "mean_sec": total / len(ordered),
        "median_sec": percentile(0.5),
        "p95_sec": percentile(0.95),
        "sum_sec": total,
        "count": len(ordered),
    }


def prediction_latency_metrics(
    predictions: Sequence[dict[str, Any]], *, timeout_cap_sec: float
) -> dict[str, float | int]:
    """Aggregate D-1 timing with timeouts charged at a preregistered cap."""

    if not math.isfinite(timeout_cap_sec) or timeout_cap_sec <= 0:
        raise ValueError("timeout_cap_sec must be finite and positive")
    durations: list[float] = []
    timeout_count = 0
    failure_count = 0
    success_count = 0
    for index, prediction in enumerate(predictions):
        status = prediction.get("status")
        if status == "ok":
            duration = prediction.get("processing_time_sec")
            if (
                not isinstance(duration, (int, float))
                or isinstance(duration, bool)
                or not math.isfinite(duration)
                or duration < 0
            ):
                raise ValueError(f"ok prediction at index {index} has invalid processing_time_sec")
            durations.append(float(duration))
            success_count += 1
        elif status == "timeout":
            durations.append(float(timeout_cap_sec))
            timeout_count += 1
        else:
            failure_count += 1
            duration = prediction.get("processing_time_sec")
            if duration is not None:
                if (
                    not isinstance(duration, (int, float))
                    or isinstance(duration, bool)
                    or not math.isfinite(duration)
                    or duration < 0
                ):
                    raise ValueError(
                        f"failed prediction at index {index} has invalid processing_time_sec"
                    )
                durations.append(float(duration))
    if not durations:
        raise ValueError("latency metrics require at least one ok or timeout prediction")
    summary = latency_summary(durations)
    attempted_count = len(predictions)
    return {
        **summary,
        "included_count": len(durations),
        "attempted_count": attempted_count,
        "success_count": success_count,
        "timeout_count": timeout_count,
        "failure_count": failure_count,
        "timeout_rate": timeout_count / attempted_count if attempted_count else 0.0,
        "failure_rate": failure_count / attempted_count if attempted_count else 0.0,
        "timeout_cap_sec": timeout_cap_sec,
    }


def realtime_rate(
    media_durations_sec: Sequence[float],
    predictions: Sequence[dict[str, Any]],
    *,
    timeout_cap_sec: float,
) -> dict[str, float | int]:
    """Compute D-2 from aligned temporal media and end-to-end attempts."""

    if len(media_durations_sec) != len(predictions):
        raise ValueError("media durations and predictions must have equal length")
    if not media_durations_sec:
        raise ValueError("real-time rate requires at least one temporal sample")
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
        for value in media_durations_sec
    ):
        raise ValueError("media durations must be finite and positive")
    for index, prediction in enumerate(predictions):
        if prediction.get("status") not in {"ok", "timeout"} and prediction.get(
            "processing_time_sec"
        ) is None:
            raise ValueError(
                f"failed prediction at index {index} must record processing_time_sec for D-2"
            )
    latency = prediction_latency_metrics(predictions, timeout_cap_sec=timeout_cap_sec)
    total_media_duration = float(sum(media_durations_sec))
    total_processing_time = float(latency["sum_sec"])
    if total_processing_time <= 0:
        raise ValueError("total processing time must be positive")
    attempted_count = len(predictions)
    success_count = sum(prediction.get("status") == "ok" for prediction in predictions)
    return {
        "realtime_rate": total_media_duration / total_processing_time,
        "media_duration_sec": total_media_duration,
        "processing_time_sec": total_processing_time,
        "attempted_count": attempted_count,
        "success_count": success_count,
        "success_rate": success_count / attempted_count,
        "failure_rate": (attempted_count - success_count) / attempted_count,
        "timeout_count": int(latency["timeout_count"]),
        "timeout_cap_sec": timeout_cap_sec,
    }


def throughput_metrics(
    media_durations_sec: Sequence[float | None],
    predictions: Sequence[dict[str, Any]],
    *,
    wall_clock_sec: float,
) -> dict[str, float | int]:
    """Compute D-4 success throughput from aligned attempts and run wall time."""

    if len(media_durations_sec) != len(predictions):
        raise ValueError("media durations and predictions must have equal length")
    if not math.isfinite(wall_clock_sec) or wall_clock_sec <= 0:
        raise ValueError("wall_clock_sec must be finite and positive")
    if any(
        value is not None
        and (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
        )
        for value in media_durations_sec
    ):
        raise ValueError("media durations must be null or finite and non-negative")
    success_indices = [
        index for index, prediction in enumerate(predictions) if prediction.get("status") == "ok"
    ]
    success_count = len(success_indices)
    attempted_count = len(predictions)
    failure_count = attempted_count - success_count
    successful_media_sec = sum(
        float(media_durations_sec[index])
        for index in success_indices
        if media_durations_sec[index] is not None
    )
    return {
        "successful_items_per_hour": success_count * 3600.0 / wall_clock_sec,
        "successful_media_hours_per_hour": successful_media_sec / wall_clock_sec,
        "successful_media_duration_sec": successful_media_sec,
        "wall_clock_sec": wall_clock_sec,
        "attempted_count": attempted_count,
        "success_count": success_count,
        "failure_count": failure_count,
        "failure_rate": failure_count / attempted_count if attempted_count else 0.0,
    }


def temporal_iou(first: tuple[float, float], second: tuple[float, float]) -> float:
    first_start, first_end = first
    second_start, second_end = second
    if first_start >= first_end or second_start >= second_end:
        raise ValueError("temporal intervals must have positive duration")
    intersection = max(0.0, min(first_end, second_end) - max(first_start, second_start))
    union = (first_end - first_start) + (second_end - second_start) - intersection
    return intersection / union


def bbox_iou(
    first: tuple[float, float, float, float], second: tuple[float, float, float, float]
) -> float:
    first_x1, first_y1, first_x2, first_y2 = first
    second_x1, second_y1, second_x2, second_y2 = second
    if first_x1 >= first_x2 or first_y1 >= first_y2 or second_x1 >= second_x2 or second_y1 >= second_y2:
        raise ValueError("bounding boxes must have positive width and height")
    intersection_width = max(0.0, min(first_x2, second_x2) - max(first_x1, second_x1))
    intersection_height = max(0.0, min(first_y2, second_y2) - max(first_y1, second_y1))
    intersection = intersection_width * intersection_height
    first_area = (first_x2 - first_x1) * (first_y2 - first_y1)
    second_area = (second_x2 - second_x1) * (second_y2 - second_y1)
    return intersection / (first_area + second_area - intersection)
