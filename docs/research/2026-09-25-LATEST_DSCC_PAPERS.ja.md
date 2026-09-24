# DSCC 最新研究スカウト — 2026-09-25

状態: **一次資料を起点にした実装引き継ぎ資料。ここに記載した外部研究の性能はDSCCで再現した結果ではない。**  
確認日: **2026-09-25**  
確認したDSCC: `a8585672ead140f0e40588a69f821b9631defd98`  
関連: [Distributed AI Research Laboratory](../proposals/DISTRIBUTED_AI_RESEARCH_LAB.ja.md)、[Distributed Open Model Commons](../proposals/DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md)、[Experience and State Sharing](../proposals/EXPERIENCE_AND_STATE_SHARING.ja.md)、[GLOBAL_SCALE_CHALLENGES](../GLOBAL_SCALE_CHALLENGES.ja.md)、[TASKS](../TASKS.md)。

## 1. この資料の使い方

このスカウトは、新しい論文を「面白そうな一覧」で終わらせず、DSCCの既存Task・G-ID・ES-IDへ接続して、別の開発エージェントが実装候補を切り出せる状態にするための資料である。

各論文について、次を分けて記録する。

- **既知研究で示されたこと**: 論文・公開仕様・公式実装が報告している範囲。
- **DSCCに効く理由**: 現在のアーキテクチャのどの不足へ接続するか。
- **実装候補**: その研究をDSCCへ適用するなら何を作るか。
- **受入証拠**: 「採用できた」と判断する前に何を測るか。
- **境界**: 論文の結果から言えないこと。

実装担当は、論文だけでなく公開コード・版・ライセンス・依存関係を再確認し、既存Issueで担当範囲を宣言する。新しいTaskやADRが必要な場合は、既存の署名/CID、権限、実行境界を黙って変更しない。

## 2. 優先度別サマリー

| ID | 論文 / 資料 | DSCC接続 | 優先 | 実装開始条件 |
|---|---|---|---|---|
| R01 | AIDE²: Recursive self-improvement of AI research agents | T012 / G071-G075 | P0 | ローカル評価契約は設計可能。自律改変実行はT003等が必要 |
| R02 | KVShareArena | T011 / LEC / ES06-ES11 | P0 | ベンチ統合・評価設計は開始可能 |
| R03 | XKV: Dual-Cache Latent Space Communication | LEC / T011 / ES06-ES09 | P0 | 状態/変換器profile設計は開始可能。実測はモデルruntime必要 |
| R04 | Decoupled DiLoCo | T011 / G034-G056 | P0 | trusted-site小規模prototypeはT003/T006後 |
| R05 | FML-Bench | T010 / T012 / G071-G073 | P0 | 外部bench adapter・process metric設計は開始可能 |
| R06 | When Latent Agents Lie | T009 / T011 / ES12-ES13 | P0 | cache manifest/integrity contract設計は開始可能 |
| R07 | P2P prefix-cache-aware inference | T005 / T011 / G032/G050/G051 | P1 | transportとruntimeの実装後 |
| R08 | CacheScout | T011 / T012 / G050/G073 | P1 | agent workflow実行基盤・cache runtime後 |
| R09 | VeriAttn | T009 / T011 / G023-G030 | P1 | TEE/GPU実機環境が必要 |
| R10 | OpenPCC | T009 / T011 / G047/G052 | P1 | TEE attestation実機環境が必要 |
| R11 | Agent communication protocol taxonomy | T002 / T005 / T012 | P1 | アーキテクチャ設計へ即反映可能 |
| R12 | Governance gaps in agent protocols | T012 / G063-G076 | P1 | 研究統治契約の設計へ即反映可能 |
| R13 | Autonomous Research Agents survey | T009 / T012 / G066/G067/G072 | P0 | 研究runの監査項目へ即反映可能 |
| R14 | AI-Research Agents in the Wild | T012 / G066 | P1 | 既存agent再利用調査へ即利用可能 |
| R15 | Memory × multi-trajectory inference | T010 / T012 / ES08/ES15 | P0 | retrieval/search評価設計へ即反映可能 |
| R16 | CacheBridge | LEC / T011 / ES06-ES10 | P0 | 既存S06の更新・adapter評価設計へ反映可能 |

