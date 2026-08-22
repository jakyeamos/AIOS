from __future__ import annotations

import json
from pathlib import Path

import pytest

import benchmark.m6_openrouter_runner as runner
from benchmark.m6_openrouter_runner import (
    OpenRouterConfig,
    build_request_payload,
    extract_usage,
    generation_provider,
    has_tool_calls,
    main,
    write_receipt,
)


def test_request_is_pinned_when_provider_is_selected() -> None:
    payload = build_request_payload(
        "hello",
        OpenRouterConfig(
            model="example/model:free",
            provider_only=("example-provider",),
            reasoning_effort="high",
        ),
    )

    assert payload["model"] == "example/model:free"
    assert payload["stream"] is False
    assert payload["provider"] == {"only": ["example-provider"], "allow_fallbacks": False}
    assert payload["reasoning"] == {"effort": "high"}


def test_usage_prefers_provider_reported_cost_and_maps_cached_tokens() -> None:
    usage = extract_usage(
        {
            "id": "gen-1",
            "model": "example/model:free",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 25,
                "total_tokens": 125,
                "prompt_tokens_details": {"cached_tokens": 7},
            },
        },
        {"data": {"total_cost": 0.001}},
    )

    assert usage.input_tokens == 100
    assert usage.output_tokens == 25
    assert usage.cached_input_tokens == 7
    assert usage.total_tokens == 125
    assert usage.cost_usd == 0.001


def test_tool_calls_are_not_silently_treated_as_completed_work() -> None:
    assert has_tool_calls({"choices": [{"message": {"tool_calls": [{"id": "call-1"}]}}]})


def test_receipt_is_immutable_and_never_writes_ledger(tmp_path: Path) -> None:
    response = {
        "id": "gen-1",
        "model": "example/model:free",
        "usage": {
            "prompt_tokens": 2,
            "completion_tokens": 3,
            "total_tokens": 5,
            "prompt_tokens_details": {"cached_tokens": 0},
            "cost": 0.0,
        },
        "choices": [{"message": {"content": "done"}}],
    }
    receipt_path = write_receipt(
        output_dir=tmp_path / "run",
        pair_id="openrouter-pair-1",
        run_id="openrouter-run-1",
        condition="baseline_repo_only",
        prompt="hello",
        payload=build_request_payload("hello", OpenRouterConfig(model="example/model:free")),
        response=response,
        generation={
            "data": {"id": "gen-1", "provider_name": "example-provider", "total_cost": 0.0}
        },
        config=OpenRouterConfig(model="example/model:free"),
    )

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["benchmark_scope"] == "openrouter_api_completion_v1"
    assert receipt["ledger_write"] == "none"
    assert receipt["score_status"] == "pending_independent_review"
    assert receipt["actual_provider"] == "example-provider"
    assert receipt["provider_response_sha256"]
    assert not (tmp_path / "run" / "m6-promotion-rerun-ledger.db").exists()


def test_generation_provider_is_unknown_without_a_provider_lookup() -> None:
    assert generation_provider(None) is None
    assert generation_provider({"data": {"provider_name": "provider-a"}}) == "provider-a"


def test_cli_requires_explicit_network_acknowledgement(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("hello", encoding="utf-8")

    assert (
        main(
            [
                "--prompt",
                str(prompt),
                "--pair-id",
                "pair-1",
                "--run-id",
                "run-1",
                "--condition",
                "baseline_repo_only",
                "--output-dir",
                str(tmp_path / "out"),
                "--model",
                "example/model:free",
            ]
        )
        == 2
    )
    assert "--allow-network" in capsys.readouterr().err


def test_validation_helpers_fail_closed_for_malformed_provider_data() -> None:
    with pytest.raises(ValueError, match="expected a JSON object"):
        runner._object([])
    with pytest.raises(ValueError, match="non-negative integer"):
        runner._nonnegative_int(True, "count")
    with pytest.raises(ValueError, match="non-negative number"):
        runner._optional_nonnegative_number(-1, "cost")
    assert runner._optional_nonnegative_number(None, "cost") is None

    with pytest.raises(ValueError, match="prompt must not be empty"):
        build_request_payload("  ", OpenRouterConfig(model="example/model"))
    with pytest.raises(ValueError, match="model must not be empty"):
        build_request_payload("hello", OpenRouterConfig(model=" "))
    with pytest.raises(ValueError, match="missing usage"):
        extract_usage({})
    with pytest.raises(ValueError, match="missing id"):
        runner.response_id({})
    with pytest.raises(ValueError, match="missing model"):
        runner.response_model({})


def test_fetch_completion_records_optional_generation_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode("utf-8")

    responses = iter(
        [
            FakeResponse({"id": "gen-2", "model": "example/model", "usage": {}}),
            FakeResponse({"data": {"provider_name": "example-provider"}}),
        ]
    )
    monkeypatch.setattr(runner, "urlopen", lambda *_args, **_kwargs: next(responses))

    response, generation = runner.fetch_completion(
        prompt="hello",
        config=OpenRouterConfig(model="example/model", timeout_seconds=1),
        api_key="test-key",
    )

    assert response["id"] == "gen-2"
    assert generation == {"data": {"provider_name": "example-provider"}}


def test_cli_requires_provider_pin_and_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("hello", encoding="utf-8")
    common = [
        "--prompt",
        str(prompt),
        "--pair-id",
        "pair-1",
        "--run-id",
        "run-1",
        "--condition",
        "baseline_repo_only",
        "--output-dir",
        str(tmp_path / "out"),
        "--model",
        "example/model:free",
        "--allow-network",
    ]

    assert main(common) == 2
    assert "--provider-only" in capsys.readouterr().err

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert main([*common, "--provider-only", "example-provider"]) == 2
    assert "OPENROUTER_API_KEY" in capsys.readouterr().err
