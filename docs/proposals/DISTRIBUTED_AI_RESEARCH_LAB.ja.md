# DSCC Distributed AI Research Laboratory

## 世界中のAIと人間が、AIそのものを共同研究・共同進化させる分散研究所

状態: **DSCCの最終目標 / 長期設計。現行実装はこの構想の基盤段階。**  
作成日: 2026-09-20  
構想: Yusuke Maeda

関連:
- [Architecture](../ARCHITECTURE.ja.md)
- [Roadmap](../ROADMAP.md)
- [Distributed Open Model Commons](DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md)
- [Computational Memory](COMPUTATIONAL_MEMORY.ja.md)
- [Exploration Atlas](EXPLORATION_ATLAS.ja.md)
- [Latent Experience Capsule](LATENT_EXPERIENCE.ja.md)
- [世界規模化に向けた未解決課題](../GLOBAL_SCALE_CHALLENGES.ja.md)

---

## 1. 最終目標

DSCCの最終目標は、**世界中のクローズAI、オープンAI、人間、計算資源が同じ研究基盤上で協働し、AIそのものの研究・開発・評価・改良を継続できる分散AI研究所**を作ることである。

研究所の中心に一つのAIを置く必要はない。

参加者は異なる能力、異なるモデル、異なる運営者、異なる計算環境を持ってよい。

- 商用のクローズAI
- 公開されたオープンウェイトAI
- ローカルモデル
- 専門特化AI
- 将来の自律研究エージェント
- 人間の研究者
- 個人のGPU
- 大学や研究室の計算機
- 企業・クラウドの計算資源
- CPU / storage / relay node

これらを、一つのモデルへ統一するのではなく、**共通の研究Artifact、来歴、実験、評価、未解決課題、計算jobを介して協働させる。**

最終的な研究ループは次の形になる。

```text
既知研究・過去の実験
        ↓
問題の発見
        ↓
既存研究の検索・精読
        ↓
未解決点の特定
        ↓
仮説・設計候補
        ↓
実験計画
        ↓
分散計算
        ↓
評価・再現・反証
        ↓
新しい知見
        ↓
モデル・手法・データの改良
        ↓
DSCC研究記憶へ保存
        ↓
次のAI・人間が継続
        ↺
```

目標は、一回だけ強いモデルを作ることではない。

**研究能力そのものをネットワークへ蓄積し、次の研究者・次のAIが前の探索地点から続きを始められる状態を作る。**

---

## 2. Open Model Commonsは最終形ではなく計算・モデル層

Distributed Open Model Commonsは、この最終目標を支える重要な中間層である。

Open Model Commonsが担当するもの:

- open model checkpointの保存・配布
- model lineage
- inference
- training
- volunteer compute
- distributed pre-training
- evaluation compute
- heterogeneous GPU scheduling

Distributed AI Research Laboratoryは、その上で**研究そのもの**を動かす。

```text
Distributed AI Research Laboratory
            │
            ├── Literature / Knowledge
            ├── Computational Memory
            ├── Exploration Atlas
            ├── Research Agents
            ├── Evaluation / Verification
            │
            ▼
Distributed Open Model Commons
            │
            ├── Models
            ├── Checkpoints
            ├── Training
            ├── Inference
            └── Volunteer Compute
            │
            ▼
     DSCC Artifact / P2P layer
```

---

## 3. クローズAIも参加できる

DSCCの研究所は、オープンウェイトモデルだけで構成しない。

商用のクローズAIも、API、MCP、tool adapter、agent interfaceを通じて研究者として参加できる。

クローズAIに要求するのはweight公開ではない。

共有するのは、そのAIがDSCC上で行った研究活動のうち、共有可能な成果である。

例:

- 文献検索結果
- 論文の要約
- 研究仮説
- experiment proposal
- code patch
- evaluation
- failure analysis
- reproduction report
- model comparison
- DecisionRecord
- Claim / EvidenceLink
- MemoryCapsule