P0/P1はDSCCへの接続優先度であり、論文そのものの科学的価値ランキングではない。

---

## 3. R01 — Recursive self-improvement of AI research agents (AIDE²)

一次資料: https://arxiv.org/abs/2609.26457  
公開日: 2026-09-22。

### 既知研究

AIDE²は、研究エージェント自身のharness codeを外側の探索対象にする二重ループを実装する。内側のagentがAI R&D課題を固定予算で最適化し、外側のagentがその研究agent自体を書き換える。候補はagentが見ないprivate held-out評価で採点され、受理されたrewriteが次世代のincumbentになる。

論文は8日間の自律runで100-nodeの系譜を生成し、7回の更新を受理したと報告する。外部のheld-out benchmarkでも改善を評価し、選択信号とagentが直接見る信号を分離する。

### DSCCに効く理由

T012の最終段階である「研究agent自身を研究対象へ戻し、改良されたagentが次cycleへ参加する」を、具体的な実験プロトコルへ落とせる。特に、**agent lineage、固定budget、public/private評価分離、候補の不採用履歴**はDSCCが保存すべきArtifactと一致する。

### 実装候補

1. `AgentVersion` / `AgentEvaluation` / `AgentPromotion`相当のversioned payloadを、既存seed kindの上に追加するADRを検討する。
2. agentのcode/config/prompt/retrieval policy/model idをCIDで固定し、各candidateがどのparent agentから派生したかを記録する。
3. T012 ResearchStateに「現在のincumbent」「未採用branch」「評価artifact」「次に編集する対象」を接続する。
4. outer-loop graderが見るprivate evaluationを、agent-visibleなArtifactと別のaccess scopeに置く設計をT001と調整する。
5. 受理・不受理を最終scoreだけでなく、cost、失敗、reward-hacking検査、held-out generalizationと一緒に保存する。

### 受入証拠

- 同じagent versionを同じbudget・同じ環境で再評価できる。
- agent-visible signalとpromotion signalの混入をテストできる。
- 改良候補が追加computeだけで勝っていないことをbudget receiptで検査できる。
- 選択に使わないheld-out taskで改善が維持されるか測る。
- agentが自分の評価器・権限・秘密testを勝手に変更できない。

### 境界

AIDE²の成功は、世界分散・敵対的参加者・異種モデル混在のDSCCで自動的に成立する証拠ではない。DSCCではagent codeの自動変更権限とpromotion権限を分離する必要がある。

---

## 4. R02 — KVShareArena: KV-Cache Reuse Across Contexts and Model Checkpoints

一次資料: https://arxiv.org/abs/2609.10266  
公開日: 2026-09-09。

### 既知研究

KVShareArenaは、完全一致prefix以外のKV再利用を、RAG chunk、他agentのreport、model checkpoint差を含めて評価する。論文は、未修復cacheが「cacheなし」より悪化する場合、位置補正だけで足りる条件、複数sourceが必要な条件では再encodingや学習が必要になること、checkpoint差でadapter方式の挙動が変わることを報告する。

### DSCCに効く理由

Experience and State Sharingの「同じprefixの継続」「異なる文脈からの情報追加」「checkpoint差」を別の問題として扱う方針を、そのまま評価できる。LEC/KV転送を実装する前に、**採用/拒否を決める共通benchmark gate**として使える。

### 実装候補

- `experiments/kv-reuse/`に外部benchmark adapterを作り、DSCCのmodel/cache/converter profileから評価ケースを生成する。
- 結果を`EvaluationRun`として保存し、source model、target model、context relation、repair method、latency、VRAM、cache bytesを記録する。
- 「直接再利用」「位置修正」「再encoding」「学習adapter」「targetでfull recompute」を同じcost ledgerで比較する。
- cache profileごとに、許可された用途を `exact-prefix / relocated / multi-source / checkpoint-transfer` のように区別する案をADRへ昇格する。

