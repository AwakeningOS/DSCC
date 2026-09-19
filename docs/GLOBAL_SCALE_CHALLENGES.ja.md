# DSCC 世界規模化に向けた未解決課題レジストリ

状態: **Living backlog / 長期課題。個別項目が実証されるまで未解決として扱う。**

目的: DSCCを、既知参加者のローカル実装から、世界中の人間・AI・計算資源が参加できる科学認知ネットワークへ発展させる際の障害を失わないための一覧である。現在の実装Taskとは分離して保持し、将来の技術やAIエージェントが解決可能になった時点で、個別Issue・ADR・実装Taskへ昇格させる。

この文書は「既存技術を列挙したので解決済み」という意味ではない。候補技術を採用しただけでは完了としない。実装、攻撃的試験、複数環境での実測、失敗条件、残存リスクを記録して初めて状態を更新する。

## 状態の読み方

- **Engineering**: 主として既存技術の統合・実装・運用で解く課題。
- **Research**: 一般解が確立しておらず、DSCC自身の研究対象になり得る課題。
- **Mixed**: 既存技術で一部を解けるが、世界規模・敵対環境では研究課題が残る。
- **Policy / Legal**: 技術だけでは完結せず、制度・契約・運用が必要な課題。

優先度は現在の実装順を固定するものではない。依存関係と危険度を示す目安である。

---

## A. 世界規模の通信・保存・発見

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G001 | NAT / CGNAT / Firewall越しの接続 | libp2p、QUIC、hole punching、relay、接続失敗時のfallback | Engineering | P0 |
| G002 | 世界規模のpeer / CID発見 | Kademlia DHT、delegated routing、複数bootstrap、federated index | Engineering | P0 |
| G003 | 中央障害点を作らない | replaceable bootstrap / relay / index operators、複数trust domain | Mixed | P0 |
| G004 | Artifactの長期可用性 | replication、pin policy、repair、erasure coding、availability audit | Engineering | P0 |
| G005 | 巨大dataset / checkpoint転送 | chunking、Merkle DAG、resume、delta transfer、compression、cache、data locality | Engineering | P1 |
| G006 | node churn・回線断・sleep | lease、retry、checkpoint、idempotent job、再配置、部分障害復旧 | Engineering | P0 |

関連: T005、T007。

---

## B. Identity・権限・信頼境界

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G007 | 鍵と実世界主体の対応 | Ed25519 identityに加え、組織credential、PKI、SPIFFE/SVID等を選択可能にする | Mixed | P0 |
| G008 | node間のtrust federation | 複数trust root、組織横断credential、失効・更新 | Mixed | P1 |
| G009 | 読取・計算・公開・管理権限の分離 | capability token、mTLS、RBAC/ABAC、policy engine、least privilege | Engineering | P0 |
| G010 | AI要求とowner権限の強制分離 | authenticated local service、別資格情報、OS/process isolation、owner approval | Engineering | P0 |
| G011 | 鍵盗難・rotation・revocation | key lineage、revocation、transparency、secure key storage | Mixed | P0 |
| G012 | Sybil attack | trust roots、validated work、rate limit、resource cost、identity diversity。単純多数決を使わない | Research | P0 |
| G013 | colluding identitiesの独立性判定 | organization / operator / network / source lineage / hardware diversityの記録と選択 | Research | P0 |
| G014 | identity/reputationを科学的真偽と混同しない | reputationはadmission/routingの一信号に限定し、Evidence/Verificationを別系統にする | Mixed | P0 |

関連: T001、T009。

---

## C. 未信頼コードの実行とホスト防御

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G015 | 第三者コードの安全実行 | WASI/Wasmtime、OCI + gVisor、microVM、seccomp/cgroups、default-deny network | Engineering | P0 |
| G016 | filesystem / secret exfiltration | capability-scoped mounts、secret isolation、read-only inputs、egress deny | Engineering | P0 |
| G017 | CPU/RAM/disk/output DoS | hard quotas、fuel/time limit、output cap、kill/cancel、backpressure | Engineering | P0 |
| G018 | GPU workerの隔離 | dedicated device/time slice、対応機器のhardware partition、driver attack-surface管理 | Mixed | P0 |
| G019 | 実行物のすり替え | executable digest、OCI digest、Sigstore/Cosign、in-toto、TUF等の供給網証明 | Engineering | P0 |
| G020 | tool digestが実行環境を十分に表さない | source/dependency/runtime/driver/profileまでversioned manifest化 | Engineering | P0 |
| G021 | 悪意あるjob class | owner policy、allowlist/denylistではなく機械可読capability、network/data範囲の宣言 | Mixed | P0 |
| G022 | runtime脆弱性自体 | patch policy、runtime matrix、host kernel/driver更新、破壊的試験 | Mixed | P1 |

