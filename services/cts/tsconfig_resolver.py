from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TS_EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts"]


def _strip_json_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"^\s*//.*$", "", text, flags=re.MULTILINE)
    return text


def _load_jsonc(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        return json.loads(_strip_json_comments(raw))
    except json.JSONDecodeError:
        return {}


@dataclass(slots=True)
class ResolverFailure:
    importer: str
    import_path: str
    reason: str


@dataclass(slots=True)
class TSConfigResolver:
    repo_root: Path
    resolution_failure_log: list[ResolverFailure] = field(default_factory=list)

    def resolve_import(self, importer_file: Path, import_path: str) -> Path | None:
        if import_path.startswith("."):
            return self._resolve_relative(importer_file, import_path)
        if import_path.startswith("@/"):
            fallback = self.repo_root / "src" / import_path[2:]
            resolved = self._resolve_fileish(fallback)
            if resolved is not None:
                return resolved
        tsconfig = self._find_tsconfig(importer_file.parent)
        config = self._load_effective_tsconfig(tsconfig) if tsconfig else {}
        compiler = config.get("compilerOptions", {})
        base_url = compiler.get("baseUrl", ".")
        base_dir = (tsconfig.parent / base_url).resolve() if tsconfig else (self.repo_root / "src")
        paths = compiler.get("paths", {})
        resolved = self._resolve_via_paths(base_dir, paths, import_path)
        if resolved is not None:
            return resolved
        package_try = self._resolve_node_module(import_path)
        if package_try is not None:
            return package_try
        self.resolution_failure_log.append(
            ResolverFailure(str(importer_file), import_path, "unresolved_import_path")
        )
        return None

    def _find_tsconfig(self, start: Path) -> Path | None:
        current = start
        while True:
            candidate = current / "tsconfig.json"
            if candidate.exists():
                return candidate
            if current == self.repo_root or current.parent == current:
                return None
            current = current.parent

    def _load_effective_tsconfig(self, tsconfig: Path) -> dict:
        loaded = _load_jsonc(tsconfig)
        extends = loaded.get("extends")
        if not extends:
            return loaded
        parent = self._resolve_extends(tsconfig.parent, extends)
        if parent is None:
            self.resolution_failure_log.append(
                ResolverFailure(str(tsconfig), extends, "tsconfig_extends_unresolved")
            )
            return loaded
        base = self._load_effective_tsconfig(parent)
        merged = dict(base)
        merged_compiler = dict(base.get("compilerOptions", {}))
        merged_compiler.update(loaded.get("compilerOptions", {}))
        merged.update(loaded)
        merged["compilerOptions"] = merged_compiler
        return merged

    def _resolve_extends(self, current_dir: Path, extends_value: str) -> Path | None:
        if extends_value.startswith("."):
            candidate = (current_dir / extends_value).resolve()
            if candidate.suffix != ".json":
                candidate = candidate.with_suffix(".json")
            return candidate if candidate.exists() else None
        package_path = extends_value
        if not package_path.endswith(".json"):
            package_path = f"{package_path}.json"
        node_modules_path = self.repo_root / "node_modules" / package_path
        if node_modules_path.exists():
            return node_modules_path
        return None

    def _resolve_via_paths(self, base_dir: Path, paths: dict, import_path: str) -> Path | None:
        for key, mapped in paths.items():
            if not isinstance(mapped, list):
                continue
            if "*" in key:
                if not self._wildcard_match(key, import_path):
                    continue
                suffix = import_path[len(key.split("*", 1)[0]) :]
                for target in mapped:
                    prefix = target.split("*", 1)[0]
                    candidate = (base_dir / f"{prefix}{suffix}").resolve()
                    resolved = self._resolve_fileish(candidate)
                    if resolved:
                        return resolved
                continue
            if key == import_path:
                for target in mapped:
                    candidate = (base_dir / target).resolve()
                    resolved = self._resolve_fileish(candidate)
                    if resolved:
                        return resolved
        return None

    def _resolve_relative(self, importer_file: Path, import_path: str) -> Path | None:
        candidate = (importer_file.parent / import_path).resolve()
        resolved = self._resolve_fileish(candidate)
        if resolved is not None:
            return resolved
        self.resolution_failure_log.append(
            ResolverFailure(str(importer_file), import_path, "relative_path_missing")
        )
        return None

    def _resolve_node_module(self, import_path: str) -> Path | None:
        module_dir = self.repo_root / "node_modules" / import_path
        return self._resolve_fileish(module_dir)

    def _resolve_fileish(self, base: Path) -> Path | None:
        if base.is_file():
            return base
        for ext in TS_EXTENSIONS:
            candidate = base.with_suffix(ext)
            if candidate.exists():
                return candidate
        for ext in TS_EXTENSIONS:
            idx = base / f"index{ext}"
            if idx.exists():
                return idx
        return None

    @staticmethod
    def _wildcard_match(pattern: str, value: str) -> bool:
        if "*" not in pattern:
            return pattern == value
        prefix, suffix = pattern.split("*", 1)
        return value.startswith(prefix) and value.endswith(suffix)