### 受入証拠

- cacheがある状態からのper-request costと、cacheを作るone-time costを分離する。
- full recomputeとの差だけでなく、cacheなしとの差も記録する。
- task/model/context別のnegative transferを保存し、平均値だけでadapterを承認しない。

---

## 5. R03 — XKV: Dual-Cache Latent Space Communication between Heterogeneous Language Models

一次資料: https://arxiv.org/abs/2608.20617  
公開日: 2026-08-20。

### 既知研究

XKVはSharerとReceiver双方のcacheを用いて、異なるfamily、depth、KV-head数、head dimension、tokenizerを持つモデル間の潜在通信を扱う。両モデル本体をfreezeし、translatorのみ学習する。論文は45のdataset-model-pair設定でLCF-Xやtext communication等と比較している。

### DSCCに効く理由

既存のExperience and State Sharingでは「pairwise converter」「共通latent」「receiver側状態への融合」を別契約にする方針を置いた。XKVは、**receiverの現在状態を使って他モデルの情報を取り込むheterogeneous translator**の具体候補になる。

### 実装候補

- OMCに`latent-converter`用manifestを設計し、source/receiver model CID、cache geometry、layer map、tokenizer、training dataset lineage、converter weights CID、injection methodを固定する。
- adapterは「prefix replacement」ではなく「receiver-state-conditioned fusion」として別classにする。
- converter directionを有向として記録し、A→Bの成功からB→Aを推定しない。

### 受入証拠

- unseen task / unseen contextでtext communication、full receiver read、no-transferと比較する。
- converterのtraining dataと最終評価source lineageを分離する。
- translator paramsだけでなく、cache transfer量・receiver cache生成費用・end-to-end latencyを測る。

---

## 6. R04 — Decoupled DiLoCo for Resilient Distributed Pre-training

一次資料: https://arxiv.org/abs/2604.21428  
公式解説: https://deepmind.google/blog/decoupled-diloco/  
公開日: 2026-04-23。

### 既知研究

Decoupled DiLoCoは複数learnerをlock-step同期から切り離し、local optimization後のparameter fragmentを非同期に集約する。minimum quorum、adaptive grace window、token-weighted mergeでstraggler/failureへ対処する。論文はfailure-proneな大規模simulationでglobal downtimeを回避しつつ性能を評価する。

### DSCCに効く理由

T011/G034/G054の「WAN・churn・非同期・低通信量pre-training」に直接関係する。家庭GPUが常時同期する設計より自然。ただし論文のcentral synchronizerをDSCCへそのまま必須化するのは、中央障害点を避ける目標と衝突する。

### 実装候補

1. 最初はtrusted LAN/複数processの小型modelでlearner-island prototypeを作る。
2. update fragment、local token count、parent checkpoint、runtime profile、merge receiptをTrainingRunへ接続する。
3. straggler、learner crash、late update、duplicate update、resumeを注入するchaos testを作る。
4. central synchronizer版をbaselineとして実装した後、replaceable/federated synchronizerやepoch単位のleader交代を研究対象にする。

### 受入証拠

- 同じ総token budgetで同期baselineとquality/goodput/communicationを比較。
- failure injected時のdowntime、staleness、checkpoint recoveryを実測。
- heterogeneous GPU・precision差は別実験として記録し、simulation結果から家庭GPU対応を推定しない。

---

## 7. R05 — FML-Bench

一次資料: https://arxiv.org/abs/2605.17373  
公開実装: https://github.com/qrzou/FML-bench  
公開日: 2026-05-17、v2 2026-05-29。

### 既知研究

18のML research task、10 domain、12のprocess-level metricを持ち、agent strategyとexecution infrastructureを分離する。単純なgreedy searchが強い条件、広い探索へ切り替える方がよい停滞条件を分析し、adaptive strategyも評価する。

### DSCCに効く理由

