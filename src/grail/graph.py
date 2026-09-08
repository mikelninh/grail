import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Edge:
    source: str
    relation: str
    target: str
    weight: float = 1.0
    evidence: str | None = None


class CollectorGraph:
    """Tiny SQLite-backed property graph for reproducible local intelligence."""

    def __init__(self, path: str = ":memory:") -> None:
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, kind TEXT NOT NULL, label TEXT NOT NULL, attrs_json TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS edges (source TEXT NOT NULL, relation TEXT NOT NULL, target TEXT NOT NULL, weight REAL NOT NULL DEFAULT 1, evidence TEXT, PRIMARY KEY (source, relation, target), FOREIGN KEY(source) REFERENCES nodes(id), FOREIGN KEY(target) REFERENCES nodes(id));
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
            CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
        """)

    def add_node(self, node_id: str, kind: str, label: str, attrs_json: str = "{}") -> None:
        self.db.execute("INSERT INTO nodes(id,kind,label,attrs_json) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,label=excluded.label,attrs_json=excluded.attrs_json", (node_id, kind, label, attrs_json))
        self.db.commit()

    def add_edge(self, edge: Edge) -> None:
        self.db.execute("INSERT INTO edges(source,relation,target,weight,evidence) VALUES(?,?,?,?,?) ON CONFLICT(source,relation,target) DO UPDATE SET weight=excluded.weight,evidence=excluded.evidence", (edge.source, edge.relation, edge.target, edge.weight, edge.evidence))
        self.db.commit()

    def neighbours(self, node_id: str, relation: str | None = None) -> list[Edge]:
        sql = "SELECT source,relation,target,weight,evidence FROM edges WHERE source=?"
        params: list[object] = [node_id]
        if relation:
            sql += " AND relation=?"
            params.append(relation)
        return [Edge(*row) for row in self.db.execute(sql, params).fetchall()]

    def shortest_semantic_path(self, source: str, target: str, max_depth: int = 4) -> list[Edge]:
        if source == target:
            return []
        queue: list[tuple[str, list[Edge]]] = [(source, [])]
        seen = {source}
        while queue:
            node, path = queue.pop(0)
            if len(path) >= max_depth:
                continue
            rows = self.db.execute("SELECT source,relation,target,weight,evidence FROM edges WHERE source=?", (node,)).fetchall()
            for row in rows:
                edge = Edge(*row)
                next_path = path + [edge]
                if edge.target == target:
                    return next_path
                if edge.target not in seen:
                    seen.add(edge.target)
                    queue.append((edge.target, next_path))
        return []
