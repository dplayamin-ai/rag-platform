"""Index backend adapters writing ``IndexRecord`` batches (bible §12 ``adapters/index``).

Planned modules: ``qdrant/`` (``filters``, ``point_id``, ``bm25_sparse``), ``opensearch/``
(``nori_settings``, ``dls``), ``saga`` (``IndexCommit`` generation saga, bible §11.4) and
``age_graph_store``.
"""

from __future__ import annotations