関連: T003、T006、T009。

---

## D. 計算結果・科学結果の検証

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G023 | workerが適当な答えを返す | replica execution、spot check、invariant、signed receipt、adaptive verification | Research | P0 |
| G024 | 検証コストが本計算と同程度になる | risk-based replication、random audit、cheap verifier、proof system | Research | P0 |
| G025 | exact reproducibility不能な数値計算 | tolerance、invariant、environment capture、hardware/runtime metadata | Mixed | P0 |
| G026 | 確率的計算・学習結果の検証 | seed、複数run、分布、信頼区間、checkpoint、statistical verification | Research | P0 |
| G027 | worker結託 | diversity-aware verifier selection、独立運営者、ランダム監査 | Research | P0 |
| G028 | 実行証明 | 必要なjob classではzkVM / verifiable computation / remote attestationを選択可能にする | Research | P1 |
| G029 | 実行が正しくても科学モデルが間違う | Claim / Evidence / contradiction / replication / reviewを実行証明と分離 | Research | P0 |
| G030 | 「署名済み」を「正しい」と誤認 | UI/API/検索でintegrity、identity、scientific verificationを別状態として保持 | Engineering | P0 |

関連: T008、T009。現行seedのverifyはintegrity検証であり、この層の完成ではない。

---

## E. 異種計算資源と世界分散スケジューリング

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G031 | CPU/GPU/VRAM/OS/driverの異種性 | capability advertisement、constraint scheduler、runtime compatibility matrix | Engineering | P1 |
| G032 | WAN帯域とdata locality | data-aware scheduling、cache locality、transfer cost込みのjob placement | Engineering | P1 |
| G033 | 離れたGPUを巨大VRAMとして扱えない | independent job parallelism、pipeline分割、通信量を抑えた学習方式 | Mixed | P0 |
| G034 | 世界規模の共同training | Local SGD、federated/distributed optimization、DiLoCo系、gradient/update compression | Research | P1 |
| G035 | participant離脱時の長時間job回復 | checkpoint、lease、rescheduling、partial result reuse | Engineering | P1 |
| G036 | 電力・温度・利用時間のowner制約 | telemetry、hard/soft policy、停止、budget accounting | Engineering | P1 |

関連: T003、T006。

---

## F. 世界規模の記憶・検索・知識汚染

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G037 | 数十億Artifactの検索 | shard、federated search、local-first index、ANN + exact fallback、hierarchical routing | Mixed | P1 |
| G038 | embedding座標系の非互換 | versioned embedding_profile_id、side-by-side index、reindex、rank fusion | Engineering | P0 |
| G039 | 検索順位を真実と誤認 | provenance-aware retrieval、evidence-aware reranking、rank/truth separation | Research | P0 |
| G040 | Sybilによる検索汚染 | source-lineage grouping、per-origin caps、diversity ranking、local recomputation | Research | P0 |
| G041 | AI生成物の自己引用・複製を独立証拠と数える | original-source recovery、lineage dedup、independent-run identity | Research | P0 |
| G042 | 自然文からEpisodeを誤抽出 | source span/pointer、extractor revision、alternate extractions、unknown保持 | Research | P1 |
| G043 | Exploration Atlasの誤類推 | semantic + structural independent retrieval、explicit mapping、gaps、BridgeとTransferAssessment分離 | Research | P1 |
| G044 | LEC / hidden-state共有のモデル間非互換 | model/cache/distiller/adapter profile、same-model検証後のcross-model adapter | Research | P2 |
| G045 | LECのprivacy / poisoning / negative transfer | provenance、permission、isolated evaluation、negative-transfer tests、採用policy | Research | P1 |
| G046 | 記憶の無制限肥大化 | dedup、retention、usefulness/usage signal、source preservation、derived-index rebuild | Mixed | P1 |

関連: T007、T010、Computational Memory、Exploration Atlas、Latent Experience Capsule。

---

## G. Privacy・法務・経済・運用

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G047 | 非公開データを他人のworkerで処理 | confidential VM / TEE、remote attestation、encryption、regional policy。保証範囲を明示 | Mixed | P1 |
| G048 | 個人情報・ライセンス・国境・削除要求・報酬設計・運用を世界規模で整合させる | private-by-default、classification、geo policy、SPDX/license policy、revocation/crypto-erasure、signed contribution receipts、fraud controls、protocol migration、observability | Policy / Legal + Mixed | P0 |

