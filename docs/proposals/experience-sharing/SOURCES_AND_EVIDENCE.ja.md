# 経験・作業状態共有の一次資料と証拠台帳

確認日: **2026-09-24**。関連設計: [AIの経験と作業状態を共有するDSCC](../EXPERIENCE_AND_STATE_SHARING.ja.md)。

この台帳では、著者による報告、公開仕様で確認できること、DSCCへの設計上の示唆を区別する。数値は外部研究の報告であり、DSCCの実測ではない。査読状況や普遍的な性能保証は推定しない。HTML本文で確認した研究には節・表を示し、要旨のみを確認した圧縮研究にはその範囲を明記する。版が更新された場合は、以前の条件を残して追記する。

<a id="s01"></a>
## S01 — ATIFとAgent Data Protocol

一次資料:
- [Harbor ATIF仕様](https://github.com/harbor-framework/harbor/blob/main/rfcs/0001-trajectory-format.md)。確認したファイルのGit blob SHA: `be6ba513be4d30dcafb2674a44b80f49aacce4b8`。
- [ADP README](https://github.com/neulab/agent-data-protocol/blob/main/README.md)。blob SHA: `a278e717fa5729ce0bbcc04df7509b237d8974dd`。
- [ADP ATIF実装](https://github.com/neulab/agent-data-protocol/blob/main/schema/atif.py)。blob SHA: `6b68ac5ee9d54cb4f39f4963f19d6025c7009bae`。

確認箇所: ATIFのIntroduction、Version History、StepObject、文脈管理規約、ADPのData Flowと実装の版検査。Harborの文書はv1.8、確認したADP実装は`ATIF-v1.7`。ATIFは軌跡の交換形式で、ADPは異なるデータをATIF経由で学習用形式へ変換する基盤である。ツール呼び出しと観測の対応、継続・サブエージェント参照、コピーされた文脈、非LLM実行の区別がある。

DSCCへの示唆: 元データ、入力形式の版、変換器の版、変換で失われた項目を保存する。`session_id`を全軌跡の一意IDとして扱わない。形式が再生を想定していても、実環境・外部サービス・副作用の再現は別途設計する。

<a id="s02"></a>
## S02 — OpenTelemetry GenAI agent規約

一次資料: [GenAI agent and framework spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md)。確認箇所: 文書の状態、操作名一覧、Plan、Execute toolの各節。確認時点の状態はDevelopment。

`invoke_agent`、`invoke_workflow`、`plan`、`execute_tool`に加え、操作名一覧には`search_memory`、`update_memory`等がある。計測規約としてハーネス接続の候補になる。操作名の存在だけで、全ライブラリが完全な入力・出力を記録するとは判定しない。

DSCCへの示唆: spanとツール呼び出しIDを原本に対応付け、収集設定、サンプリング、省略、切り詰め、欠落を記録する。監視用トレースを無条件に完全な経験記録として扱わない。

<a id="s03"></a>
## S03 — Trellis / Experience Graphs

一次資料: [Experience Graphs: The Data Foundation for Self-Improving Agents, arXiv:2606.29823v1](https://arxiv.org/html/2606.29823v1)。確認箇所: §4の論理モデル・文脈管理・複数版と時間遡及、§5、§6–7。

成果物、実行結果、評価、分岐、探索統計をデータ基盤の状態として扱い、履歴取得と学習データ抽出へつなぐ提案。KernelEvolveに基づく初期測定も報告されている。DSCCでは原本・探索履歴・派生統計の分離と、過去時点の入力復元を参考にする。

設計上の差: 論文の管理された共有基盤と、DSCCの任意参加・複数運営者・ローカル優先の構成は同一ではない。論文の高速化をDSCCの性能として転記せず、分散整合性、可用性、アクセス制御、独立運営者での運用は別課題にする。

<a id="s04"></a>
## S04 — ExpGraph

一次資料: [ExpGraph: Model-Agnostic Experience Learning with Graph-Structured Memory for LLM Agents, arXiv:2605.30712v1](https://arxiv.org/html/2605.30712v1)。確認箇所: §2.2、§3.1–3.2。

軌跡から短い自然言語の技能・失敗の教訓を作り、意味類似に基づくグラフと有用性の情報で検索する。実行側モデルを固定し、検索側を課題の結果で学習する。全文軌跡を保存すること自体は、この経験要約の目的ではない。

DSCCへの示唆: 原本を残したうえで作る教訓・検索方針の候補。意味類似の辺を、操作の因果関係や仮説の支持関係へ読み替えない。原本の経験グラフと、そこから作る要約グラフを区別する。

<a id="s05"></a>
## S05 — Cross-Model KV Cache Transfer

一次資料: [Cross-Model KV Cache Transfer in LLM Families: A Closed-Form Linear Mapping for Prefill Reuse, arXiv:2608.03893v1](https://arxiv.org/html/2608.03893v1)。確認箇所: §2.1、§3、表1・5、§5、付録G。

同系列で、共有トークナイザーと一致するKVヘッド数・ヘッド次元を持つ組合せを評価。RoPEを外したKey等からリッジ回帰で変換する。Qwen3 14B→32Bの五課題平均保持率は97.6%。Llama 3.1 8B→70BのGSM8K保持率は18.2%で、課題差が大きい。保持率は受信側単独の成績に対する比であり、正答率そのものではない。

表5の32Kでは変換277.6 ms、再プリフィル6975.3 ms。付録Gは受信プロセスへキャッシュを届ける費用を測定していないと明記する。変換がゼロ時間、完全な内部状態コピー、全モデル・全課題で同品質という結果ではない。KV構造が一致することは評価範囲であり、異なる構造への一般化は未検証である。

<a id="s06"></a>
## S06 — CacheBridge

一次資料: [CacheBridge: Efficient Cross-Model KV Cache Transfer, arXiv:2609.00891v1](https://arxiv.org/html/2609.00891v1)。確認箇所: §3、§4.1–4.4、四課題の性能保持表。

ヘッド対応を利用する写像と、アテンションへの影響を考慮した校正を研究。論文内の同条件比較ではMinistral 3の8B→14Bで平均保持率59.43%→97.57%。評価はHellaSwag、ARC-Challenge、WinoGrande、MMLUの部分集合であり、S05のGSM8Kを含む五課題平均とは別の値である。

Qwen3 14B→32Bで4.296 GB→0.538 GBになったのは変換器の保存容量。転送するKV自体がその容量に圧縮されたわけではない。DSCCは変換器の構成・校正・適用費用も記録し、単純な再構成誤差だけで採否を決めない。数学推論の転送問題が解消したとは、この比較から結論しない。

<a id="s07"></a>
## S07 — Cache-to-Cache

一次資料: [Cache-to-Cache: Direct Semantic Communication Between Large Language Models, arXiv:2510.03215](https://arxiv.org/html/2510.03215)。確認箇所: 閲覧時の本文§3.3、式3、融合器の設計。

送信側と受信側のKVを入力し、学習した変換・融合器とゲートを使って受信側へ情報を加える。モデル本体を固定する構成が記載されている。受信側の既存KVも使うため、受信側のプリフィルを不要にするS05と同じ費用モデルではない。

DSCCへの示唆: 状態を置き換える変換器と、現在の状態へ情報を追加する融合器を別の契約として管理する。受信側文脈、入力の対応、注入対象の層、必要な前計算を明示する。

<a id="s08"></a>
## S08 — 共通潜在空間 / K-V Cache Alignment

一次資料: [Latent Space Communication via K-V Cache Alignment, arXiv:2601.06123v1](https://arxiv.org/html/2601.06123v1)。確認箇所: §2–3、§6、付録A。

モデルごとに共通空間への符号化器・復号器を学習する。Gemma-2構造の100M–400Mモデル（トークン埋め込みを除く）を使い、本体を固定して評価。学習したソフトプロンプトの移植も扱う。

DSCCへの示唆: ペアごとの直接写像に加え、複数モデルが接続する潜在空間を登録する候補になる。新しいモデルにも変換器と評価が必要であり、未評価の大規模モデルや商用モデル間の共通言語が完成した証拠にはしない。

<a id="s09"></a>
## S09 — Latent Cache Flow / LCF-X

一次資料: [Latent Cache Flow: Model-to-Model Communication Without Text, arXiv:2605.22863v2](https://arxiv.org/html/2605.22863v2)。確認箇所: §3、§4.1–4.2、§5、付録E。

LCFはKV融合を低次元の経路にし、LCF-Xは送信側の異なる文脈を固定サイズの表現へ集約する。共有文脈の実験はQwen2.5-0.5B-Instruct→Qwen3-0.6B。異文脈の実験は二つのQwen3-0.6BにHotpotQAの資料を分担させ、課題用に注入器を学習している。

DSCCへの示唆: 同じ接頭辞の継続と、異なる資料からの情報取り込みを別に実装・評価する。HotpotQAでの通信結果だけから、長期の試行錯誤や任意の異系列間の経験転移まで実証済みにしない。本文と付録で学習時間・ステップの記載差があるため、その値は性能見積もりに採用していない。

<a id="s10"></a>
## S10 — KV-Distill

一次資料: [KV-Distill: Nearly Lossless Learnable Context Compression for LLMs, arXiv:2503.10337v1](https://arxiv.org/abs/2503.10337v1)。今回の確認範囲: 要旨。

長い文脈のKVを短い表現へ蒸留し、生成分布を近づける方式。圧縮の候補として保持する。DSCCで採用する前に、本文・コード・対応モデル・調整費用・対象課題を精読し、独自の経験転移目的との違いを確認する。要旨の最大圧縮率を、任意の経験で達成できる設計値として使わない。

<a id="s11"></a>
## S11 — KVSculpt

一次資料: [KVSculpt: KV Cache Compression as Distillation, arXiv:2603.27819v1](https://arxiv.org/abs/2603.27819v1)。今回の確認範囲: 要旨。

元のKVを選ぶ・結合するだけでなく、少数の合成KVを最適化してアテンションを近似する方式。Qwen2.5-1.5B-Instructの2048トークン条件等が報告されている。DSCCでは層・ヘッド別の圧縮予算と合わせて検討する候補。最適化費用と未知課題への効果は本文・実装を確認してから採用を判断する。

## DSCC内の根拠と実装状態

確認した基準コミットは`1ffa7de482991223bc3a86336364bbb0c7df58f1`。

- [PR #19](https://github.com/AwakeningOS/DSCC/pull/19): 九つの研究プロファイルと、原本付きのローカル引き継ぎを追加した実装。
- [研究引き継ぎの契約](../../RESEARCH_HANDOFF.md): 全祖先の取得、元の種類・明示された関係の維持。実モデルでの研究継続実証とは区別する。
- [T010](../../tasks/T010.md): 探索取り込み、独立した意味・構造検索、対応付け、転用評価の実装課題。
- [LEC提案](../LATENT_EXPERIENCE.ja.md): 未見問題における経験の効果を評価する既存構想。
- [プロトコル](../../PROTOCOL.md): 制限JSON、小規模レコード、親数・bundle制限、大容量ブロックの別保存。

本資料の追加は、これらの未完了課題を完了扱いにしない。DSCCが外部研究の数値を再現したという報告でもない。

## 更新するときの記録形式

後任は、資料URLと版／commit、確認した節・表、主張、対象モデル・課題・文脈長、比較の分母、測定に含めた費用、実装入手性、DSCCで試した条件、失敗条件を追記する。ベンチマークの平均、正答率、相対保持率、変換器の容量、送信キャッシュの容量を取り違えない。

文献で答えられる問いを先に整理し、DSCCに適用したときに残る問いを実験する。未確認の数値や、この会話での説明だけを一次資料の代わりに追記しない。
