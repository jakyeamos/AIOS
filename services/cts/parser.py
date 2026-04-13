from __future__ import annotations

import ast
import hashlib
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .confidence import default_edge_confidence, default_node_confidence
from .models import CTSEdge, CTSNode, EdgeKind, ExtractionMethod, NodeKind, ResolutionMethod
from .tsconfig_resolver import TSConfigResolver

SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
}

IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
}

TS_CALL_RE = re.compile(r"\b([A-Za-z_$][A-Za-z0-9_$]*)\s*\(")
TS_IMPORT_RE = re.compile(r"^\s*import\s+(.+?)\s+from\s+['\"]([^'\"]+)['\"]")
TS_REQUIRE_RE = re.compile(r"require\(\s*['\"]([^'\"]+)['\"]\s*\)")
TS_CLASS_RE = re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][A-Za-z0-9_$]*)")
TS_FUNCTION_RE = re.compile(r"^\s*(?:export\s+)?function\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*\(")
TS_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(?:async\s*)?\(.*\)\s*=>"
)
TS_METHOD_RE = re.compile(r"^\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\([^)]*\)\s*\{")

TS_CALL_KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "function",
    "typeof",
    "return",
    "new",
    "await",
    "super",
    "import",
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _node_id(repo_id: str, qualified_name: str) -> str:
    return _sha256(f"{repo_id}:{qualified_name}")


def _edge_id(repo_id: str, kind: EdgeKind, source: str, target: str, file_path: str, line: int) -> str:
    return _sha256(f"{repo_id}:{kind.value}:{source}:{target}:{file_path}:{line}")


def _is_test_file(path: Path) -> bool:
    lower = str(path).lower()
    return "test" in lower or lower.endswith("_spec.ts") or lower.endswith(".spec.ts")


@dataclass(slots=True)
class ParseResult:
    nodes: list[CTSNode] = field(default_factory=list)
    edges: list[CTSEdge] = field(default_factory=list)
    total_files: int = 0
    parsed_files: int = 0
    failed_files: list[str] = field(default_factory=list)
    language_file_counts: dict[str, int] = field(default_factory=dict)

    @property
    def coverage_pct(self) -> float:
        if self.total_files == 0:
            return 0.0
        return self.parsed_files / self.total_files

    @property
    def language_breakdown(self) -> dict[str, float]:
        if self.parsed_files == 0:
            return {}
        return {
            lang: count / self.parsed_files
            for lang, count in sorted(self.language_file_counts.items(), key=lambda i: i[0])
        }


@dataclass(slots=True)
class ScopeBlock:
    qn: str
    start_line: int
    end_line: int