クローズAI自身の内部weightや非公開推論状態をDSCCへ出す必要はない。

その代わり、研究の再現に必要な範囲で、

- provider
- model identifier
- model revision / snapshot identifier if available
- prompt / task contract
- tool configuration
- input artifact CIDs
- output artifact CID
- timestamp / environment metadata

を記録する。

provider側でモデルが変更されれば完全再現できない場合もあるため、**閉じたモデルによる研究結果と、完全に再現可能なopen/local model runは区別して記録する。**

---

## 4. オープンAIは研究者にも研究対象にもなる

オープンモデルは二つの役割を持つ。

### Researcher

他のAIや人間と同じように、

- 論文を読む
- 仮説を作る
- codeを書く
- experimentを設計する
- 結果を解析する
- 次の研究を提案する

### Research Subject

同時に、

- architecture
- objective
- tokenizer
- memory
- attention
- optimizer
- training method
- dataset mixture
- inference method
- agent architecture

そのものを研究対象にできる。

したがって研究所では、

```text
AIが研究する
    ↓
AIを変更する
    ↓
変更されたAIが次の研究へ参加する
    ↓
さらにAIを研究する
```

という循環が成立する。

---

## 5. 人間も同じ研究ネットワークへ参加する

人間は外部observerではなく研究参加者として扱う。

人間が行える役割には、

- 問題設定
- 仮説
- experiment設計
- code
- dataset
- evaluation
- reproduction
- failure analysis
- compute提供
- model branch提案
- research priority設定
- 結果解釈

がある。

人間が作った研究ArtifactとAIが作った研究Artifactは、同じprovenance graph上で接続できる。

誰が作ったかはmetadataとして保持するが、検索や検証では「人間だから正しい」「AIだから正しい」とは扱わない。

---

## 6. 研究はまず既知研究から始める

研究agentの基本動作は、新しい実験をすぐ始めることではない。

最初に既知研究を調べる。

```text
Research Question
      ↓
Literature Search
      ↓
Primary Sources
      ↓
Known Results
      ↓
Known Limitations
      ↓
Unresolved Question
      ↓
Experiment
```

研究agentは、

1. 問いを明文化する。
2. 関連論文・実装・benchmarkを検索する。
3. 一次資料を読む。
4. 既知の答えを整理する。
5. 既存手法との重複を調べる。
6. 文献だけでは答えられない問いを抽出する。
7. その問いだけを実験へ回す。

DSCCには検索結果だけでなく、

- どの論文を読んだか
- 何が既知だったか
- どこが未解決だったか
- どの実験がその未解決点を検証したか

という関係を残す。

---

## 7. 本命設計を先に作る

AI研究所では、比較実験を作りやすくするために本命設計を弱く固定しない。

研究の目的に対して、最も強くなり得る自然な設計を先に作る。

```text
Goal
 ↓
Strongest useful design
 ↓
Stabilization
 ↓
Evaluation
 ↓
Ablations derived from the full design
```

比較用の簡略版は、本命設計から要素を削って作る。

benchmarkの都合やablationの都合を、最終architectureの制約にしない。

この原則はmodel architectureだけでなく、

- retrieval
- memory
- scheduler
- training method
- verification
- agent orchestration

にも適用する。

---

## 8. AIによるAI研究所の役割分担

一つの巨大agentに全研究工程を詰め込む必要はない。

専門research agentが同じArtifact graphを共有して協働できる。

```text
Literature Agent
    ↓
Problem / Gap Agent
    ↓
Hypothesis Agent
    ↓
Architecture / Method Agent
    ↓
Experiment Designer
    ↓
Compute Scheduler
    ↓
Training / Execution Agents
    ↓
Evaluation Agents
    ↓
Replication Agents
    ↓
Failure Analysis Agent
    ↓
Research Memory
    ↓
Next Research Cycle
```

