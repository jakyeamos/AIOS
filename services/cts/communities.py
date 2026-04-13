from __future__ import annotations

from collections import Counter
from typing import Any


def detect_communities(store, repo_id: str, limit: int = 20) -> list[dict[str, Any]]:
    rows = store.conn.execute(
        """
        SELECT file_path, COUNT(*) AS node_count
        FROM nodes
        WHERE repo_id=?
        GROUP BY file_path
        ORDER BY node_count DESC
        LIMIT ?
        """,
        (repo_id, limit),
    ).fetchall()
    communities = []
    for row in rows:
        path = row["file_path"]
        domain = path.split("/", 1)[0] if "/" in path else path
        communities.append(
            {
                "name": domain,
                "file_path": path,
                "node_count": int(row["node_count"]),
                "cohesion_score": round(min(1.0, int(row["node_count"]) / 50.0), 2),
            }
        )
    grouped = Counter(c["name"] for c in communities)
    for community in communities:
        community["cross_community_links"] = grouped[community["name"]] - 1
    return communities