G048は一項目にまとめて終了させるものではない。実装段階では、少なくともprivacy、cross-border data、license、contribution accounting、protocol upgrade、incident responseへ分割して独立Issue化する。

---

## H. Distributed Open Model Commons固有の課題

長期構想は [Distributed Open Model Commons](proposals/DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md) を参照する。G031-G036の異種計算・WAN trainingを前提に、公共推論・ボランティアpre-training・共同モデル開発として特に残る問題を以下へ追加する。

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G049 | 巨大model/checkpointをcontent-addressedに分割・再構成する | large-object manifest、weight sharding、partial fetch、replication、repair、license metadata | Engineering | P1 |
| G050 | 分散推論でmodel shardやreplicaがjoin/leaveしてもserviceを継続する | topology-aware routing、replication、rebalancing、session affinity、failure recovery | Mixed | P1 |
| G051 | WAN上のtoken-by-token通信latency | regional inference islands、replicas、pipeline/expert placement、latency-aware execution plans | Research | P1 |
| G052 | public inferenceでprompt / KV / hidden stateがvolunteer operatorへ漏れる | privacy class、trusted execution、confidential compute、routing policy、必要に応じた暗号技術 | Research | P0 |
| G053 | heterogeneous consumer GPUでtraining roleを割り当てる | memory-aware sharding、asymmetric parallelism、capability benchmarks、dynamic island formation | Research | P1 |
| G054 | churn・非同期・stale update下でpre-trainingを安定収束させる | low-communication optimization、elastic membership、staleness control、checkpoint recovery | Research | P0 |
| G055 | 未信頼training workerのupdateが正しいか・有害でないか検証する | selective replay、sanity checks、held-out evaluation、redundant training、update verification、poisoning/backdoor tests | Research | P0 |
| G056 | hardware/vendor/precision差による数値挙動と収束差 | versioned runtime profiles、mixed-precision policy、cross-vendor validation、numerical drift measurement | Mixed | P1 |
| G057 | training dataset mixを世界分散でも再現可能・合法に保つ | dataset manifests、source lineage、license/consent policy、shard identity、removal/retraction handling | Mixed | P0 |
| G058 | checkpoint fork / promotion / rollbackを中央の単一headなしで扱う | immutable model lineage、signed mutable release labels、fork-aware governance、rollback rules | Mixed | P1 |
| G059 | 計算量の申告と「有用な貢献」を混同しない | signed execution receipts、measured resource use、verification result、model-quality contributionを別記録にする | Research | P1 |
| G060 | 公共モデル利用の公平性と混雑制御 | local/community policy、quotas、queueing、priority classes、複数gateway。科学的信頼やidentity scoreとは分離 | Policy / Legal + Engineering | P2 |
| G061 | model/data/code供給網への悪意ある差し替え | signed model manifests、tool/runtime digest、checkpoint verification、TUF/Sigstore/in-toto等 | Engineering | P0 |
| G062 | community modelのrelease判断を自動score一つへ還元しない | reproducible evaluations、multiple branches、documented promotion policy、人間/組織/agent governanceの分離 | Mixed | P1 |

既存のDiLoCo、OpenDiLoCo、INTELLECT、Petals等が示した成果はこれらの一部に解決候補を与えるが、家庭の異種GPUが自由参加するDSCCネットワーク全体の実証とは扱わない。

---

## I. Distributed AI Research Laboratory固有の課題

最終目標は [Distributed AI Research Laboratory](proposals/DISTRIBUTED_AI_RESEARCH_LAB.ja.md) を参照する。Open Model Commonsの計算・model層に加えて、異なるAIと人間が長期研究を継承するための課題を管理する。

