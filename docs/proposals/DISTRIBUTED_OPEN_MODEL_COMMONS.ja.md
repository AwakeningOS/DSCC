# みんなで使い、みんなで育てるオープンLLM計算コモンズ

## DSCC Distributed Open Model Commons — 公共推論・ボランティア計算・世界分散プレ学習の長期構想

状態: **長期model/compute層の設計提案。DSCC全体の最終目標は Distributed AI Research Laboratory。現行DSCCには分散推論・分散学習・GPU workerは未実装。**  
作成日: 2026-09-20  
DSCC構想・問題提起: Yusuke Maeda  
関連: [Architecture](../ARCHITECTURE.ja.md)、[Roadmap](../ROADMAP.md)、[世界規模化の未解決課題](../GLOBAL_SCALE_CHALLENGES.ja.md)、[Computational Memory](COMPUTATIONAL_MEMORY.ja.md)、[Exploration Atlas](EXPLORATION_ATLAS.ja.md)、[Latent Experience Capsule](LATENT_EXPERIENCE.ja.md)

## 1. 目標

DSCCのmodel/compute層として、**オープンなLLMを、世界中の参加者が少しずつ提供する計算資源で共同利用・共同開発できる公共計算基盤**を置く。この層の上に、closed AI・open AI・人間がAI研究そのものを共同で進める [Distributed AI Research Laboratory](DISTRIBUTED_AI_RESEARCH_LAB.ja.md) を構成する。

対象は企業の非公開モデルを複製することではない。モデル、データ、コード、ライセンスが共有可能な範囲で、公開されたモデルとDSCC上で共同開発したモデルを扱う。

最終的には、次の三つを同じ基盤の上で成立させる。

1. **Public Inference Commons** — 高価なGPUを持たない利用者も、分散した参加ノードを通じてオープンLLMを利用できる。
2. **Volunteer Training Commons** — GPU、CPU、ストレージ、帯域を参加者が明示的に提供し、fine-tuning、評価、探索、最終的にはpre-trainingへ利用できる。
3. **Open Model Research Commons** — モデルの重みだけでなく、試した設計、失敗、評価、設定、checkpoint、データ構成、再現結果を研究資産として共有し、人間とAIエージェントが共同で次のモデルを育てる。

ここでいう「公共」は、各参加者の資源を無断で使用することを意味しない。**各node ownerは常に参加、停止、資源上限、job class、公開範囲を制御できる。** 一台のnodeが離脱しても全体が継続できる構造を目指すが、個々のownerの停止権を回避する仕組みは目標にしない。

## 2. なぜDSCCで行うのか

単にdistributed trainerを作るだけなら、モデル開発の経験はcheckpointの外へ失われやすい。

DSCCでは、モデル開発そのものを既存の研究資産基盤へ載せる。

```text
Open model checkpoint
        │
        ├── training configuration
        ├── source/data lineage
        ├── code/tool digest
        ├── hardware/runtime profile
        ├── evaluation
        ├── failed experiments
        ├── open questions
        └── derived checkpoints
                │
                ▼
        Computational Memory
                │
        Exploration Atlas
                │
     Human / AI research agents
                │
                ▼
          next experiments
                │
                ▼
        next model generation
```

目標は「世界中のGPUを一つの巨大GPUに見せる」ことではない。通信特性に応じて、

- 推論を分担する。
- 独立した実験を大量並列化する。
- 評価やデータ処理を分散する。
- 低通信量の学習法でpre-trainingを協調する。
- モデル開発の探索履歴を共有し、同じ失敗を繰り返さない。

という複数の計算classを使い分ける。

## 3. 参加者はGPUを持っていなくてもよい

DSCC Open Model Commonsでは参加方法を一種類に固定しない。

### GPU participant

- inference worker
- training worker
- evaluation worker
- simulation / model-search worker
- checkpoint変換や量子化

### CPU / storage participant

- tokenizer / preprocessing
- dataset validation
- Artifact / checkpoint shard replication
- search index
- P2P relay
- deterministic verification
- build / conversion jobs

### Research participant

- architecture proposal
- dataset / filtering proposal
- evaluation design
- reproduction
- error analysis
- Exploration Atlasへの試行履歴提供

### User

計算資源を提供しなくても、許可されたpublic modelを利用できる構成を目標にする。将来のresource policyや混雑制御は、利用権と科学的信頼を混同せず別に扱う。

## 4. 完成形の概念構成