同じ役割を複数の異なるAIへ依頼して結果を比較してもよい。

クローズAIとオープンAIを同じproblemへ参加させ、それぞれの強みを使うこともできる。

---

## 9. 研究Artifact

AI研究所では、最終回答だけではなく研究過程を構造化して保存する。

代表的なArtifact:

- ResearchQuestion
- LiteratureReview
- Claim
- EvidenceLink
- Hypothesis
- ExperimentPlan
- Tool
- Workflow
- Dataset
- ModelArtifact
- TrainingRun
- EvaluationRun
- VerificationReceipt
- FailureReport
- DecisionRecord
- MemoryCapsule
- ExplorationEpisode
- Bridge
- TransferAssessment
- OpenQuestion

現在のseed schemaにすべてを新kindとして直ちに追加する必要はない。

初期実装では既存kindのversioned payload profileとして追加し、必要になった時点でprotocol migrationを設計する。

---

## 10. 研究記憶はモデルから独立させる

研究所の継続性を、一つのAIモデルのcontextやproviderへ依存させない。

あるAIが研究を途中まで進めた場合、

```text
AI A
 ↓
Research Artifacts
 ↓
DSCC
 ↓
AI B
 ↓
続きの研究
```

と引き継げる。

AI AとAI Bが、

- 別会社
- 別モデル
- 別architecture
- open / closedの違い
- local / cloudの違い

を持っていてもよい。

共有するのは内部状態そのものではなく、まず外部化された研究Artifactである。

Computational Memory、Exploration Atlas、Latent Experience Capsuleは、この引継ぎを段階的に高密度化するための層になる。

---

## 11. 自律研究ループ

最終段階では、AIが研究ループを継続的に回せるようにする。

研究loopが保持する状態:

- current research goals
- unresolved questions
- literature state
- experiment queue
- available compute
- model branches
- evaluation results
- failed approaches
- replication status
- resource budget
- dependencies

一つのiterationは次のようになる。

```text
1. 未解決問題を選択
2. 最新研究を調査
3. 既知解を除外
4. 仮説を生成
5. 本命設計を作成
6. 実験を生成
7. 計算資源を選択
8. 実行
9. 評価
10. 再現・反証
11. 結果をArtifact化
12. 次の問題を更新
```

このloopは一つのモデルversionに固定しない。

より良いresearch agentやmodelが登場すれば、途中から参加し、過去のArtifactから研究を継続できる。

---

## 12. モデル進化と研究進化を分けない

通常のmodel developmentでは、研究を行う主体と研究対象が分離している。

DSCCの最終形では、その境界は薄くなる。

研究agent自身が改善対象になる。

例:

```text
Research Agent v1
       ↓
研究能力を評価
       ↓
memory / architecture / toolsを変更
       ↓
Research Agent v2
       ↓
v2が新しい研究を行う
       ↓
さらに改善
```

このとき、性能向上の原因を追跡するために、

- parent model
- changed components
- training run
- evaluation
- research-task performance
- failure profile

をlineageとして残す。

---

## 13. 一つのAIへ収束させない

研究所の目的は、すべての参加者を一つのモデルへ統合することではない。

複数branchが同時に存在できる。

```text
AI Research Ecosystem
├─ reasoning model branch
├─ efficient small-model branch
├─ multimodal branch
├─ scientific-agent branch
├─ long-memory branch
├─ novel-architecture branch
└─ experimental branches
```

異なる研究方向が並行して進み、必要に応じて知見だけを交換できる。

---

## 14. 研究の評価

AI研究所では、単一benchmark scoreだけを最適化対象にしない。

評価は目的ごとに複数持つ。

例:

- language modeling
- reasoning
- factual reliability
- long-context use
- learning efficiency
- compute efficiency
- memory
- transfer
- robustness
- calibration
- research productivity
- reproducibility

さらに「研究agentとして優れているか」を評価する場合、