T012のresearch-agent能力評価と、T010 Exploration Atlasの「探索の仕方」を直接測れる。最終scoreだけでなく、探索過程のmetricをDSCC Artifactへ保存できる。

### 実装候補

- FML-Benchを外部benchmark adapterとして接続し、agent/model/providerを交換しても同一task/configでrunできるwrapperを作る。
- process metricをExploration Atlas Episodeへ対応付ける。
- stagnation detectionを「戦略切替の候補signal」として保存し、製品ロジックへ即固定しない。

### 受入証拠

- agent strategyを変えてもexecution harnessが同じであることを記録。
- score、token/cost、試行数、branching、failure recoveryを同じRunへ保存。
- adaptive policyを、選択に使っていないtaskで評価する。

---

## 8. R06 — When Latent Agents Lie: KV-Cache Integrity in Multi-Agent LLM Collaboration

一次資料: https://arxiv.org/abs/2606.28958  
公開日: 2026-06-27。

### 既知研究

multi-agent systemでvisible messageとKV stateを同時に渡す構成に対し、latent stateの改変・poisoningを扱う。cleanなlatent collaborationの利点と、malicious specialistがhidden state経由で最終回答へ影響する問題を評価する。

### DSCCに効く理由

LEC/KV共有を始めると、通常のArtifactより大きく検査しづらいlatent blobが攻撃面になる。現行DSCCのlarge blockはCIDで内容同一性を検査できるが、**そのblockが「どのmodel/session/prefix/cache geometryに属するか」まで暗号的にbindingしたmanifest**が必要になる。

### 実装候補

- cache/latent manifestにblob CID、model CID、cache profile、source context CID、session/run、tensor metadata、converter CID、producer keyを結び付けて署名する。
- 外部研究で扱われる認証付きtransport／MAC系の防御をそのまま唯一解にせず、DSCCではCID + Ed25519署名による公開検証可能manifestも比較する。
- manifest mismatch、replay、cross-session substitution、converter substitutionをT009の攻撃テストへ追加する。

### 受入証拠

- 1 byte改変だけでなく、正しいblobを別session/modelへ差し替える攻撃もfail-closedになる。
- integrity validとscientific usefulness/safetyを別状態として保持する。
- untrusted latentを注入前に隔離評価できる。

---

## 9. R07 — Towards Distributed Inference of LLMs on a P2P Network

一次資料: https://arxiv.org/abs/2606.17059  
公開日: 2026-05-07。

### 既知研究

各peerがlocal prefix radix treeと、anti-entropyで非同期更新する他peerのcache推定を持ち、推定上の最長prefix matchへrequestをrouteする。stale metadataはcache missを増やすが、workerがfull modelを実行できる限り出力の正しさを壊さないため、strong consistencyを不要にする設計。

### DSCCに効く理由

T005/T011で、**性能用metadataはeventual consistencyでよいが、権限・model identity・結果のprovenanceは強く検証する**という分離を作れる。

### 実装候補

- cache availabilityを再構築可能なsoft-state indexとしてtransport層から分離する。
- peer cache summaryにTTL/generation/model profileを付ける。
- stale route時は安全にlocal/full-prefillへfallbackする。
- permissionやjob authorizationを、この弱整合cache indexへ載せない。

### 受入証拠

- metadata loss/stalenessがcorrectnessではなく性能劣化に限定される。
- latency、hotspot、skew、churn、relay経由を実ネットワークで測る。
- simulationだけでWAN性能を確定しない。

---

## 10. R08 — CacheScout: Learning Agent Execution for KV-Cache Management in Agentic Serving

一次資料: https://arxiv.org/abs/2608.14624  
公開日: 2026-07-16。

### 既知研究

multi-agent workflowでagent実行遷移をonlineに学習し、recencyだけでなく「次にどのagent contextが使われるか」でcache eviction/prefetchを行う。vLLM上の実装でKV hit率、TTFT、per-turn latency、throughput改善を報告する。

### DSCCに効く理由

