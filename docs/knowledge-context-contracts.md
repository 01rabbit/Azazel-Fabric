# Knowledge Context 契約（v1 意味ペイロード）

実装: `azazel_fabric.knowledge_context`。Fabric Issue #72 に対応する最初の候補スライス。

状態: **experimental**（互換性の約束なし）。最初に含まれる版は `0.10.0rc1`。採用状況と experimental の理由は [release compatibility](release-compatibility.md#contract-family-adoption-and-the-r1c-gate) を参照。

これは **記述のみ** の契約である。認証、資格情報、トランスポート、鍵 ID、署名、コミッショニング、経路、ネットワーククライアント、ローカルポリシーの受理判断、学習、推論、強制は含まない。それらは利用側（consumer adapter）と別のトランスポート層の責務である。

## ペイロード

| スキーマ | クラス |
| --- | --- |
| `knowledge-context-request/v1` | `KnowledgeContextRequestV1` |
| `knowledge-context-response/v1` | `KnowledgeContextResponseV1` |

- すべてのモデルは frozen かつ `extra="forbid"`。`schema_version` は必須の定数で、未知のバージョンは拒否する。
- リクエスト: `request_id`, `correlation_id`, `source_product`, `source_ref`, `requested_at`, 有界な `entities`（種別 + 値）。生イベント、フレーム、任意のメタデータマップは持てない。
- レスポンス: リクエストの `request_id` / `correlation_id` / `source_product` / `source_ref` をそのまま返し、`provider_id`、`snapshot`（`ref` / `state` / `as_of`）、`facts`、`inferences`、`unknowns`、`limitations`、`generated_at`、`expires_at`、定数 `authority = "advisory_only"` を持つ（入力では `authority` を省略でき、正規出力には必ず含む）。snapshot state は `complete` / `partial` / `stale`。取得不能は成功レスポンスではなく、consumer 側の transport 結果として表す。
- consumer は `assert_response_correlates(request, response)` で4つの相関値の一致と `generated_at >= requested_at`、すべての `facts` / `inferences` の `subject` が依頼 `entities` 内にあることを検証する。この補助関数は身元・署名・現在時刻に対する鮮度を検証しない。
- `facts`（`SourceReportedFact`）は「ソースがこう報告した」という主張で、真実の保証ではない。有界で重複のない `provenance` 参照を必須とする。
- `inferences`（`InferenceClaim`）は別の型で、有界で重複のない `method_refs` と根拠となる `basis_fact_ids` を必須とする。思考過程（chain-of-thought）の欄は無い。
- `unknowns` と `limitations` は必須の明示欄（空は可）。

## 信頼の姿勢

- `source_product`、`provider_id`、各 `*_ref` は **相関用の主張** であり、認証済みの身元ではない。ref はopaqueな識別値で、文字列 `://` を含められない。その他の表記がURIらしく見えても、consumerはネットワーク取得先として解決・参照しない。
- 自由記述テキストと提供者の身元はすべて信頼できないデータである。長さと `str.isprintable()` による印字可能性は制限するが、内容の意味は検証しない（Unicodeの印字可能性判定はPythonのUnicode databaseに依存し、正規化もしない）。資格情報や秘密が文章に混ざらないようにする責任は、送出側アダプタにある。
- ソース側の署名があっても、それは内容の真実性を認証しない。
- 初期の P0 フィルタや、サービス固有の TTL 値は、このスキーマには入れない（consumer adapter が行う）。

## 検証

- 上限は定数（`MAX_ENTITIES=32`, `MAX_FACTS=64`, `MAX_INFERENCES=32`, `MAX_PROVENANCE_REFS=8`, `MAX_METHOD_REFS=8`, `MAX_BASIS_FACTS=16`, `MAX_UNKNOWNS=16`, `MAX_LIMITATIONS=16`、文字列長は各 `MAX_*_LENGTH`）と Pydantic の制約で強制する。さらに request/response の合計正規化 JSON は既存の共有 MIO 128 KiB 上限で検証する。
- `Identifier` / `ProductName` / `Token` / `OpaqueRef` は厳格な `str`（bool や数値を暗黙変換しない）で、正規表現 `[A-Za-z0-9_][A-Za-z0-9_.:/@+\-]*` に一致する ASCII のみを受け入れる。`OpaqueRef` はさらに `://` を拒否する。
- 時刻は UTC オフセット付きの ISO 8601 文字列、またはタイムゾーン付き `datetime` のみ。ナイーブな時刻、日付のみ、数値のタイムスタンプは拒否する。
- 辞書入力は、既存の `mio_contracts.validation.assert_no_mio_directives` でキーを再帰的に走査し、指示・ツール呼び出し・リンク形の欄を拒否する。自由記述の値は走査・無害化しない。命令のような文章も非信頼データとして保持されるため、consumerは命令として実行してはならない。
- `fact_id` / `inference_id` の重複、事実 ID と推論 ID の衝突、存在しない `basis_fact_ids` への参照、重複する `provenance` / `method_refs`、`snapshot.as_of > generated_at`、`expires_at <= generated_at` を拒否する。
- Fabric は壁時計を参照しない。「現在時刻に対して期限切れか」の判断は行わない。

## 正規化 JSON と境界

`canonical_knowledge_context_bytes(model)` は、検証済みモデルから決定的な UTF-8 JSON を返す。正規化前に再検証するため、`model_copy(update=...)` 等で検証を迂回したモデルは拒否する。キーはソート済み、余分な空白なし、非 ASCII はそのまま、NaN は拒否、時刻は UTC の `Z` 形式。配列（`entities`、`facts`、`inferences`、`unknowns`、`limitations` など）は入力順を保持し、並べ替えない。要素順を変えると署名対象のバイト列も変わるが、この契約は順序に順位付けの意味を定めない。同じ検証済みペイロードは常に同じバイト列になる。

リクエストとレスポンスを結びつける前に、consumerは4つの相関値が一致することを確認する。相関値はtransport認証の代わりにならない。

- **Fabric は署名しない。** このバイト列は、利用側トランスポート層が後で署名するのに適した入力である。鍵、鍵 ID、署名、検証はこのモジュールの範囲外。
- **意味上の `expires_at` はスナップショット応答の鮮度** であり、外側のトランスポートの有効期限や身元ポリシーとは別物である。トランスポート側の期限切れや認証の判断は、この契約では表現も代替もしない。
- Fabric は時計を参照しないサービス非依存の契約であるため、全体に適用される最大応答遅延や、意味上の `expires_at` の標準的な有効期間（鮮度の長さ）を定義しない。consumer は次をそれぞれ設定して強制しなければならない: (a) `generated_at - requested_at` で測る要求から応答までの最大遅延、(b) 現在時刻から `generated_at` までの許容範囲と `generated_at - snapshot.as_of` で測るsnapshotの最大古さ、(c) `expires_at - generated_at` で測る意味上の鮮度ウィンドウ上限、(d) 外側の認証済みトランスポート TTL。さらにconsumerは現在時刻が `expires_at` に達した応答を拒否しなければならない。`snapshot.state = "stale"` は `expires_at` が未来でも stale のままであり、期限値によって complete/fresh に昇格しない。
- たとえば consumer が外側の署名付き応答 TTL に 30 秒を選ぶ場合、その値はトランスポートの再送（リプレイ）を制限するが、共有の意味上の最大経過時間（max-age）を定義するものではない。
- ペイロードは生成時に既存の `assert_bounded_mio_payload` と同じ 128 KiB 合計サイズ上限を通過する。各フィールドが個別上限内でも、合計が超えれば拒否する。

## ゴールデンフィクスチャ

`tests/fixtures/knowledge_context/request_v1.json` と `response_v1.json` は正規化形式（末尾に改行 1 つ）で保存してある。ラウンドトリップ後の正規化バイト列がこのファイルと一致することを `tests/test_knowledge_context_contract.py` が確認する。
