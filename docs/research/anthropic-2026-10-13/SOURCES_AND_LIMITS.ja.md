# Anthropic研究の証拠台帳・確認範囲

確認日: **2026-10-13**。関連する[DSCC設計・受入条件](../2026-10-13-ANTHROPIC_EDGE_HANDOFF.ja.md)。

## 1. 原報告

William Zhou / Daniel Freeman, Anthropic Frontier Red Team, **AI models may be capable of self-replicating without access to a datacenter**, 2026-10-12。
一次資料: https://www.anthropic.com/research/self-replicating-ai

確認範囲: HTML本文の導入・A–G、付録A–F、本文中の表と図表キャプション。公開研究報告として扱い、査読論文・独立追試・DSCCの測定とは呼ばない。原報告全体や攻撃用の実装は転載しない。

<a id="observations"></a>
## 2. 短い観測台帳

以下は著者の報告であり、DSCCの実験値ではない。条件の足りない箇所は下の確認課題へ残す。

| ID | 確認位置 | 報告された範囲 |
|---|---|---|
| A01 | 導入・A | 4GBのTVボックス15台、約55ドル/台でGemma4-26B-A4Bを0.39 token/s。層を分担するPPで、各台2層。 |
| A02 | A | 9Bエージェントが9種類中8種類で環境構築。対象は原則Llama3.1-8B。 |
| A03 | B | 隔離された簡略評価ではGLM-5.2が連鎖完遂。操作するモデルの推論は別サーバで、配置されるモデルと異なる。 |
| A04 | A・付録A | Mementoは前任の作業環境・コード・短いメモを新実行へ継承。設定試験は1回1.5時間、合計6時間。 |
| A05 | D | Qwen3.5-9Bの20系譜・6世代。成功率は初代45%、後続61–84%。 |
| A06 | D | 同9BへのOpus 4.8助言は有意な改善なし。助言利用を別課題でRLした条件も評価。 |
| A07 | 付録B/C | RAM帯域とpipelineの待ちが問題。文脈短縮による課題性能低下、4-bit重みとfp8 KV、入力/出力速度の差を扱う。 |
| A08 | C・結論 | 速度からの規模・所要時間推定と、将来能力の予測は、実機の統合実証と別。 |

## 3. この結果から直接は言えないこと

ここはDSCCへの適用上の分析である。

- A01は指定構成の推論。自由参加WANでの速度、出入りへの耐性、事前学習、費用優位は別の証拠を要する。
- A02の「8/9」は機種の被覆であり、試行成功率88.9%の意味ではない。指定対象と設定役のモデルを分ける。
- A03は小型機だけで司令・推論・評価まで閉じた実証ではない。DSCCの独立性試験では外部依存を層別に除く。
- A05で増えた経験と時間、環境の変更、メモ、新しい実行の効果は、この集計だけでは分解できない。各世代の分母・脱落・raw trialは未確認。同じ系譜の世代を独立標本にしない。
- A06は対象の設定作業・モデル・条件での結果。助言、成果物付きの委譲、全面的な担当交代は同じ介入ではない。
- A07の文脈条件を全タスクの普遍的な必要長として固定しない。付録Bの復旧理由は、TVボックス構成での故障注入の実測保証とは分ける。
- 本稿では原報告の拡散用手順・探索対象・侵入方法を実装へ落とさない。機器所有者が許可した実行だけを設計対象にする。

<a id="figures"></a>
## 4. 動的図表の読み取り状況

### G01: 機種別の環境構築表

https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/04-inference-setup-grid-light.html

HTMLの説明文を取得した。重要な注記は、各runのbest attemptを集計していること、失敗をゼロに入れる表示と成功例だけの表示を選べること、物理機器の列とクラウドの列で同時実行条件が異なること。対象モデルにJetsonの例外があり、9Bのthinking設定も明記される。機種別の全セル値は今回取得できていない。

図にはデータ日付として2026-07-30、ECIには2026-10-01という記述がある。公開日2026-10-12と混同せず、データ収集期間・モデルrevisionとの整合はraw dataで再確認する。本文から不明なモデル版を補完しない。

### 開いたが数値系列を取得できなかった図

- 世代継承: https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/10-learning-over-generations-light.html
- 助言: https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/11-advisor-access-light.html
- 単発/Memento比較: https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/12-single-attempt-vs-memento-light.html
- メモリ: https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/13-memory-per-box-light.html
- 入力処理: https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/14-prefill-speed-light.html
- 出力生成: https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/15-decode-speed-light.html
- 文脈制限: https://assets.claude.ai/brand/artifacts/editorial/ai-worms-figures-blog/16-context-window-light.html