T012のresearch workflowとT011のservingがつながると、Literature→Code→Evaluatorのような実行系列が蓄積する。Experience Graphの履歴を、研究の意味検索だけでなく**計算配置・cache prefetchのsignal**へ利用できる。

### 実装候補

- agent/workflow transition modelをderived indexとして保存し、原本trajectoryから再構築可能にする。
- schedulerへprefetch hintを渡すが、権限や必須routingには使わない。
- workload変化で古いtransitionが害になるためgeneration/decayを持たせる。

### 受入証拠

- LRU/prefix-cache baselineと同じworkloadでhit率・TTFT・VRAM・prefetch wasteを測る。
- workflow変更後のnegative transferを測る。
- prefetchが他jobの公平性やowner quotaを破らない。

---

## 11. R09 — Communication-Efficient Verifiable Attention for LLM Inference (VeriAttn)

一次資料: https://arxiv.org/abs/2606.16352  
公開日: 2026-06。

### 既知研究

untrusted GPUへattention計算をoffloadしつつTEE側で検証する設計。prefill/decodeの通信・検証overheadを減らすためのpipelineやcache partitionを提案し、Intel TDX環境で既存TEE-shielded partitioningとの比較を報告する。

### DSCCに効く理由

G023-G030の「remote workerが正しい計算を返したか」「検証コストを本計算より小さくできるか」に直結する。

### 実装候補

- 直ちにcoreへ組み込まず、Verification adapter候補としてT009/T011の調査対象に登録する。
- TEE attestation、GPU runtime、model hash、verified region、unverified regionをVerificationReceiptへ対応付ける。

### 受入証拠

- correctness fault injectionとmalicious GPU modelを区別した試験。
- TEE-GPU通信量、prefill/decode overhead、対応hardwareを実測。
- TEEが使えない一般consumer環境では別verification経路へfallbackする。

---

## 12. R10 — OpenPCC: Open and Confidential LLM Serving on Commodity TEEs

一次資料: https://arxiv.org/abs/2606.11145  
公開実装: https://github.com/openpcc/openpcc  
公開日: 2026-06。

### 既知研究

commercially available TEEを使ったconfidential LLM serving frameworkを提示し、Llama-3 8B + vLLMのprototypeを評価する。prompt/output/logをservice providerから保護する方向の設計。

### DSCCに効く理由

G047/G052の「private research dataやKVを他者のworkerへ渡す」問題に対応する候補。T011のpublic inferenceを現実化する際、compute integrityとdata confidentialityを別々に扱う必要がある。

### 実装候補

- `confidential_compute` capability profileを将来のruntime matrixに追加するADR候補。
- attestation evidenceをArtifactとして保存し、model/runtime digestとsessionへbindingする。
- confidential routeをowner policyが要求できるようT001/T011のpolicyへ接続する。

### 受入証拠

- attestation failure時fail-closed。
- host/operatorからprompt/outputが見えない境界を実機で確認。
- GPU/CPU TEEの保証範囲・driver・DMA・log経路を明記。

---

## 13. R11 — A Technical Taxonomy of LLM Agent Communication Protocols

一次資料: https://arxiv.org/abs/2606.19135  
公開日: 2026-06-17。

### 既知研究

9つのactive open-source protocolを、counterparty、payload、interaction state、discovery、schema flexibilityの5次元で分類する。長期的には単一protocolよりfederated/layered stackへ進む可能性を論じる。

### DSCCに効く理由

DSCCはMCP、P2P transport、Artifact protocol、Research protocol、Experience protocolを持つ方向にある。これらを一つの万能schemaに押し込まず、**責任境界を持つ層**として設計する根拠になる。

### 実装候補

- Architecture文書にprotocol responsibility matrixを追加する。
- 「tool/data接続」「agent間message」「artifact transfer」「research semantics」「governance」を別interfaceにする。
- 各adapterが何を保証しないかを明記する。

### 受入証拠

- 同じ研究handoffを複数host protocol経由で再現し、DSCC Artifact/CIDが不変である。
- transport交換で研究意味論やowner authorityが変わらない。