class RepoParser:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.ts_resolver = TSConfigResolver(repo_root=self.repo_root)

    def collect_files(self) -> list[Path]:
        files: list[Path] = []
        for path in self.repo_root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in IGNORE_DIRS for part in path.parts):
                continue
            if path.suffix in SUPPORTED_EXTENSIONS:
                files.append(path)
        return sorted(files)

    def parse(
        self,
        repo_id: str,
        files: Iterable[Path] | None = None,
    ) -> ParseResult:
        file_list = list(files) if files is not None else self.collect_files()
        result = ParseResult(total_files=len(file_list))
        for file_path in file_list:
            language = SUPPORTED_EXTENSIONS.get(file_path.suffix)
            if language is None:
                continue
            try:
                if language == "python":
                    nodes, edges = self._parse_python_file(repo_id, file_path)
                else:
                    nodes, edges = self._parse_ts_file(repo_id, file_path, language)
            except Exception:
                result.failed_files.append(str(file_path))
                continue
            result.nodes.extend(nodes)
            result.edges.extend(edges)
            result.parsed_files += 1
            result.language_file_counts[language] = result.language_file_counts.get(language, 0) + 1
        return result

    def _relative(self, path: Path) -> str:
        return str(path.resolve().relative_to(self.repo_root))

    def _module_qualified_name(self, path: Path) -> str:
        rel = self._relative(path)
        stem = rel.rsplit(".", 1)[0].replace("/", ".")
        return f"module.{stem}"

    def _file_node(self, repo_id: str, path: Path, language: str, unresolved_calls: int) -> CTSNode:
        rel = self._relative(path)
        qn = f"file:{rel}"
        now = ""
        is_test = _is_test_file(path)
        return CTSNode(
            id=_node_id(repo_id, qn),
            repo_id=repo_id,
            kind=NodeKind.FILE if not is_test else NodeKind.TEST,
            name=path.name,
            qualified_name=qn,
            file_path=rel,
            line_start=1,
            line_end=max(1, len(path.read_text(encoding="utf-8", errors="replace").splitlines())),
            language=language,
            parent_qualified=None,
            params=None,
            return_type=None,
            modifiers=[],
            is_test=is_test,
            file_hash=_file_hash(path),
            confidence=default_node_confidence(ExtractionMethod.TREE_SITTER),
            extraction_method=ExtractionMethod.TREE_SITTER,
            last_verified_at=None,
            is_stale=False,
            unresolved_call_count=unresolved_calls,
            extra={},
            updated_at=now,
        )

    def _parse_python_file(self, repo_id: str, path: Path) -> tuple[list[CTSNode], list[CTSEdge]]:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source)
        rel = self._relative(path)
        module_qn = self._module_qualified_name(path)
        file_qn = f"file:{rel}"
        defs: dict[str, str] = {}
        nodes: list[CTSNode] = []
        edges: list[CTSEdge] = []
        unresolved_calls = 0

        class DefCollector(ast.NodeVisitor):
            def __init__(self) -> None:
                self.stack: list[str] = []

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                parent = self.stack[-1] if self.stack else module_qn
                qn = f"{parent}.{node.name}"
                defs[node.name] = qn
                self.stack.append(qn)
                self.generic_visit(node)
                self.stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                parent = self.stack[-1] if self.stack else module_qn
                qn = f"{parent}.{node.name}"
                defs[node.name] = qn
                self.stack.append(qn)
                self.generic_visit(node)
                self.stack.pop()

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self.visit_FunctionDef(node)  # type: ignore[arg-type]

        DefCollector().visit(tree)

        class Analyzer(ast.NodeVisitor):
            def __init__(self) -> None:
                self.stack: list[str] = []
                self.class_stack: list[str] = []

            def _parent_qn(self) -> str:
                if self.stack:
                    return self.stack[-1]
                return module_qn

            def _add_contains(self, parent_qn: str, child_qn: str, line: int) -> None:
                edges.append(
                    CTSEdge(
                        id=_edge_id(repo_id, EdgeKind.CONTAINS, parent_qn, child_qn, rel, line),
                        repo_id=repo_id,
                        kind=EdgeKind.CONTAINS,
                        source_qualified=parent_qn,
                        target_qualified=child_qn,
                        file_path=rel,
                        line=line,
                        confidence=default_edge_confidence(
                            ExtractionMethod.TREE_SITTER, ResolutionMethod.STATIC
                        ),
                        resolution_method=ResolutionMethod.STATIC,
                        extraction_method=ExtractionMethod.TREE_SITTER,
                        is_stale=False,
                    )
                )

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                parent = self._parent_qn()
                qn = f"{parent}.{node.name}"
                line_end = getattr(node, "end_lineno", node.lineno)
                class_node = CTSNode(
                    id=_node_id(repo_id, qn),
                    repo_id=repo_id,
                    kind=NodeKind.CLASS,
                    name=node.name,
                    qualified_name=qn,
                    file_path=rel,
                    line_start=node.lineno,
                    line_end=line_end,
                    language="python",
                    parent_qualified=parent,
                    is_test=_is_test_file(path),
                    file_hash=_file_hash(path),
                    confidence=default_node_confidence(ExtractionMethod.TREE_SITTER),
                    extraction_method=ExtractionMethod.TREE_SITTER,
                )
                nodes.append(class_node)
                self._add_contains(file_qn if parent == module_qn else parent, qn, node.lineno)
                for base in node.bases:
                    base_name = self._expr_name(base)
                    if base_name:
                        target_qn = defs.get(base_name, f"unresolved::{base_name}")
                        resolution = (
                            ResolutionMethod.STATIC
                            if target_qn in defs.values()
                            else ResolutionMethod.UNRESOLVED
                        )
                        edges.append(
                            CTSEdge(
                                id=_edge_id(repo_id, EdgeKind.INHERITS, qn, target_qn, rel, node.lineno),
                                repo_id=repo_id,
                                kind=EdgeKind.INHERITS,
                                source_qualified=qn,
                                target_qualified=target_qn,
                                file_path=rel,
                                line=node.lineno,
                                confidence=default_edge_confidence(
                                    ExtractionMethod.TREE_SITTER, resolution
                                ),
                                resolution_method=resolution,
                                extraction_method=ExtractionMethod.TREE_SITTER,
                            )
                        )
                self.stack.append(qn)
                self.class_stack.append(qn)
                self.generic_visit(node)
                self.class_stack.pop()
                self.stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self._visit_function_like(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self._visit_function_like(node)

            def _visit_function_like(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                parent = self._parent_qn()
                qn = f"{parent}.{node.name}"
                line_end = getattr(node, "end_lineno", node.lineno)
                is_test = _is_test_file(path) or node.name.startswith("test_")
                fn_node = CTSNode(
                    id=_node_id(repo_id, qn),
                    repo_id=repo_id,
                    kind=NodeKind.TEST if is_test else NodeKind.FUNCTION,
                    name=node.name,
                    qualified_name=qn,
                    file_path=rel,
                    line_start=node.lineno,
                    line_end=line_end,
                    language="python",
                    parent_qualified=parent,
                    params=", ".join(a.arg for a in node.args.args),
                    is_test=is_test,
                    file_hash=_file_hash(path),
                    confidence=default_node_confidence(ExtractionMethod.TREE_SITTER),
                    extraction_method=ExtractionMethod.TREE_SITTER,
                )
                nodes.append(fn_node)
                self._add_contains(file_qn if parent == module_qn else parent, qn, node.lineno)
                self.stack.append(qn)
                self.generic_visit(node)
                self.stack.pop()

            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    target_qn = f"module.{alias.name}"
                    edges.append(
                        CTSEdge(
                            id=_edge_id(repo_id, EdgeKind.IMPORTS_FROM, file_qn, target_qn, rel, node.lineno),
                            repo_id=repo_id,
                            kind=EdgeKind.IMPORTS_FROM,
                            source_qualified=file_qn,
                            target_qualified=target_qn,
                            file_path=rel,
                            line=node.lineno,
                            confidence=default_edge_confidence(
                                ExtractionMethod.TREE_SITTER, ResolutionMethod.STATIC
                            ),
                            resolution_method=ResolutionMethod.STATIC,
                            extraction_method=ExtractionMethod.TREE_SITTER,
                        )
                    )
                self.generic_visit(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                mod = node.module or ""
                target_qn = f"module.{mod}" if mod else "module.unknown"
                edges.append(
                    CTSEdge(
                        id=_edge_id(repo_id, EdgeKind.IMPORTS_FROM, file_qn, target_qn, rel, node.lineno),
                        repo_id=repo_id,
                        kind=EdgeKind.IMPORTS_FROM,
                        source_qualified=file_qn,
                        target_qualified=target_qn,
                        file_path=rel,
                        line=node.lineno,
                        confidence=default_edge_confidence(
                            ExtractionMethod.TREE_SITTER, ResolutionMethod.STATIC
                        ),
                        resolution_method=ResolutionMethod.STATIC,
                        extraction_method=ExtractionMethod.TREE_SITTER,
                    )
                )
                self.generic_visit(node)

            def visit_Call(self, node: ast.Call) -> None:
                nonlocal unresolved_calls
                source_qn = self.stack[-1] if self.stack else file_qn
                called = self._expr_name(node.func)
                if called:
                    target_qn = defs.get(called)
                    if target_qn:
                        resolution = ResolutionMethod.STATIC
                    else:
                        target_qn = f"unresolved::{called}"
                        resolution = ResolutionMethod.UNRESOLVED
                        unresolved_calls += 1
                    edges.append(
                        CTSEdge(
                            id=_edge_id(
                                repo_id,
                                EdgeKind.CALLS,
                                source_qn,
                                target_qn,
                                rel,
                                getattr(node, "lineno", 1),
                            ),
                            repo_id=repo_id,
                            kind=EdgeKind.CALLS,
                            source_qualified=source_qn,
                            target_qualified=target_qn,
                            file_path=rel,
                            line=getattr(node, "lineno", 1),
                            confidence=default_edge_confidence(ExtractionMethod.TREE_SITTER, resolution),
                            resolution_method=resolution,
                            extraction_method=ExtractionMethod.TREE_SITTER,
                        )
                    )
                self.generic_visit(node)

            @staticmethod
            def _expr_name(expr: ast.expr) -> str | None:
                if isinstance(expr, ast.Name):
                    return expr.id
                if isinstance(expr, ast.Attribute):
                    return expr.attr
                return None

        Analyzer().visit(tree)
        nodes.insert(0, self._file_node(repo_id, path, "python", unresolved_calls))
        return nodes, edges

    def _parse_ts_file(
        self,
        repo_id: str,
        path: Path,
        language: str,
    ) -> tuple[list[CTSNode], list[CTSEdge]]:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        rel = self._relative(path)
        module_qn = self._module_qualified_name(path)
        file_qn = f"file:{rel}"
        nodes: list[CTSNode] = []
        edges: list[CTSEdge] = []
        symbol_to_qn: dict[str, str] = {}
        import_symbols: dict[str, str] = {}
        blocks: list[ScopeBlock] = []
        unresolved_calls = 0
        file_hash = _file_hash(path)

        for line_no, raw in enumerate(lines, start=1):
            m_import = TS_IMPORT_RE.match(raw)
            if m_import:
                imported_part, import_path = m_import.groups()
                resolved = self.ts_resolver.resolve_import(path, import_path)
                target = (
                    self._module_qualified_name(resolved)
                    if resolved and resolved.exists()
                    else f"module.{import_path}"
                )
                edges.append(
                    CTSEdge(
                        id=_edge_id(repo_id, EdgeKind.IMPORTS_FROM, file_qn, target, rel, line_no),
                        repo_id=repo_id,
                        kind=EdgeKind.IMPORTS_FROM,
                        source_qualified=file_qn,
                        target_qualified=target,
                        file_path=rel,
                        line=line_no,
                        confidence=default_edge_confidence(
                            ExtractionMethod.TREE_SITTER, ResolutionMethod.ALIAS_RESOLVED
                        ),
                        resolution_method=ResolutionMethod.ALIAS_RESOLVED,
                        extraction_method=ExtractionMethod.TREE_SITTER,
                    )
                )
                for sym in self._extract_import_symbols(imported_part):
                    import_symbols[sym] = target
                continue

            req_match = TS_REQUIRE_RE.search(raw)
            if req_match:
                import_path = req_match.group(1)
                target = f"module.{import_path}"
                edges.append(
                    CTSEdge(
                        id=_edge_id(repo_id, EdgeKind.IMPORTS_FROM, file_qn, target, rel, line_no),
                        repo_id=repo_id,
                        kind=EdgeKind.IMPORTS_FROM,
                        source_qualified=file_qn,
                        target_qualified=target,
                        file_path=rel,
                        line=line_no,
                        confidence=default_edge_confidence(
                            ExtractionMethod.TREE_SITTER, ResolutionMethod.STATIC
                        ),
                        resolution_method=ResolutionMethod.STATIC,
                        extraction_method=ExtractionMethod.TREE_SITTER,
                    )
                )
                continue

            qn: str | None = None
            kind = NodeKind.FUNCTION
            m_class = TS_CLASS_RE.match(raw)
            if m_class:
                name = m_class.group(1)
                qn = f"{module_qn}.{name}"
                kind = NodeKind.CLASS
            else:
                m_fn = TS_FUNCTION_RE.match(raw)
                if m_fn:
                    name = m_fn.group(1)
                    qn = f"{module_qn}.{name}"
                    kind = NodeKind.FUNCTION
                else:
                    m_arrow = TS_ARROW_RE.match(raw)
                    if m_arrow:
                        name = m_arrow.group(1)
                        qn = f"{module_qn}.{name}"
                        kind = NodeKind.FUNCTION
                    elif TS_METHOD_RE.match(raw):
                        method_name = TS_METHOD_RE.match(raw).group(1)  # type: ignore[union-attr]
                        class_scope = self._class_scope_for_line(blocks, line_no)
                        if class_scope:
                            qn = f"{class_scope}.{method_name}"
                            kind = NodeKind.FUNCTION
            if qn:
                line_end = self._find_block_end(lines, line_no)
                symbol_to_qn[qn.rsplit(".", 1)[-1]] = qn
                blocks.append(ScopeBlock(qn=qn, start_line=line_no, end_line=line_end))
                node = CTSNode(
                    id=_node_id(repo_id, qn),
                    repo_id=repo_id,
                    kind=kind,
                    name=qn.rsplit(".", 1)[-1],
                    qualified_name=qn,
                    file_path=rel,
                    line_start=line_no,
                    line_end=line_end,
                    language=language,
                    parent_qualified=module_qn,
                    is_test=_is_test_file(path),
                    file_hash=file_hash,
                    confidence=default_node_confidence(ExtractionMethod.TREE_SITTER),
                    extraction_method=ExtractionMethod.TREE_SITTER,
                )
                nodes.append(node)
                edges.append(
                    CTSEdge(
                        id=_edge_id(repo_id, EdgeKind.CONTAINS, file_qn, qn, rel, line_no),
                        repo_id=repo_id,
                        kind=EdgeKind.CONTAINS,
                        source_qualified=file_qn,
                        target_qualified=qn,
                        file_path=rel,
                        line=line_no,
                        confidence=default_edge_confidence(
                            ExtractionMethod.TREE_SITTER, ResolutionMethod.STATIC
                        ),
                        resolution_method=ResolutionMethod.STATIC,
                        extraction_method=ExtractionMethod.TREE_SITTER,
                    )
                )

        sorted_blocks = sorted(blocks, key=lambda b: (b.start_line, b.end_line - b.start_line))

        for line_no, raw in enumerate(lines, start=1):
            source_qn = self._source_scope_for_line(sorted_blocks, file_qn, line_no)
            for match in TS_CALL_RE.finditer(raw):
                callee = match.group(1)
                if callee in TS_CALL_KEYWORDS:
                    continue
                if callee in symbol_to_qn:
                    target_qn = symbol_to_qn[callee]
                    resolution = ResolutionMethod.STATIC
                elif callee in import_symbols:
                    target_qn = import_symbols[callee]
                    resolution = ResolutionMethod.ALIAS_RESOLVED
                else:
                    target_qn = f"unresolved::{callee}"
                    resolution = ResolutionMethod.UNRESOLVED
                    unresolved_calls += 1
                edges.append(
                    CTSEdge(
                        id=_edge_id(repo_id, EdgeKind.CALLS, source_qn, target_qn, rel, line_no),
                        repo_id=repo_id,
                        kind=EdgeKind.CALLS,
                        source_qualified=source_qn,
                        target_qualified=target_qn,
                        file_path=rel,
                        line=line_no,
                        confidence=default_edge_confidence(ExtractionMethod.TREE_SITTER, resolution),
                        resolution_method=resolution,
                        extraction_method=ExtractionMethod.TREE_SITTER,
                    )
                )

        nodes.insert(0, self._file_node(repo_id, path, language, unresolved_calls))
        return nodes, edges

    @staticmethod
    def _extract_import_symbols(import_spec: str) -> list[str]:
        symbols: list[str] = []
        spec = import_spec.strip()
        if spec.startswith("{") and spec.endswith("}"):
            names = spec[1:-1].split(",")
            for name in names:
                cleaned = name.strip()
                if " as " in cleaned:
                    symbols.append(cleaned.split(" as ", 1)[1].strip())
                elif cleaned:
                    symbols.append(cleaned)
            return symbols
        if "," in spec:
            first, rest = spec.split(",", 1)
            symbols.append(first.strip())
            symbols.extend(RepoParser._extract_import_symbols(rest.strip()))
            return [s for s in symbols if s]
        if spec.startswith("* as "):
            return [spec[5:].strip()]
        if spec:
            return [spec]
        return symbols

    @staticmethod
    def _find_block_end(lines: list[str], line_no: int) -> int:
        balance = 0
        started = False
        for idx in range(line_no - 1, len(lines)):
            line = lines[idx]
            opens = line.count("{")
            closes = line.count("}")
            if opens > 0:
                started = True
            balance += opens
            balance -= closes
            if started and balance <= 0:
                return idx + 1
        return len(lines)

    @staticmethod
    def _source_scope_for_line(blocks: list[ScopeBlock], fallback: str, line: int) -> str:
        for block in blocks:
            if block.start_line <= line <= block.end_line:
                return block.qn
        return fallback

    @staticmethod
    def _class_scope_for_line(blocks: list[ScopeBlock], line: int) -> str | None:
        class_blocks = [b for b in blocks if ".class." not in b.qn]
        for block in class_blocks:
            if block.start_line <= line <= block.end_line and block.qn.rsplit(".", 1)[-1][0].isupper():
                return block.qn
        return None