```text
                  Users / Researchers / Agents
                           │
                           ▼
                  DSCC Model Gateway
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
       Inference Swarm              Training Swarm
             │                           │
      model replicas /              local training
      pipeline / experts            + rare synchronization
             │                           │
             └─────────────┬─────────────┘
                           ▼
                    Model Artifacts
                           │
           checkpoint / config / lineage
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
     Computational Memory        Exploration Atlas
             │                           │
             └─────────────┬─────────────┘
                           ▼
                    Research Agents
                           │
                     new experiments
                           │
                           └──────────────↺
```

通信、実行、検証、検索、研究記憶は分離する。推論routingの順位を科学的真偽に使わず、training contributionの量を研究結果の正しさに使わない。

## 5. Model Artifact

モデルを単一の巨大ファイル名として扱わず、再構成可能なversioned Artifact群として扱う。

概念上は次を持つ。

```text
ModelArtifact
├─ architecture / model config
├─ tokenizer profile
├─ weight manifest
├─ weight shards / checkpoint CIDs
├─ precision / quantization profile
├─ runtime compatibility
├─ parent model/checkpoint CIDs
├─ training run CIDs
├─ dataset / mixture provenance
├─ evaluation CIDs
├─ license / redistribution constraints
└─ signatures / release status
```

重み全体をseed JSON recordへ直接格納しない。現行1 MiB recordを変更して巨大weightを押し込むのではなく、大容量block/storage adapterとmanifestを別途設計する。

Model ArtifactのCIDや署名は完全性と来歴を示すが、モデルが安全、有用、科学的に優れていることを保証しない。

## 6. Public Inference Commons

### 6.1 基本形

利用者はモデル全体を自分のGPUへ置く必要がない。

候補は複数ある。

- 完全model replicaを持つworkerへrequest routingする。
- Transformer layerを複数nodeへ分ける。
- model expertsを異なるnodeへ配置する。
- 地域内の高速node群を一つのinference islandとして使う。
- CPU / GPU / RAM offloadを組み合わせる。
- 同一modelの複数replicaへload balanceする。

世界WANでは各tokenごとに大陸間通信する構成はlatencyに弱い。したがって一つの方式へ固定せず、model size、network、hardware、latency requirementに応じてexecution planを選ぶ。

### 6.2 既知の入口

Petalsは、複数参加者が大規模言語モデルの層を分担し、consumer GPUを含む環境で大規模モデルのcollaborative inference / fine-tuningを行う方式を実証している。BLOOM-176Bで約1 step/secの推論を報告している。

これは「世界規模DSCC inferenceが完成済み」という証拠ではない。DSCCではさらにowner policy、untrusted worker verification、prompt privacy、モデルshardの可用性、複数runtime、公共accessを扱う必要がある。

## 7. Volunteer Training Commons

### 7.1 通常の同期学習をそのままWANへ持ち込まない

通常のdata parallel trainingでは、ほぼ毎step、大量のgradient / parameter communicationが発生する。家庭回線や大陸間WANではこれが支配的なbottleneckになる。

そこで、世界分散pre-trainingでは**local computationを増やし、global communicationの頻度を下げる**方式を中心候補とする。

```text
Worker / island A
  local optimizer
  N local steps
        │
Worker / island B
  local optimizer
  N local steps
        ├── occasional global update
Worker / island C
  local optimizer
  N local steps
        │
        ▼
   next outer round
```

DiLoCo、OpenDiLoCo、PRIME系はこの方向の重要な先行例である。

### 7.2 「一枚の家庭GPU」と「GPU island」を区別する

世界分散学習の実証があることと、RTX 3060からH100まで一枚単位で自由参加するネットワークが完成していることは別である。

初期の本命設計では、

```text
local island
  ├─ 1 GPU
  ├─ several GPUs
  ├─ university server
  └─ cloud cluster
        │
        ▼
low-frequency global synchronization
```

のように、**local island内部とworld-wide同期を分ける**。

一枚のconsumer GPUでも、model / optimizer stateが収まるtask class、sharded local execution、evaluation、independent experimentsなどで参加できるようにする。モデル全体を一枚に載せられない場合は、無理に同じtraining roleへ押し込まない。

## 8. 現段階で実際に確認されていること

以下は、2026-09-20時点で公開一次資料から確認できる代表例である。各研究の条件は異なり、DSCC全体の実証として流用しない。