---

## 14. R12 — Governance Gaps in Agent Interoperability Protocols

一次資料: https://arxiv.org/abs/2606.31498  
公開日: 2026-06-30。

### 既知研究

MCP、A2A、ACP、ANP、ERC-8004をmembership、deliberation、voting、dissent preservation、human escalation、audit/replayの6軸で比較し、agent community governanceは既存interoperability protocolの上位層として必要だと論じる。

### DSCCに効く理由

T012は既に`contradicts`や`supersedes`を保存する。世界規模研究所では、transport protocolに研究上の合意形成を任せず、**反対意見を消さない研究統治層**が必要になる。

### 実装候補

- ResearchStateにmembership/policyを直接埋め込まず、別PolicyProfile/DecisionRecordへ分ける。
- human escalation、review requirement、promotion threshold、dissent retentionをproject policyとしてversion管理する。
- votingをscientific truth判定に使わず、resource allocationやrelease promotion等のgovernance actionへ限定する。

### 受入証拠

- 少数意見・contradicting evidenceが投票で削除されない。
- policy revisionと決定時点のpolicyを監査できる。
- transport上のidentityと研究上のauthorityを分離する。

---

## 15. R13 — Autonomous Research Agents: A Survey of AI Scientists and the Verification Gap

一次資料: https://arxiv.org/abs/2608.05179  
初回公開日: 2026-06-29。

### 既知研究

125候補から35 workを含め、24 runnable system等をauditする。code releaseに比べ、seed/execution trace、novelty verification、result-selection disclosureなどの再現・検証artifactが不足する傾向を報告する。

### DSCCに効く理由

DSCCが「最終paper」よりも、**実行trace、選択されたrun、失敗、novelty確認、評価者、原本**を保存する理由を裏付ける。T012の研究agentが生成したclaimを、runした事実だけでverifiedにしないためのチェックリストになる。

### 実装候補

各ResearchState / EvaluationRunについて、少なくとも以下の監査項目をreportへ追加する候補とする。

- agent/model/provider/snapshot
- prompt/harness/code revision
- seedまたはdeterminism class
- execution trace
- baseline provenance
- run selection policy
- novelty/overlap check
- human intervention
- independent verification status

### 受入証拠

- 「実行済み」「再現済み」「独立検証済み」「新規性確認済み」を別状態で問い合わせられる。
- best-runだけ公開して失敗runを隠した場合にselection disclosure不足として表示できる。

---

## 16. R14 — AI-Research Agents in the Wild

一次資料: https://arxiv.org/abs/2609.11975  
公開日: 2026-09-01。

### 既知研究

2026-06-10でfreezeしたsource-grounded registryとして139のcanonical public repositoryと101 paperを整理し、paper-repository関係やdesign lineageを監査する。

### DSCCに効く理由

T012でAI Scientistを最初から再実装する前に、**既存agent/harness/benchmarkのどれをcomponentとして接続できるか**を調べる入口になる。既知研究を先に使い、DSCC固有の研究継承・分散計算・provenanceへ実験を絞る方針に合う。

### 実装候補

- registryを「外部研究agent catalog」のsourceとして調べ、DSCC用に再配布せず、URL/revision/license/capabilityのIndexRecordを作る。
- 代表agentをFML-Bench/T012 handoff experimentへadapter接続する。

### 受入証拠

- 外部repoの版・license・実行条件を固定できる。
- agent比較が同一task/harnessで行われる。
- registryの「関連あり」を実装互換性や科学的優位の証拠にしない。

---

## 17. R15 — When Does Memory Help Multi-Trajectory Inference for Tool-Use LLM Agents?

一次資料: https://arxiv.org/abs/2605.28224  
公開日: 2026-05-27。

### 既知研究

cross-trajectory memoryをscopeとabstractionに分け、best-of-N、beam search、MCTSの3つのinference strategy × 4 tool-use benchmarkで評価する。同じmemoryでもsearch strategyによって効果が変わる。論文はreflectionがMCTSでのみ有意になった例、atomic fact extractionがaccuracy-neutralでも一部taskでtrajectoryを19–26%短縮した例を報告する。