本文のキャプションで確認できる説明はA台帳へ記載した。図を開けたことを数値の全読取りとしない。グラフを目測して生データに変換したり、未取得のp値・信頼区間・各条件の分母を作ったりしない。

作業コンテナから原HTMLを別途取得する試みは名前解決に失敗し、動的図のdownloadも失敗した。本文はweb経由で確認した。原HTMLのbyte snapshotやchecksumを取得したとは主張しない。

<a id="prior-art"></a>
## 5. 補完した一次資料と仕様

### P01 — Petals

- 論文: https://arxiv.org/abs/2209.01188
- 読んだ本文版: https://arxiv.org/html/2209.01188v2
- 初出2022-09-02、v2は2023-03-02。今回の研究より以前の先行技術。

確認箇所: §2.1の層分担と入力保持、§3.2の経路変更・交換先への以前の入力の再送、§4のprivacy/security。

交換先でKVを再構築するには入力が必要。分割・復旧・機密性は別の契約になる。機密データには信頼する参加者や隔離swarmが必要とする記述も確認した。Anthropicの実機でPetalsをそのまま動かしたという意味ではない。今回はPetalsのコード実行・性能再現はしていない。

### P02 — Piの履歴形式

https://pi.dev/docs/latest/session-format

確認箇所: version、entry種類、tree、context building。現行文書はJSONLの親子構造、モデル変更、tool結果の呼出しID、圧縮とモデル可視文脈を説明する。`latest`は可変なので、アダプター実装時はパッケージ版・commitとfixtureを固定する。保存履歴とモデルへの入力、原本と派生要約を区別する設計の参考にする。

### P03 — Piの実行イベント

https://pi.dev/docs/latest/json

JSON/RPCでの実行イベントの公開仕様を確認。保存済みsessionと進行中のevent streamを同一形式と思い込まず、それぞれに変換器と欠落検査を置く。PiそのものがDSCCの所有者権限・隔離を実装するとは扱わない。

### P04 — Piのローカルモデル・隔離資料

- https://pi.dev/docs/latest/llama-cpp
- https://pi.dev/docs/latest/containerization

公開ガイドの存在と対象を確認した。ローカル推論接続と実行隔離を別の接続条件として扱う。今回、Piのインストール・モデル取得・コンテナ起動は行っていない。

**Mementoについて:** 原報告はPiを基にしたと説明するが、今回確認した公開資料から実験用Mementoの完全なコード、forkのcommit、raw trials一式は確定できなかった。現行Piをインストールすれば同じ実験になるとは言えない。「公開されていない」と一般化せず、今回の確認限界として残す。

## 6. DSCC側の参照

基準は`7b730bc8e0765a4d7e3f1c89c83304d1ac518b5e`。

- [README](../../../README.md): 独立性・ローカル実行・任意参加という目的。今回は変更しない。
- [STATUS](../../STATUS.md): 実装と未実装の境界。
- [planner.py](../../../src/dscc/planner.py): GPUフィルター、容量のみの配置、非実行フラグ。
- [研究継承](../../RESEARCH_HANDOFF.md): 原本参照と小記録の祖先closure、大型block除外、拡張情報の扱い。
- [T011](../../tasks/T011.md)、[T012](../../tasks/T012.md): 今回の設計案の受入先。
- [協力者連合](../DSCC_2026_Distributed_AI_Architecture.md): 既知の協力者から始める既存方針。

これは過去の研究台帳の全件監査ではない。新しい方式が採用済みになったとも、全リポジトリのコードを再監査したとも主張しない。

## 7. 採用前に追加取得するもの

1. 実機の型番、実行コードrevision、モデルの正確なartifact、量子化・cache設定、回線・電源条件。
2. 機種別のattempt数、全失敗、固定予算、評価API・検証器、速度の測定方式。
3. Mementoの世代定義、各世代の分母、保持する環境、メモ、raw trajectory、単発との比較予算。
4. 助言条件の入力、呼出し回数、費用、下流実行、評価に使われた全試行。
5. 復旧を主張する場合の故障注入ログ、再送内容、再計算量、数値比較。

不足を二次記事の推測で埋めず、取得できた部分ごとに確認深度を更新する。DSCCでの再現は独立したEvaluationRunへ記録する。
