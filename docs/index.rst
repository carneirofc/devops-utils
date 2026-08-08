devops-utils
============

A set of utility tools for DevOps, built around a dependency-free core exposed
through several optional surfaces: a **CLI**, an **MCP server**, **agent
tools**, a **Claude Code plugin**, a **TUI**, and a **Qt UI**.

Two things it does today:

* **Azure DevOps, made scriptable and agent-friendly** — work items, builds,
  repositories and pull requests over plain REST, on cloud and on-prem alike,
  with clean JSON on stdout and a human confirmation in front of every write.
* **Kubernetes manifest sanitizing** — mask every ``Secret`` value so a manifest
  can be pasted into a ticket, a chat, or an LLM prompt.

Nothing has to be installed to try it::

   uvx --from "devops-utils[azure]" devops-utils azdo list --project MyProject --mine

Start with :doc:`guide/install`, then pick the guide that matches what you are
doing.

.. toctree::
   :maxdepth: 2
   :caption: User guide

   guide/install
   guide/azure-devops
   guide/bulk-plans
   guide/sanitize
   guide/agents

.. toctree::
   :maxdepth: 2
   :caption: Agent guides

   agents/domain
   agents/azure-devops
   agents/issue-tracker
   agents/triage-labels

.. toctree::
   :maxdepth: 2
   :caption: API reference

   api/devops_utils

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