### DSCCに効く理由

Experience Graph/Computational Memoryを「検索精度だけ」で評価すると不十分で、**memory representation × retrieval × search policy**の組として研究する必要がある。

### 実装候補

- T010 evaluation matrixに `memory_profile_id × search_strategy_id × task_class` を追加する。
- Reflection、fact、raw observation、graph pathを同一interfaceでagentへ供給するadapterを作る。
- success率だけでなくsteps、tool calls、duplicate exploration、negative transferを測る。

### 受入証拠

- 同じmemoryを複数search strategyで評価。
- task stateをforkできない環境では、MCTS/beamを無理にbaseline化しない。
- memoryが「短くしただけ」「accuracyを上げた」「探索多様性を上げた」を分ける。

---

## 18. R16 — CacheBridge

一次資料: https://arxiv.org/abs/2609.00891  
公開日: 2026-09-01。  
既存DSCC資料: [Experience/state evidence ledger S06](../proposals/experience-sharing/SOURCES_AND_EVIDENCE.ja.md#s06)。

### 既知研究

Full-Head Mappingに対し、architecture-indexed head対応、attention-sensitive calibration、bounded mapper constructionを導入する。論文はQwen3で高いtarget retention、mapper storage削減、application/construction高速化を報告する。

### DSCCに効く理由

「cross-model KVはpairごとに巨大なfull mappingが必要」という前提を弱め、converter registryを現実的にする候補。XKVとは用途が違い、CacheBridgeは同じshared prefixのtarget cacheを再構築する方向、XKVはreceiverの現在cacheとSharer情報を融合する方向として分ける。

### 実装候補

- 既存S06のprofile案に`head_mapping_method`、`calibration_objective`、`construction_cost`、`mapper_bytes`を追加するADR候補。
- Full-Head / CacheBridge / receiver re-prefillを同じKVShareArena系evaluationで比較する。

### 受入証拠

- mapper容量の削減と、送るKV cache量の削減を混同しない。
- Qwen/Ministralでの報告から、未評価familyを自動承認しない。
- GSM8K等の精密推論も含めたtask別評価を行う。

---

## 19. 横断的な実装候補

### Lane A — Research-agent evaluation pack（今すぐ設計可能）

対象: R01, R05, R13, R14, R15  
接続: T010/T012

成果物候補:

- external research-agent benchmark adapter
- process metric → Exploration Atlas mapping
- research-run audit checklist
- agent lineage / promotion proposal
- source-grounded external agent catalog

最初の受入:

1. 同一taskで2種類以上のagent/harnessを実行できる。
2. scoreだけでなくtrace、cost、selection、failureをDSCC Artifactへ戻す。
3. private/held-out評価をagent-visible contextへ漏らさない。
4. 実際の別modelがT012 ResearchStateだけから作業を継続する。

### Lane B — KV / latent transfer evaluation pack（設計・adapter work開始可能）

対象: R02, R03, R06, R16  
接続: LEC/T011/T009

成果物候補:

- cache/latent manifest + signed binding
- converter registry
- KVShareArena adapter
- cross-session substitution security tests
- exact-prefix / cross-context / checkpoint / fusion class分離

最初の受入:

1. model/cache/context/converter mismatchを注入前に拒否できる。
2. full re-prefill、text communication、no-cacheと同条件比較する。
3. latencyだけでなくtransfer bytes、VRAM、quality、negative transferを保存する。

### Lane C — Resilient distributed model execution（runtime依存）

対象: R04, R07, R08  
接続: T005/T006/T011

成果物候補:

- learner-island training prototype
- weakly consistent cache-location index
- agent-aware prefetch hints
- churn/straggler/failure injection harness

最初の受入:

1. local/trusted siteでfailure注入を再現。
2. stale routingはcorrectnessを壊さずfallbackする。
3. training updateのlineageとtoken contributionを保存。
4. WAN実測前にworld-scale性能を主張しない。

### Lane D — Remote worker trust and confidentiality（実機依存）

対象: R09, R10  
接続: T009/T011/G023-G030/G047/G052

成果物候補:

- verification adapter
- attestation artifact/profile
- confidential-compute capability
- fail-closed routing policy

最初の受入:

1. attestation/integrity failureを明示的に拒否。
2. computation correctnessとdata confidentialityを別々に評価。
3. TEEなしworkerへprivate jobを誤routeしない。

### Lane E — Layered interoperability and governance（設計可能）

対象: R11, R12  
接続: T002/T005/T012

成果物候補:

- protocol responsibility matrix
- project governance profile
- dissent/human-escalation/audit contract

最初の受入:

1. host/transportを交換してもDSCC Artifact/CIDの意味が変わらない。
2. contradiction/dissentが多数決で消えない。
3. owner authority、transport identity、scientific evidence、project governanceを別状態で保持する。

## 20. 実装順に関する提案

世界分散runtimeが完成するまで研究を止める必要はない。次の順序なら、現在のローカル基盤から検証を積み上げられる。

```text
(1) FML-Bench + research-run audit adapter
       ↓
(2) T012の実model handoff experiment
       ↓
(3) KVShareArena評価adapter + cache/latent manifest
       ↓
(4) Exploration Atlasのmemory × search評価
       ↓
(5) trusted local GPUでKV/latent converter実験
       ↓
(6) T005/T011でP2P cache routing / resilient execution
       ↓
(7) TEE/verificationを含むuntrusted worker実験
       ↓
(8) AIDE²型のagent self-improvement loop
```

(8)のself-improvementは最終目標に近いが、promotion評価・sandbox・権限分離・auditを先に通す。逆に、(1)〜(4)は分散GPU完成前でも進められる。

## 21. 後任エージェントへの手順

1. 対象R-IDの一次資料の最新版と公開実装を再確認する。
2. DSCCの関連Task/G/ES-IDを読む。
3. 既知研究で答えがある部分は再発明しない。
4. DSCC固有の未解決点だけをIssueの問いにする。
5. 実装前に、入力・出力・評価・失敗条件をAcceptanceとして書く。
6. mock/synthetic/local simulationと実model/GPU/WAN/敵対環境の証拠を分ける。
7. 実装結果はResearchState / EvaluationRun / FailureReportへ戻し、次のエージェントが続きを始められるようにする。

## 22. 一次資料一覧

- R01 AIDE²: https://arxiv.org/abs/2609.26457
- R02 KVShareArena: https://arxiv.org/abs/2609.10266
- R03 XKV: https://arxiv.org/abs/2608.20617
- R04 Decoupled DiLoCo: https://arxiv.org/abs/2604.21428
- R05 FML-Bench: https://arxiv.org/abs/2605.17373 / https://github.com/qrzou/FML-bench
- R06 When Latent Agents Lie: https://arxiv.org/abs/2606.28958
- R07 P2P inference: https://arxiv.org/abs/2606.17059
- R08 CacheScout: https://arxiv.org/abs/2608.14624
- R09 VeriAttn: https://arxiv.org/abs/2606.16352
- R10 OpenPCC: https://arxiv.org/abs/2606.11145 / https://github.com/openpcc/openpcc
- R11 Protocol taxonomy: https://arxiv.org/abs/2606.19135
- R12 Governance gaps: https://arxiv.org/abs/2606.31498
- R13 Verification-gap survey: https://arxiv.org/abs/2608.05179
- R14 AI-Research Agents in the Wild: https://arxiv.org/abs/2609.11975
- R15 Memory × multi-trajectory inference: https://arxiv.org/abs/2605.28224
- R16 CacheBridge: https://arxiv.org/abs/2609.00891

この資料をマージしただけでは、各方式をDSCCが実装・再現・採用したことにはならない。実装状態は各Task/Issue/validation reportで更新する。
