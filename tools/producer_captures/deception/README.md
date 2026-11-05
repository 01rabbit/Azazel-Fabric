# Azazel-Deception 実 producer 出力の採取 (Fabric#23 B2 用)

- Deception commit: `305af85` (main, Fabric v0.9.0 pin)。採取時 azazel-fabric 0.9.0 / pydantic 2.14.2。
- 再生成: `<venv>/bin/python capture.py <Azazel-Deception の checkout> <出力先>`。出力の `*.json`（`refusals.json` を除く）を `tests/fixtures/producer_captures/deception/` に置き、`python3 tools/producer_captures/embed.py` を実行する
  (venv は Deception の checkout で `pip install -e '.[dev]'`)
- 決定性: 2 回実行して全ファイルがバイト一致 (JSON は `sort_keys`, indent=2, 末尾改行)。時刻は固定リテラル、乱数なし。
- 検証: 全 JSON を下表の Fabric v0.9.0 モデルで `model_validate` して通過 (capture.py 末尾で毎回実行)。
- 入力はすべて Deception のテストの値をそのまま借用。製品リポジトリは未変更。

producer の位置: `observation_export.py:39 export_observations` / `effect_projection.py:356 project_presented_terrain`, `:627 observe_effect` / `outcome_export.py:102 presented_terrain_lifecycle_outcome` (すべて src/azazel_deception/runtime/)。

| ファイル | family | Fabric モデル | producer | 入力の出所 |
|---|---|---|---|---|
| deception_contracts_interaction_observation_interaction_port.json | deception_contracts | InteractionObservation | export_observations (+ InteractionObserver.record, observation.py) | tests/test_observation_export.py:81 (同じ構成。runtime_context 付き、observed_at 固定、`_host` は tests/test_runtime.py:19) |
| deception_contracts_interaction_observation_reaction_service.json | 同上 | 同上 | 同上 | 同上 (reaction/enumerate、latency・dwell・attempt・confounder 入り) |
| deception_contracts_interaction_observation_export_list.json | 同上 | InteractionObservation の配列 (export_observations の戻りそのまま) | 同上 | 同上。lifecycle イベントが除外されることも反映 |
| effect_contracts_presented_terrain_ref_live.json | effect_contracts | PresentedTerrainRef | project_presented_terrain | tests/test_effect_contracts_producer.py:77 `_snapshot` 既定, :116 |
| effect_contracts_presented_terrain_ref_live_bound_to_decided_effect.json | 同上 | 同上 | 同上 (source_effect=decided) | :375 `_decided_effect` |
| effect_contracts_presented_terrain_ref_shadow_stale.json | 同上 | 同上 (planned_shadow, stale) | 同上 (source_effect=shadow) | :356 `_shadow_effect`, `_SHADOW_SNAPSHOT` |
| effect_contracts_presented_terrain_ref_synthetic_refs.json | 同上 | 同上 (artifact/identity/credential 参照入り) | 同上 | :563 (identity:finance:clerk-1 / credential:smb:clerk-1) + artifact:honey:invoice-2026 (:50 付近の定数) |
| effect_contracts_effect_observation_active.json | 同上 | EffectObservation | observe_effect | :336 + :818 `an_edge_effect` |
| effect_contracts_effect_observation_terminated.json | 同上 | 同上 (observed_fact) | 同上 | 同上。status/終了理由/時刻のみ当方で指定 (テストに terminated の例なし) |
| outcome_contracts_presented_terrain_lifecycle_during.json | outcome_contracts | OutcomeObservationV0 | presented_terrain_lifecycle_outcome | tests/test_cross_product_golden_outcome.py:13。Deception 自身の tests/fixtures/outcome/cross_product_presented_terrain_outcome_v0.json と JSON 一致を確認 |
| outcome_contracts_presented_terrain_lifecycle_after_reset.json | 同上 | 同上 (phase=after) | 同上 | tests/test_presented_terrain_outcome_export.py:61 の形 (時刻は golden 側の値に揃えた) |

## 拒否・縮退 (refusals.json、Fabric モデルの出力ではなく例外の記録)
例外型とメッセージを記録。いずれも該当テストと同じ入力で発生を確認済み。
- EffectProjectionRefused: no_expiry (:214), two_isolation_assertions (:234), untyped_identity (:575), non_snapshot (:262)
- EffectRefRejected: shadow effect を live terrain に束縛 (:482)、accept_defensive_effect_ref の planned_shadow / advisory_inference (:846)
- ValueError (outcome): stale snapshot (test_presented_terrain_outcome_export.py:76)、telemetry_coverage に attacker_belief (:88 付近の形)

## 秘密・実値の確認
実 IP・ホスト名・パス・メール・認証情報本文・壁時計時刻なし (grep 確認)。credential/identity は `credential:smb:clerk-1` `identity:finance:clerk-1` の合成参照のみ。node は `az06-test` `edge-1` 等のテスト値、時刻は 2026-01-01 / 2026-08-26 / 2026-09-20 の固定値。

## 未採取
- accept_defensive_effect_ref の成功出力 (DefensiveEffectRef): 受信した Edge の payload の再検証であり Deception が生成するデータではないため対象外。