| 系統 | 公開結果 | DSCCにとって意味すること |
|---|---|---|
| DeDLOC (2021) | heterogeneous / unreliableなopen collaborationを対象にし、実際のvolunteerを含む40参加者でlanguage-model pretrainingを報告 | 一般参加型の協調学習はLLM以前から実証例がある |
| Petals (2022) | 大規模モデルのcollaborative inference / fine-tuning。BLOOM-176Bをconsumer GPU群で約1 step/secと報告 | モデルを複数参加nodeへ分割して利用する入口がある |
| DiLoCo (2023) | 8 workersでfully synchronous trainingと同等の性能を報告し、communicationを500倍削減。resource availability変動へのrobustnessも報告 | WAN trainingではlocal steps + rare synchronizationが有力 |
| OpenDiLoCo (2024) | 2大陸・3か国でtrainingし、90–95% compute utilizationを報告。billion-parameter規模まで拡張 | geographic distributionでの再現可能なopen implementationがある |
| INTELLECT-1 (2024) | 10B modelを1 trillion tokens学習。最大14 concurrent nodes、3大陸、30 independent compute providers、83–96% compute utilization。従来data parallel比で400倍のbandwidth reductionを報告 | 10B級のglobal collaborative pretrainingは既に実証段階 |
| INTELLECT-2 (2025) | 32B reasoning modelのglobally distributed asynchronous RL。dynamic heterogeneous permissionless contributorsと、untrusted inference worker検証を扱う | permissionless / heterogeneous workerを含む学習・検証へ進み始めている |
| DiLoCoX (2025) | 107B modelのpre-trainingを1 Gbps networkで実証し、vanilla AllReduce比357倍のspeedupを報告 | 100B超でも低帯域cluster間学習が可能な方向を示す |
| VeriLLM (2025 preprint) | decentralized inferenceで約1%のverification overheadを報告する検証方式を提案 | untrusted inference verificationにも専用研究が進んでいる |
| HetCCL (2026 preprint) | NVIDIA / AMD混在GPUのcollective communicationをRDMA clusterで統合 | accelerator heterogeneityは改善中。ただし家庭WANの解決ではない |

したがって、現在の問いは「分散LLM学習は可能か」ではない。

**DSCCが解くべき問いは、既に成立しているcluster / global-island型の分散学習を、一般参加者の不均一・不安定・部分的に未信頼な計算資源まで広げ、研究履歴と検証を含む公共基盤として成立させられるか**である。

## 9. 現段階でまだ実証できていないもの

DSCCは次を実証済みと扱わない。

- 家庭のconsumer GPUが自由にjoin / leaveする世界ネットワークで、10B以上のLLMを安定してpre-trainできること。
- NVIDIA、AMD、Apple Silicon、CPUなどを一つのtraining swarmへ効率よく混在させられること。
- 一枚ごとの遅いGPUを多数足せば、data-center GPU clusterと同じ効率になること。
- permissionlessなworkerのgradient / model updateが正しいことを低コストで完全検証できること。
- 悪意あるtraining contributorによるpoisoning / backdoor / targeted updateを一般的に防げること。
- 分散推論でpromptやhidden stateをvolunteer operatorから完全に秘匿できること。
- 世界中へ複製したcheckpoint / datasetのlicense、削除、privacy要求を自動的に解決できること。
- contribution accountingや報酬を導入すればSybilや無意味な計算水増しが自然に解決すること。
- すべてのmodel architectureを一つのparallelization方式で扱えること。

## 10. DSCCで追加すべき主要機能

### A. Model distribution

- large-object content-addressed storage
- checkpoint sharding
- partial fetch
- replication / repair
- model manifest
- license-aware distribution
- model lineage

### B. Compute capability advertisement

各workerは自己申告だけでなく、測定可能な範囲で次をadvertiseする。

- accelerator vendor / model
- usable memory
- supported precision
- driver/runtime
- measured local bandwidth
- approximate network capability
- owner time window
- power/thermal policy
- accepted job classes
- privacy / data restrictions

schedulerは「GPU枚数」だけで仕事を割り振らない。

### C. Inference scheduler

- compatible model shard discovery
- latency-aware routing
- topology-aware placement
- replication
- failover
- session affinity / KV handling
- verification class
- privacy class

### D. Training scheduler

- local island formation
- model / optimizer partition compatibility
- data shard placement
- local-step budget
- global synchronization rounds
- stale / dropped worker handling
- live checkpoint
- partial-result recovery
- contribution measurement

### E. Verification

推論と学習を別々に扱う。

Inference:
- duplicate / spot inference
- verifier assignment
- deterministic kernels where possible
- proof / attestation adapters where useful

Training:
- signed training observations
- replayable micro-tests
- gradient / update sanity checks
- held-out evaluation
- independent reproduction
- poisoning / backdoor probes
- checkpoint lineage
- selective redundant computation

