"""Bulk work-item operations driven by a declarative plan.

A *plan* is a YAML/JSON document describing a batch of work-item writes —
creates, updates, links, comments — applied in order with local ``ref:``
cross-references so a child can be parented to an item created earlier in the
same run. The schema is deliberately loose: beyond the small set of named keys
below, **any** work-item field (process-specific or ``Custom.*``) goes through
the free-form ``fields`` map untouched, so callers are never limited to what
this module names explicitly.

Plan shape::

    project: Contoso              # default project for every item (optional)
    defaults:                     # merged into every item; the item wins
      type: User Story
      area_path: Contoso\\Payments
      fields:
        Custom.Source: git-history
    items:
      - ref: feat-checkout        # local handle other items can point at
        type: Feature
        title: Guest checkout
        description: "<p>…</p>"   # HTML
        state: Closed             # applied via a follow-up patch on create
        assigned_to: dev@contoso.com
        tags: [checkout]
        area_path: …
        iteration_path: …
        fields:                   # ANY reference name passes through as-is
          Microsoft.VSTS.Scheduling.TargetDate: 2026-08-31
          Custom.RiskLevel: High
        links:
          - {kind: commit, value: 3f2a91c, repo: web-app}
          - {kind: hyperlink, value: "https://…"}
        comments:
          - Imported from git history.
      - ref: story-1
        type: User Story
        title: Pay without an account
        parent: ref:feat-checkout # or a real work-item id
      - id: 1421                  # an existing item → update
        state: Active
        fields: {Custom.RiskLevel: Low}

Rules:

- An item with ``id`` is an **update**; without it, a **create** (``type`` and
  ``title`` required). ``action: create|update`` may be given explicitly and is
  validated against the presence of ``id``.
- ``parent`` and the value of work-item link kinds (``parent``, ``child``,
  ``work_item``, ``predecessor``, ``successor``) accept ``ref:<name>`` — the
  referenced item must appear **earlier** in ``items``.
- Unknown item keys are collected as warnings, not errors: a typo should be
  visible in the review window without making user extensions impossible.
- All links of an item are sent in a **single** JSON-patch request.
"""

from __future__ import annotations

from typing import Any

import yaml

from devops_utils.core.azure_devops.client import AzureDevOpsClient
from devops_utils.core.azure_devops.workitems import (
    JSON_PATCH,
    LINK_KINDS,
    WORK_ITEM_RELATIONS,
    _add,
    _build_relation,
    _trim,
    add_comment,
    create_work_item,
    update_work_item,
)

#: Item keys this module interprets. Everything else is warned about; arbitrary
#: fields belong under the free-form ``fields`` map.
KNOWN_ITEM_KEYS = (
    "ref",
    "action",
    "id",
    "project",
    "type",
    "title",
    "description",
    "state",
    "assigned_to",
    "tags",
    "area_path",
    "iteration_path",
    "parent",
    "fields",
    "links",
    "comments",
)

_REF_PREFIX = "ref:"


class PlanError(ValueError):
    """A plan failed validation; the message lists every problem found."""


def load_plan(text: str) -> dict[str, Any]:
    """Parse a YAML (or JSON — a YAML subset) plan document."""
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise PlanError("plan must be a mapping with an 'items' list")
    return data