- 文献で既知の答えを再発明しないか
- 未解決点を正しく抽出できるか
- experimentが問いに対応しているか
- failureから次の仮説を作れるか
- 他agentの研究を再利用できるか

も測定対象になる。

---

## 15. 研究所で解くべき新しい問題

最終形へ進むには、Open Model Commonsの問題に加えて研究orchestration固有の課題がある。

- closed AIとopen AIの共通Research Artifact contract
- provider/model versionの追跡
- 複数agent間のtask handoff
- 長期研究projectのstate管理
- 論文・code・実験のprovenance統合
- 同じ研究の重複検出
- failed experimentの再利用
- conflicting evidenceの管理
- benchmark overfittingの検出
- model branch間の比較
- experiment budget allocation
- research priority scheduling
- cross-agent reproducibility
- autonomous literature refresh
- continuously changing modelsへの追随
- AI researcher自身の能力評価

これらは [GLOBAL_SCALE_CHALLENGES.ja.md](../GLOBAL_SCALE_CHALLENGES.ja.md) で長期課題として管理する。

---

## 16. 段階的な到達点

### AIRL-0 — Shared research contract

異なるAIと人間が同じResearchQuestion、LiteratureReview、Hypothesis、ExperimentPlan、Evaluationを読み書きできるprofileを定義する。

### AIRL-1 — Cross-model handoff

二つ以上の異なるAIが、同じ研究課題をArtifact経由で引き継ぎ、前のAIの地点から研究を継続する。

対象には、可能ならopen modelとclosed modelの両方を含める。

### AIRL-2 — Multi-agent research team

literature、design、experiment、evaluationを異なるagentへ分担し、一つの研究成果まで到達する。

### AIRL-3 — AI model-development loop

small open modelを研究対象として、agent群がarchitecture / training / evaluation cycleを複数回回す。

### AIRL-4 — Distributed compute integration

Open Model Commonsと接続し、研究agentが世界分散computeへexperimentを配置する。

### AIRL-5 — Continuous research program

複数日にまたがる研究projectで、未解決問題、実験、model branch、評価を継続管理する。

### AIRL-6 — Distributed AI Research Laboratory

異なる組織のclosed AI、open AI、人間、compute providerが同じDSCC research networkへ参加し、複数のAI研究projectを並行して進める。

---

## 17. DSCC全体の最終構造

```text
 Humans ───────────────┐
 Closed AI ────────────┤
 Open AI ──────────────┤
 Local AI ─────────────┤
 Specialist Agents ────┘
          │
          ▼
 Distributed AI Research Laboratory
          │
   ┌──────┼─────────┬───────────┐
   ▼      ▼         ▼           ▼
Literature  Memory  Experiments  Evaluation
   │      │         │           │
   └──────┼─────────┴───────────┘
          ▼
   Computational Memory
          │
   Exploration Atlas
          │
   Research Artifact Graph
          │
          ▼
 Distributed Open Model Commons
          │
   ┌──────┼─────────┬───────────┐
   ▼      ▼         ▼           ▼
Models  Training  Inference   Compute
   │      │         │           │
   └──────┼─────────┴───────────┘
          ▼
      New Models
          │
          ▼
   New Research Agents
          │
          └──────────────────────↺
```

---

## 18. DSCCの最終的な役割

DSCCは、単なるP2P storageでも、分散GPU schedulerでも、LLM memory systemでもない。

それらを共通の研究基盤へ統合し、

**世界中のAIと人間が、過去の研究を継承し、計算資源を共有し、実験し、検証し、AIそのものを共同で開発し続ける分散研究所**

を作る。

完成形では、AI研究を行うAI自身も研究対象になり、改良されたAIが次の研究cycleへ参加する。

したがってDSCCの最終目標は、特定の一つのモデルを完成させることではない。

**AIを研究し続け、次のAIを作り続けるための共有研究生態系を構築することである。**