「training workerがGPU時間を使った」ことと「有用で正しいupdateを作った」ことを分ける。

## 11. 共同モデル開発の形

DSCCでは単一training runだけを共同作業にしない。

```text
                  Base Model vN
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
 architecture A     data mix B       optimizer C
       │               │                │
 TrainingRun       TrainingRun       TrainingRun
       │               │                │
 Evaluation        Evaluation        Evaluation
       │               │                │
       └───────────────┼────────────────┘
                       ▼
              Exploration Atlas
                       │
            promising / failed paths
                       │
                       ▼
                  Model vN+1
```

各experimentは独立Artifactとして保存する。

推奨する最低限の記録:

- parent checkpoint
- exact architecture/config
- tokenizer
- dataset source/mix
- training code/tool digest
- optimizer/hyperparameters
- random seed where applicable
- hardware/runtime
- token count / compute / wall-clock
- checkpoint CIDs
- evaluation
- failures / interruption
- investigator/agent notes
- independent reproduction status

最終scoreだけを残さない。

## 12. AIエージェントの役割

将来のresearch agentは、ownerが許可したbudget内で次を行える。

1. 過去のTrainingRun、失敗、評価を検索する。
2. 未探索の設計を提案する。
3. Exploration Atlasで別experimentの探索構造を比較する。
4. 利用可能なcompute capabilityからjob graphを作る。
5. owner / project policyの承認を得たjobだけ提出する。
6. 結果を記録し、再評価・再現候補を作る。
7. 有望checkpointを候補として提示する。

AIが自分で「公式model version」を宣言する権限を自動取得しない。研究結果とrelease / governance判断を分離する。

## 13. 一つのglobal model headを強制しない

オープン開発ではforkを失敗扱いにしない。

```text
Model v1
├─ research branch A
├─ multilingual branch B
├─ small-efficient branch C
└─ experimental architecture D
```

checkpoint lineageをGitのcommit graphに近い形で保持し、複数branchを許す。

「公式」「推奨」「stable」などのmutable labelは、immutable checkpoint本体と分離する。どのbranchを利用するかはproject / community / node policyによって異なってよい。

## 14. クリアすべき主要課題

詳細な長期レジストリは [GLOBAL_SCALE_CHALLENGES.ja.md](../GLOBAL_SCALE_CHALLENGES.ja.md) に置く。本構想で特に重要なのは次である。

### Distributed inference

- 高latency WANでtoken-by-token pipelineをどう避けるか。
- model shardが消えた場合の高速rebalancing。
- popular layer / expertへのhotspot。
- prompt / KV / hidden-state privacy。
- untrusted workerが正しい推論を返したかの安価な検証。
- public利用時のrate controlとavailability。

### Volunteer pre-training

- heterogeneous GPUでstragglerを全体停止させない。
- VRAM差に応じて役割を変える。
- node join / leaveでoptimizer convergenceを壊さない。
- 非同期 / stale updateを安定化する。
- 低速家庭回線でglobal synchronizationを成立させる。
- 数値差・precision差・vendor差を扱う。
- malicious gradient / update / poisoned dataを検出する。
- checkpointを壊さず継続・fork・rollbackできる。
- data mixtureを再現可能にする。
- training contributionの有用性を測る。

### Open-model governance

- model / data license。
- release candidateと研究branchの分離。
- checkpoint署名とsupply chain。
- dataset removal / privacy request。
- contribution receiptとSybil耐性。
- compute提供者がいつでも退出できること。
- 一つの企業・indexer・scheduler・gatewayを必須にしないこと。

## 15. 段階的な実証目標

日付ではなく、実証条件で進める。

### OMC-0 — Artifact contract

ModelArtifact、checkpoint manifest、runtime profile、TrainingRun、evaluationのdraft contractを作る。巨大weight本体はexternal block adapterへ置く。

合格:
- 同じcheckpoint manifestから同じidentityを再構成できる。
- 親checkpoint、training run、license、evaluationへ辿れる。
- 既存DSCC CIDを壊さない。

### OMC-1 — trusted two-machine inference

明示的に信頼した2台で、小型open modelのinferenceを分担する。

合格:
- 片方の停止を検出する。
- model/runtime incompatibilityを拒否する。
- 単一GPU実行との出力・性能差を記録する。

### OMC-2 — heterogeneous inference pool

複数世代 / 複数容量の実GPUでrouting / partitionを行う。

合格:
- schedulerがGPU枚数ではなく測定能力を使う。
- churn時のrecoveryを測る。
- latency / throughput / network bytesを記録する。

### OMC-3 — trusted volunteer training

