"""Azure DevOps REST helpers (cloud + on-prem Server).

Requires the ``azure`` extra (``httpx``); the dependency is deferred-imported so
importing :mod:`devops_utils` never pulls it in when unused.
"""

from devops_utils.core.azure_devops.client import (
    AzureDevOpsClient,
    AzureDevOpsError,
)
from devops_utils.core.azure_devops.repos import list_repositories, resolve_repo
from devops_utils.core.azure_devops.workitems import (
    add_attachment,
    add_comment,
    add_link,
    create_work_item,
    get_work_item,
    list_work_items,
    query_wiql,
    remove_link,
    search_work_items,
    set_tags,
    update_work_item,
)

__all__ = [
    "AzureDevOpsClient",
    "AzureDevOpsError",
    "add_attachment",
    "add_comment",
    "add_link",
    "create_work_item",
    "get_work_item",
    "list_repositories",
    "list_work_items",
    "query_wiql",
    "remove_link",
    "resolve_repo",
    "search_work_items",
    "set_tags",
    "update_work_item",
]