def validate_plan(plan: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Normalize and validate a plan.

    Merges ``defaults`` into every item (item values win; the two ``fields``
    maps are merged key-wise), resolves the effective project, and checks
    ordering of ``ref:`` references.

    Returns:
        ``(items, warnings)`` — the normalized items in application order and
        human-readable warnings (unknown keys, …) for the review window.

    Raises:
        PlanError: With every hard problem found, one per line.
    """
    raw_items = plan.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise PlanError("plan must carry a non-empty 'items' list")

    defaults = plan.get("defaults") or {}
    if not isinstance(defaults, dict):
        raise PlanError("'defaults' must be a mapping")
    plan_project = plan.get("project")

    errors: list[str] = []
    warnings: list[str] = []
    items: list[dict[str, Any]] = []
    seen_refs: set[str] = set()

    for pos, raw in enumerate(raw_items):
        label = f"items[{pos}]"
        if not isinstance(raw, dict):
            errors.append(f"{label}: must be a mapping")
            continue

        item = {**defaults, **raw}
        merged_fields = {**(defaults.get("fields") or {}), **(raw.get("fields") or {})}
        if merged_fields:
            item["fields"] = merged_fields

        for key in raw:
            if key not in KNOWN_ITEM_KEYS:
                warnings.append(
                    f"{label}: unknown key {key!r} is ignored — custom work-item "
                    "fields go under 'fields' by reference name"
                )

        action = item.get("action") or ("update" if item.get("id") else "create")
        if action not in ("create", "update"):
            errors.append(f"{label}: action must be 'create' or 'update'")
        if action == "update" and not item.get("id"):
            errors.append(f"{label}: update requires 'id'")
        if action == "create" and item.get("id"):
            errors.append(f"{label}: create must not carry 'id'")
        if action == "create":
            if not item.get("type"):
                errors.append(f"{label}: create requires 'type'")
            if not item.get("title"):
                errors.append(f"{label}: create requires 'title'")
        item["action"] = action

        item["project"] = item.get("project") or plan_project
        if action == "create" and not item["project"]:
            errors.append(f"{label}: no project (set plan-level 'project' or per item)")

        parent = item.get("parent")
        if (
            isinstance(parent, str)
            and parent.startswith(_REF_PREFIX)
            and parent[len(_REF_PREFIX) :] not in seen_refs
        ):
            errors.append(
                f"{label}: parent {parent!r} does not point at an earlier item"
            )

        links = item.get("links") or []
        if not isinstance(links, list):
            errors.append(f"{label}: 'links' must be a list")
            links = []
        for lpos, link in enumerate(links):
            llabel = f"{label}.links[{lpos}]"
            if not isinstance(link, dict):
                errors.append(f"{llabel}: must be a mapping")
                continue
            kind = link.get("kind")
            if kind not in LINK_KINDS:
                errors.append(f"{llabel}: kind must be one of {LINK_KINDS}")
                continue
            if link.get("value") in (None, ""):
                errors.append(f"{llabel}: requires 'value'")
            value = str(link.get("value") or "")
            if value.startswith(_REF_PREFIX):
                if kind not in WORK_ITEM_RELATIONS:
                    errors.append(
                        f"{llabel}: 'ref:' values only work for work-item kinds"
                    )
                elif value[len(_REF_PREFIX) :] not in seen_refs:
                    errors.append(
                        f"{llabel}: {value!r} does not point at an earlier item"
                    )
            if kind in ("commit", "pull_request", "branch"):
                if not link.get("repo"):
                    errors.append(f"{llabel}: kind {kind!r} requires 'repo'")
                if not (link.get("project") or item["project"]):
                    errors.append(f"{llabel}: kind {kind!r} requires a project")

        ref = item.get("ref")
        if ref:
            if ref in seen_refs:
                errors.append(f"{label}: duplicate ref {ref!r}")
            seen_refs.add(str(ref))

        items.append(item)

    if errors:
        raise PlanError("\n".join(errors))
    return items, warnings


def plan_preview(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize normalized items for the human review window (no requests)."""
    preview: list[dict[str, Any]] = []
    for item in items:
        entry: dict[str, Any] = {"action": item["action"]}
        for key in ("ref", "id", "project", "type", "title", "state", "assigned_to"):
            if item.get(key) is not None:
                entry[key] = item[key]
        if item.get("parent") is not None:
            entry["parent"] = item["parent"]
        if item.get("tags"):
            entry["tags"] = item["tags"]
        if item.get("fields"):
            entry["fields"] = item["fields"]
        if item.get("links"):
            entry["links"] = [
                f"{link.get('kind')}:{link.get('value')}" for link in item["links"]
            ]
        if item.get("comments"):
            entry["comments"] = len(item["comments"])
        preview.append(entry)
    return preview


def apply_plan(
    client: AzureDevOpsClient,
    plan: dict[str, Any],
    *,
    stop_on_error: bool = False,
) -> list[dict[str, Any]]:
    """Apply a validated plan sequentially and return per-item results.

    Each result is ``{"ref", "action", "status", "id", "url"}`` with
    ``status`` one of ``created``/``updated``/``failed`` (plus ``"error"`` when
    failed). A failed item never stops ref resolution bookkeeping; later items
    parented to it fail with a clear message instead of mis-parenting.

    Args:
        stop_on_error: When true, stop at the first failed item (already
            applied items stay applied — there is no rollback).
    """
    items, _warnings = validate_plan(plan)
    ref_ids: dict[str, int] = {}
    results: list[dict[str, Any]] = []

    for pos, item in enumerate(items):
        result: dict[str, Any] = {
            "ref": item.get("ref"),
            "action": item["action"],
            "id": item.get("id"),
            "status": "failed",
        }
        try:
            wi = _apply_item(client, item, ref_ids)
            result.update(
                id=wi["id"],
                url=wi.get("url"),
                status="created" if item["action"] == "create" else "updated",
            )
            if item.get("ref"):
                ref_ids[str(item["ref"])] = wi["id"]
        except Exception as exc:  # noqa: BLE001 - reported per item, not raised
            result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(result)
        if result["status"] == "failed" and stop_on_error:
            for skipped in items[pos + 1 :]:
                results.append(
                    {
                        "ref": skipped.get("ref"),
                        "action": skipped["action"],
                        "id": skipped.get("id"),
                        "status": "skipped",
                    }
                )
            break
    return results


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _resolve_ref(value: Any, ref_ids: dict[str, int]) -> Any:
    """Turn ``ref:<name>`` into the created work-item id (int passes through)."""
    if isinstance(value, str) and value.startswith(_REF_PREFIX):
        name = value[len(_REF_PREFIX) :]
        if name not in ref_ids:
            raise ValueError(
                f"reference {value!r} points at an item that was not created "
                "(it failed or comes later in the plan)"
            )
        return ref_ids[name]
    return value


def _apply_item(
    client: AzureDevOpsClient,
    item: dict[str, Any],
    ref_ids: dict[str, int],
) -> dict[str, Any]:
    """Apply one normalized item: create/update, then state, links, comments."""
    if item["action"] == "create":
        parent = _resolve_ref(item.get("parent"), ref_ids)
        wi = create_work_item(
            client,
            item["project"],
            item["type"],
            item["title"],
            description=item.get("description"),
            tags=item.get("tags"),
            area_path=item.get("area_path"),
            iteration_path=item.get("iteration_path"),
            assigned_to=item.get("assigned_to"),
            parent=int(parent) if parent is not None else None,
            fields=item.get("fields"),
        )
        # New items start in the template's initial state; a requested state is
        # applied as a follow-up patch so e.g. historical work can land Closed.
        if item.get("state"):
            wi = update_work_item(client, wi["id"], state=item["state"])
    else:
        wi = update_work_item(
            client,
            int(item["id"]),
            state=item.get("state"),
            assigned_to=item.get("assigned_to"),
            title=item.get("title"),
            description=item.get("description"),
            area_path=item.get("area_path"),
            iteration_path=item.get("iteration_path"),
            fields=item.get("fields"),
        )

    links = item.get("links") or []
    if links:
        wi = _add_links(client, wi["id"], links, item.get("project"), ref_ids)
    for text in item.get("comments") or []:
        wi = add_comment(client, wi["id"], text)
    return wi


def _add_links(
    client: AzureDevOpsClient,
    work_item_id: int,
    links: list[dict[str, Any]],
    default_project: str | None,
    ref_ids: dict[str, int],
) -> dict[str, Any]:
    """Add all of an item's links in one JSON-patch request."""
    ops: list[dict[str, Any]] = []
    for link in links:
        value = _resolve_ref(link.get("value"), ref_ids)
        rel, url, name = _build_relation(
            client,
            link["kind"],
            str(value),
            link.get("project") or default_project,
            link.get("repo"),
        )
        attributes: dict[str, Any] = {}
        if name:
            attributes["name"] = name
        if link.get("comment"):
            attributes["comment"] = link["comment"]
        relation: dict[str, Any] = {"rel": rel, "url": url}
        if attributes:
            relation["attributes"] = attributes
        ops.append(_add("/relations/-", relation))

    data = client.request(
        "PATCH",
        f"_apis/wit/workitems/{work_item_id}",
        json=ops,
        content_type=JSON_PATCH,
    )
    return _trim(data)
