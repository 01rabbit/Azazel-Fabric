# Azazel-Edge 実 producer 出力の採取 (Fabric#23 B2 用)

- Edge: commit `e84af9a8ca7c9668416db41cd085d17264cbd8b9`(Fabric v0.9.0 pin)。変更なし。
- Fabric: azazel-fabric 0.9.0 (`requirements/fabric.txt`)。Python 3.10 の venv。
- 再生成: `<venv>/bin/python capture.py <Azazel-Edge の checkout> <出力先>`。出力の `*.json`（`refusals.json` を除く）を `tests/fixtures/producer_captures/edge/` に置き、`python3 tools/producer_captures/embed.py` を実行する
  (venv は pytest pydantic PyYAML requests + requirements/fabric.txt)
- 入力は Edge のテストの入力ビルダーをそのまま import して使った(`tests/` を sys.path に足すだけ。Edge 側は無変更)。時刻はすべてテスト内の固定値、乱数なし。
- 決定性: 別プロセスで 2 回実行し、全 JSON がバイト一致(sort_keys, indent=2, 末尾改行)。
- 検証: 下表の全ファイルを Fabric モデルで `model_validate` し通過。署名付きは MAC を除いた本体を検証し、`verify_decision_signature` も True。

行番号は Edge e84af9a のもの。テスト入力の出所は下の「入力」列。

| ファイル | family | Fabric モデル | producer | 入力(テスト) |
|---|---|---|---|---|
| effect_traffic_shaping.json | effect_contracts | DefensiveEffectRef | py/azazel_edge/outcome/effect_export.py:161 `export_defensive_effect_ref` | tests/test_outcome_effect_export.py:54 `a_receipt`, :75 `export`(既定=:92 test_edge_mints_a_typed_effect_reference) |
| effect_isolation.json | effect_contracts | DefensiveEffectRef | 同上 | 同上 + mechanism_kind=ISOLATION(:102 test_the_effect_id_identifies...) |
| engagement_candidate_redirect.json | engagement_contracts | EngagementCandidate | py/azazel_edge/engagement/candidate.py:112 `build_engagement_candidate` | tests/test_engagement_candidate.py:21 `_soc`, :32 `_noc`, :43 `_decision`(:64 test_build_maps_redirect_to_decoy_engagement) |
| engagement_candidate_isolate.json | engagement_contracts | EngagementCandidate | 同上 | 同上 + action=isolate(:102 test_isolate_request_downgraded_to_redirect) |
| engagement_event_redirect_accepted.json | engagement_contracts | EngagementEvent | candidate.py:222 `engagement_event` | :111 test_engagement_event_records_accepted_activity_and_reaction |
| engagement_event_redirect_downgraded_to_notify.json | engagement_contracts | EngagementEvent | candidate.py:222 (内部で :176 evaluate_engagement) | :92 test_downgraded_when_arbiter_chose_weaker_action(attacker_reaction=disengaged は採取側の追加) |
| deception_transition_unsigned.json | deception_contracts | EnvironmentTransitionDecision | py/azazel_edge/deception_transition.py:111 `build_transition_decision` | tests/test_deception_transition.py:25 AS_OF, :29 `_kw`(:43 test_build_produces_canonical_decision) |
| deception_transition_signed.json | deception_contracts | EnvironmentTransitionDecision (+ decision_signature) | 同上(key 指定) | 鍵は Fabric の `GOLDEN_DECISION_SIGNATURE_KEY`、入力は :60 test_build_is_deterministic と同じ |
| deception_transition_from_arbiter.json | deception_contracts | EnvironmentTransitionDecision | deception_transition.py:191 `transition_decision_from_arbiter` | :159 test_from_arbiter_carries_evidence_and_reason(署名なし) |
| outcome_execution_{throttle,redirect}.json | outcome_contracts | ExecutionRefV0 | py/azazel_edge/outcome/shared_export.py:188 `execution_to_shared_v0` | tests/test_outcome_shared_export.py:28 `rust_event`、tests/test_outcome_shared_export_fabric_projection.py:51 `_export_all` と同じ組立 |
| outcome_mechanism_{throttle,redirect}.json | outcome_contracts | MechanismObservationV0 | shared_export.py:216 `mechanism_to_shared_v0` | 同上 |
| outcome_mechanism_throttle_observed.json | outcome_contracts | MechanismObservationV0 | 同上 | test_outcome_shared_export.py:78 test_mechanism_export_preserves_mechanism_not_tactical_effect |
| outcome_mechanism_route_change_degraded_to_unknown.json | outcome_contracts | MechanismObservationV0 | 同上 | :91 test_internal_route_change_is_downgraded_to_unknown_not_invented(縮退: mechanism_kind=unknown + limitations) |
| outcome_outcome_{throttle,redirect}.json | outcome_contracts | OutcomeObservationV0 | shared_export.py:271 `outcome_to_shared_v0` | :116 `_objective`, :128 `_outcome` |
| outcome_assessment_{throttle,redirect}.json | outcome_contracts | TacticalEffectAssessmentRefV0 | shared_export.py:320 `assessment_to_shared_v0` | :169 `_assessment` |

## refusals.json(出力が無いケースの記録)
producer が例外/None を返し、Fabric record を出さないケース。モデルではないので検証対象外。
- effect_no_lease (EffectExportRefused、expires_at 無し; test :207)
- effect_route_change (同、EffectClass に該当無し; test :219)
- effect_unknown_mechanism (同; test :226)
- deception_transition_rejected_status (TransitionDecisionError; test_deception_transition.py:116)
- outcome_execution_expired (SharedOutcomeExportError; test_outcome_shared_export.py:71)
- engagement_disabled (enabled=False で None; test_engagement_candidate.py:56)
- engagement_evaluation_downgraded_plain_dict: `evaluate_engagement` は素の dict を返し Fabric モデルが無い(参考として記録のみ)。

## 注意
- deception_transition_signed.json の `decision_signature` は、Fabric の既存定数 `azazel_fabric.testing.golden.GOLDEN_DECISION_SIGNATURE_KEY`（`golden-fixture-transport-key-v1`）による HMAC（2026-11-05 オーナー判断で Fabric の定数に統一）。秘密ではなく、実運用鍵でもない。consumer 試験はこの定数で検証する。
- 署名付き JSON は `decision_signature` が EnvironmentTransitionDecision のフィールドではない(extra=forbid)ため、モデル検証は MAC を除いた本体に対して行う。
- IP・ホスト名は出力に含まれない(scope は digest、outcome は metrics のみ)。ID は `edge-1` `decision-1` `env-1` 等のテスト用ラベルと、Edge が決定的に導出するハッシュ。時刻は 2026-08/09 の固定値。