まず小型modelで、複数拠点の明示的に信頼した参加者がlow-communication trainingを行う。

合格:
- centralized baselineと同じdataset / token budgetだけを公平性の唯一条件にせず、quality、compute、network、wall-clockを比較する。
- worker離脱 / 復帰を含む。
- checkpoint lineageを完全に残す。

### OMC-4 — public small-model pre-training

100M–1B級など、実際に全runを追跡・再実行可能な規模からpublic volunteer experimentを行う。

合格:
- independent participants。
- heterogeneous devices。
- cross-NAT。
- malicious / malformed contribution tests。
- raw cost / utilization / communication / failure logs公開。
- model、data、code、evaluationを再利用可能にする。

### OMC-5 — adversarial training network

未信頼workerを含め、verification、poisoning resistance、Sybil controlsを導入する。

合格:
- predefined malicious workersを実際に投入し、検出率・false positive・追加costを測る。
- 一つのoperatorの多数identityを独立検証数に数えない。
- failure caseを公開する。

### OMC-6 — community-scale open model

小型実証で成立した方式を、1B–10B以上のcommunity modelへ段階的に拡張する。

parameter countを成功条件にしない。中央clusterに対するquality / total compute / network / wall-clock / resilienceと、研究再利用性を測る。

## 16. DSCCの独自価値

分散推論も分散学習もDSCCが最初に発明するものではない。

DSCCが狙う独自の統合点は、

```text
volunteer compute
      +
open model distribution
      +
verifiable provenance
      +
reproducible TrainingRun
      +
shared scientific memory
      +
cross-model / cross-agent handoff
      +
exploration history
      +
owner-controlled permission
```

である。

単に「余ったGPUを集める」のではなく、**世界中の人とAIが、計算資源だけでなくモデル開発で得た経験も共有する研究所をネットワークとして作る**。

## 17. 先行研究・実装

以下は構想の新規性を主張するためではなく、2026-09-20時点で「どこまで既に可能か」を区別するための入口である。

- Diskin et al., **Distributed Deep Learning In Open Collaborations / DeDLOC** (NeurIPS 2021). heterogeneous volunteer collaborationと40参加者による協調pretraining。  
  https://arxiv.org/abs/2106.10207
- Borzunov et al., **Petals: Collaborative Inference and Fine-tuning of Large Models** (2022/2023). consumer GPUを含む分散inference / fine-tuning。  
  https://arxiv.org/abs/2209.01188
- Douillard et al., **DiLoCo: Distributed Low-Communication Training of Language Models** (2023). local stepsを増やしてglobal communicationを削減。  
  https://arxiv.org/abs/2311.08105
- Jaghouar et al., **OpenDiLoCo: An Open-Source Framework for Globally Distributed Low-Communication Training** (2024). 複数国・複数大陸でのopen implementation。  
  https://arxiv.org/abs/2407.07852
- Jaghouar et al., **INTELLECT-1 Technical Report** (2024). 10B、1T tokens、世界分散pre-training。  
  https://arxiv.org/abs/2412.01152
- Prime Intellect Team et al., **INTELLECT-2** (2025). 32B reasoning modelのglobally distributed asynchronous RLとpermissionless contributor検証。  
  https://arxiv.org/abs/2505.07291
- Qi et al., **DiLoCoX** (2025). 107B modelを1 Gbps network上でpre-trainしたと報告。  
  https://arxiv.org/abs/2506.21263
- Tang et al., **FusionAI** (2023). massive consumer-level GPUを対象にしたdecentralized LLM training / serving構想。完全なpublic volunteer pretraining実証とは区別する。  
  https://arxiv.org/abs/2309.01172
- Wang et al., **VeriLLM** (2025 preprint). permissionless decentralized inferenceのlightweight verificationを提案。  
  https://arxiv.org/abs/2509.24257
- Kim et al., **HetCCL** (2026 preprint). NVIDIA / AMD heterogeneous GPU collective communication。RDMA cluster条件であり家庭WAN実証ではない。  
  https://arxiv.org/abs/2601.22585

## 18. 今回の到達点

この文書で追加するのは実装ではなく、DSCCの長期的な目標を明文化したことである。

**Open Model Commonsは、DSCCをオープンLLMの共同利用・共同学習基盤へ拡張し、最終的なDistributed AI Research Laboratoryへmodel、checkpoint、training、inference、volunteer computeを提供する。**

現在のM0、P2P、sandbox、GPU、verificationの未実装状態は変わらない。各段階は、既存研究を再利用しつつ、実機・実ネットワーク・敵対条件で確認できたものだけを実装済みとする。