| ID | 問題 | 必要になる能力・候補技術 | 種別 | 優先 |
|---|---|---|---|---|
| G063 | closed AI / open AI / human間で研究状態を共通表現する | versioned ResearchQuestion / LiteratureReview / Hypothesis / ExperimentPlan / Evaluation / ResearchState profiles | Engineering | P0 |
| G064 | closed modelがprovider側で更新され完全再現できない | provider/model/snapshot metadata、input/output CIDs、tool/config capture、再現性class | Mixed | P0 |
| G065 | agent交代時に会話contextなしで研究を継続する | artifact-only handoff、explicit unresolved questions、dependency graph、project state | Engineering | P0 |
| G066 | 既知研究を再発明して無駄な実験を行う | primary-literature retrieval、citation graph、known-result registry、novelty/overlap check | Research | P0 |
| G067 | 論文の主張とDSCC内の実測結果を混同する | source type、Claim/Evidence関係、measured-vs-reported provenance、date/model scope | Engineering | P0 |
| G068 | 複数agentが同じ研究を重複実行する | experiment fingerprint、semantic/structural duplicate detection、shared work queue | Mixed | P1 |
| G069 | 異なるagentの結論が衝突する | competing hypotheses、evidence graph、replication requests、unresolved conflict state | Research | P0 |
| G070 | 長期projectのresearch stateが肥大化・分岐する | immutable project snapshots、branching、checkpointed research state、summaries linked to originals | Mixed | P1 |
| G071 | benchmarkだけを最適化して実能力を誤る | rotating/held-out evaluation、cross-benchmark transfer、adversarial evaluation、metric provenance | Research | P0 |
| G072 | research agent自身の能力を測れない | literature efficiency、novel-gap identification、experiment validity、failure recovery、cross-agent handoff benchmarks | Research | P1 |
| G073 | 研究budgetをどの問い・branchへ配るか | expected-information-gain、portfolio scheduling、uncertainty/impact/cost models、human/agent priorities | Research | P1 |
| G074 | 新しいmodel/agentが過去研究を正しく再利用できない | compatibility profiles、retrieval evaluation、transfer tests、source-linked summaries、LEC adapters where justified | Research | P1 |
| G075 | 自律研究loopが同じ局所探索を繰り返す | exploration diversity、branching strategies、negative-result memory、novelty search、periodic problem reframing | Research | P1 |
| G076 | 世界規模で複数研究projectを同時進行する | project namespace、dependency scheduling、federated research index、cross-project artifact reuse | Mixed | P1 |

これらはAI研究の品質・効率・継続性に関する問題であり、単純なP2P接続やGPU数だけでは解決しない。

---

## 完成条件を誤らないための共通原則

世界規模版では、次を別々の事実として保持する。

```text
signature valid
    ≠ identity independently verified
    ≠ computation independently verified
    ≠ scientific claim supported
    ≠ safe to execute
    ≠ safe to disclose
    ≠ legally distributable
```

同様に、

```text
semantic similarity ≠ truth
structural similarity ≠ successful analogy
Bridge ≠ tested transfer
many records ≠ many independent confirmations
execution proof ≠ scientific correctness
many GPUs ≠ one large shared VRAM
```

この分離をprotocol、UI、search、verification、receiptsに一貫して反映する。

## 将来のAIエージェントへの運用ルール

1. この一覧の問題が既知研究・既存標準で実質的に解かれていないか、まず一次資料を調査する。
2. 解決候補が見つかったら、いきなり「SOLVED」にせず、DSCCへ適用した場合の前提・脅威モデル・失敗条件を記録する。
3. 実装可能なものは既存Taskとの依存関係を確認し、専用Issue / branch / acceptance testを作る。
4. 世界規模に必要な本命設計を先に作る。比較やablationの都合で本命の自由度を削らない。
5. 合格判定は実測に基づく。mock、synthetic fixture、同一PC、同一operatorだけの試験を世界規模実証へ外挿しない。
6. 問題が解決した場合も削除せず、`Resolved by`、対象version、証拠、残存制約を追記して履歴を残す。
7. 新しい障害が発見されたらG-IDを追加し、既存番号を再利用しない。

## 現在の最短クリティカルパス

現行M0から世界公開に向けた土台として、少なくとも次の順序が重要である。

```text
T001 owner / agent authority separation
  ↓
T003 enforceable sandbox
  ↓
T005 authenticated peer transport
  ↓
T007 source/catalog/research-object separation
  ↓
verification layer (G023-G030)
  ↓
GPU / heterogeneous workers
  ↓
T011 Open Model Commons execution
  ↓
federated identity + adversarial search / Sybil defenses
  ↓
world-scale federation
  ↓
T012 cross-model research handoff
  ↓
multi-agent / long-running research orchestration
  ↓
Distributed AI Research Laboratory
```

Computational Memory、Exploration Atlas、LECはこの基盤と並行して研究できるが、安全な世界規模実行・共有が完成したという意味にはしない。

## この文書の役割

これは固定ロードマップではなく、**「技術が進歩したときに拾える未解決問題の保存場所」**である。

将来、AIエージェントが現在難しい問題を解けるようになった場合、この一覧から一件ずつIssue化し、一次資料、設計、実装、攻撃的検証、実測結果を残してDSCCへ統合する。
