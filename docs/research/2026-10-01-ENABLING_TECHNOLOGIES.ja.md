# DSCC 実現を近づける新技術スカウト — 2026-10-01

状態: **実装・標準・製品技術の参考資料。ここに記載した外部機能はDSCCに実装済みではない。**  
確認日: **2026-10-01**  
確認したDSCC: `f52ef6fa6c5d2512ea9b0543366bec17dcafb745`  
目的: DSCCが独自に低レベル機構を再発明せず、成熟してきた外部技術をアダプターとして利用できるように、現在利用可能または標準化が進む技術を整理する。

関連:
- [Distributed Open Model Commons](../proposals/DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md)
- [Distributed AI Research Laboratory](../proposals/DISTRIBUTED_AI_RESEARCH_LAB.ja.md)
- [Experience and State Sharing](../proposals/EXPERIENCE_AND_STATE_SHARING.ja.md)
- [2026-09-25 最新論文スカウト](2026-09-25-LATEST_DSCC_PAPERS.ja.md)
- [世界規模化に向けた未解決課題](../GLOBAL_SCALE_CHALLENGES.ja.md)

## 1. 結論

2026年10月時点では、DSCCの実現に必要だった複数の部品が、別々の製品・OSS・標準としてかなり具体化している。

```text
agent / resource discovery
    DNS-AID
        ↓
AI asset / model / skill sharing
    OpenSharing
        ↓
local / nearby GPU pool
    WiCi / exo
        ↓
distributed inference data plane
    Dynamo + NIXL / vLLM KV transfer
        ↓
high-performance local island
    UALink / Ultra Ethernet / CXL
        ↓
DSCC provenance / policy / research-state layer
```

DSCCが価値を出す場所は、これらを置き換えることではなく、**来歴、権限、研究状態、経験、検証、公開範囲を保ったまま接続する上位層**にある。

## 2. 優先度サマリー

| ID | 技術 | DSCC接続 | 今すぐ使える度 | 主な役割 |
|---|---|---|---|---|
| E01 | WiCi Protocol | T006/T011 | Preview / vendor implementation | LAN GPU worker・状態をGPU側に残す設計 |
| E02 | NVIDIA Dynamo + NIXL | T011 | OSS / production-oriented | prefill-decode分離、KV/weight data plane |
| E03 | vLLM KV transfer / LMCache connector | T011 | OSS | KV転送を交換可能なconnectorとして扱う |
| E04 | OpenSharing | T005/T007/T011/T012 | OSS/spec | model・data・skillのzero-copy共有 |
| E05 | DNS-AID | T002/T005/T009/T012 | OSS + IETF draft | 分散agent/MCP discovery |
| E06 | exo | T006/T011 | OSS | ローカル異種device clusterとtopology-aware parallel |
| E07 | UALink | T006/T011 | industry standard | accelerator scale-up island |
| E08 | Ultra Ethernet | T005/T006/T011 | industry standard | AI/HPC scale-out network |
| E09 | CXL 4.0 | T006/T011 | industry standard / hardware-dependent | memory pooling・tiering・composition |
| E10 | Open agent/asset stack separation | T002/T005/T007/T012 | design rule | discovery/transport/assets/research semanticsを分離 |

優先度の意味:
- **Immediate adapter**: E03/E04/E05は、DSCC側で外部adapter設計を始められる。
- **Local prototype**: E01/E02/E06は、T001/T003/T006の境界が整った後にLAN/単一owner環境で実機試験しやすい。
- **Hardware horizon**: E07/E08/E09は、DSCCが独自実装するものではなく、将来のcapability/runtime profileで認識すべき基盤。

---

## 3. E01 — WiCi Protocol: GPUを「ネットワークPCIe」にせず、仕事をGPU側へ寄せる

一次資料:
- https://wici.ai/technology
- https://wici.ai/article/nearby-gpu-feel-local.html
- https://developer.wici.ai/

### 確認できること

WiCiはローカルネットワーク上の専用GPU箱を、API、SDK、GPU runtimeから利用する設計を公開している。OpenAI/Ollama互換endpoint、model caching、token streaming、workload priority、複数端末からの共有を掲げる。

技術資料では、naiveなGPU remotingは多数の細かいdriver callが各々RTTを支払うため成立しにくく、stable factsのcache、重複排除、streaming、pipelining、expensive stateのGPU側保持でblocking round tripを減らす方針を説明している。

### DSCCへの意味

DSCCの第一段階のGPU共有は、遠隔GPUをPCIe deviceとして完全透過化するより、

```text
model / checkpoint / cache をworker側に保持
          ↓
job + input CIDだけ送る
          ↓
result / receiptだけ返す
```

方が現実的である。

T011では「独立GPU workerへのjob offload」をLevel 1、「cache/model locality-aware scheduling」をLevel 2として先に実装し、tight tensor/pipeline parallelは後段に置くべきという根拠になる。

### 実装候補

- capability profileへ `network_locality`, `resident_model_cids`, `resident_block_cids`, `queue_class`, `estimated_rtt_ms` を将来追加するADR候補。
- scheduler costをVRAM容量だけでなく `model_load + transfer + RTT-bound synchronizations + queue wait` で比較する。
- OpenAI-compatible remote worker adapterを、owner-approved job runtimeの外側にprototypeとして作る。
- model/block localityをsoft-state indexとして保持し、実際のblock CID検証と分ける。

### 受入証拠

- 同一LANでlocal GPU / remote API / naive RPC相当を比較。
- job種別ごとのbytes、RTT、blocking boundary、model load time、TTFT、throughputを記録。
- WiCiの公開性能値はvendor報告として扱い、DSCCの性能値へ転記しない。

---

## 4. E02 — NVIDIA Dynamo + NIXL: 分散推論のcontrol planeとdata planeを分離する

一次資料:
- https://docs.nvidia.com/dynamo/
- https://docs.nvidia.com/dynamo/dev/kubernetes/disaggregated-serving/overview
- https://github.com/ai-dynamo/nixl/blob/main/docs/nixl.md
- https://developer.nvidia.com/blog/enhancing-distributed-inference-performance-with-the-nvidia-inference-transfer-library/

### 確認できること

Dynamoは分散推論frameworkとして、disaggregated serving、KV-aware routing、cache management、autoscalingを扱う。prefill workerとdecode workerを別poolへ分け、KV cacheをworker間で移動させる構成を公開している。

NIXLはHBM/VRAM、DRAM、NVMe、file/object storage等を共通のtransfer abstractionで扱うdata-movement libraryで、UCX、GDS等のbackendをplug-inとして利用する。NIXL自身はorchestratorではなく、上位conductorがrequest、allocation、metadata exchangeを管理する前提になっている。

### DSCCへの意味

DSCCは低レベル転送engineを自作せず、

```text
DSCC
  ├─ authority / provenance / policy / scheduling intent
  └─ adapter
       ↓
Dynamo / vLLM / other runtime
       ↓
NIXL / UCX / GDS / TCP / storage backend
```

という責任分担を取れる。

### 実装候補

- T011 runtime adapter interfaceに `prepare / transfer / execute / collect_receipt` を定義し、Dynamo/NIXLを一実装候補にする。
- NIXL backend名をDSCC protocolの固定enumにせず、versioned runtime capabilityとして記録する。
- KV transfer、weight transfer、checkpoint transferを同じ「bytes移動」として雑に扱わず、semantic typeを保持する。
- data planeの成功とscientific correctnessを別receiptにする。

### 受入証拠

- 2 GPU trusted hostでprefill/decode分離とaggregated servingを比較。
- KV bytes、transfer time、TTFT、TPOT、worker failure時fallbackを保存。
- runtimeの実行権限はT001/T003のowner boundaryを通す。

---

## 5. E03 — vLLM KV transfer / LMCache connector: KV移動を交換可能なinterfaceにする

一次資料:
- https://docs.vllm.ai/en/latest/api/vllm/config/kv_transfer/
- https://docs.vllm.ai/en/stable/api/vllm/distributed/kv_transfer/kv_connector/v1/lmcache_mp_connector/

### 確認できること

vLLMは`KVTransferConfig`を持ち、分散KV cache transfer用connectorを設定可能にしている。LMCache multi-process connector等も公開されており、KV data planeが特定実装へ固定されない方向が進んでいる。

### DSCCへの意味

Experience/State Sharingで提案した `converter profile` と、runtimeで実際にbytesを動かす `transport connector` を分離できる。

```text
semantic compatibility
  model A cache → model B cache converter
        ↓
runtime transfer connector
  NIXL / LMCache / torch-distributed / future backend
```

この二つを同じものにしないことが重要。

### 実装候補

- DSCC側のstate manifestに `logical_format` と `transport_connector_profile` を別参照で持つ。
- vLLM connectorを検出・記録するadapterを作り、未対応connectorは拒否ではなくcapability unknownとして扱う。
- exact-prefix transferとcross-model converted cacheを別job classにする。

### 受入証拠

- 同じcache artifactを複数connectorで移動してdigest一致を確認。
- transfer成功とmodel quality保持を別々に評価。
- connector更新時に古いevaluationを自動継承しない。

---

## 6. E04 — OpenSharing: DSCCのmodel/data/skill共有を独自APIだけに閉じない

一次資料:
- https://www.linuxfoundation.org/press/linux-foundation-announces-opensharing-project-to-standardize-ai-asset-and-data-exchange
- https://github.com/OpenSharing-IO/OpenSharing
- https://opensharing.io/

### 確認できること

OpenSharingはLinux Foundation AI & Data配下のopen protocolで、Table、Volume、AgentSkill、Modelを共通のshare/schema/asset hierarchyで共有する。assetsをコピーせず、provider storageに保持したままshort-lived scoped credentialまたはpresigned URLを渡すzero-copy credential vendingを採用する。

`Agent`自体の共有は確認時点ではcommunity proposalであり、specified assetと同列に完成扱いしない。

### DSCCへの意味

T007/T011でmodel weights、dataset、agent skillを世界共有する際、DSCC専用download protocolだけを作る必要はない。

DSCCが保持すべきなのは、

- CID / immutable identity
- provenance
- license / consent
- scientific relation
- DSCC policy

であり、actual bytesへのaccessはOpenSharing adapterへ委譲できる可能性がある。

### 実装候補

- T007にOpenSharing import/export adapter laneを追加する候補。
- `Model` → OMC model manifest、`Volume` → dataset/raw artifact、`AgentSkill` → Tool/Workflowへのmapping tableを作る。
- credentialはArtifactへ永続保存せず、取得時のephemeral secretとして扱う。
- OpenSharing asset revisionとDSCC CIDの対応を明示し、mutable URLをCID代替にしない。

### 受入証拠

- 同じassetをcopyせず取得し、取得byteのCIDをDSCC側で検証。
- credential期限切れ、revocation、provider unavailableを扱う。
- private shareをpublic indexへ漏らさない。

---

## 7. E05 — DNS-AID: 中央registryなしのagent/MCP discovery

一次資料:
- https://www.linuxfoundation.org/press/linux-foundation-announces-dns-aid-project-to-advance-decentralized-ai-agent-discovery
- https://github.com/dns-aid/dns-aid-core
- https://www.dns-aid.org/
- IETF draft: https://datatracker.ietf.org/doc/draft-mozleywilliams-dnsop-dnsaid/

### 確認できること

DNS-AIDはDNSを使ってagent/MCP endpointを公開・発見するreference implementationで、仕様はIETF draft側で開発されている。DNSSEC、JWS、DANE等を組み合わせるtrust pathを持ち、中央registryやhard-coded URLを避ける。

### DSCCへの意味

T005のpeer discoveryをすべてKademlia DHTだけに賭ける必要はない。

```text
organization-owned stable endpoint
    DNS-AID / DNSSEC
          +
ephemeral / content discovery
    DHT / local discovery / federated index
```

のhybridが可能。

特にclosed AI service、institutional verifier、gateway、MCP endpointの発見はDNSと相性が良い。

### 実装候補

- DNS-AID discovery adapterをT002/T005の独立moduleとしてprototype。
- discovery recordから得たendpointを「identity verified」「scientific trusted」と自動昇格しない。
- DNS domain ownership、DSCC signing key、research authorityを別のidentity layerとして保持。
- DNS failure時にmanual invitationを維持する。

### 受入証拠

- DNSSEC valid/invalid、record rotation、expired endpoint、split-horizon DNSを試験。
- discovery resultがowner approvalを迂回してremote executionを起動しない。
- DNSが落ちても既知peerとのローカル作業を継続できる。

---

## 8. E06 — exo: 家庭・研究室内の複数deviceを一つの推論islandにする

一次資料:
- https://github.com/exo-explore/exo

### 確認できること

exoは複数deviceのautomatic discovery、topology-aware model partition、Tensor Parallel、MLX distributed、OpenAI/Claude/Ollama互換APIを持つOSS。current READMEではThunderbolt 5 RDMA対応も掲げる。性能値はproject/benchmark source依存なのでDSCCで再現するまで一般化しない。

### DSCCへの意味

T011の「世界中のGPUを直接一つにする」前に、

```text
home / lab / office island
  ├─ device A
  ├─ device B
  └─ device C
       ↓
island-level inference endpoint
       ↓
DSCC world network
```

と二層化できる。

WAN越しのtensor-parallelを避け、低遅延linkがある場所だけtight couplingする設計になる。

### 実装候補

- DSCC capabilityに `compute_island`概念を追加するADR候補。
- island内部topologyはexo等へ任せ、DSCCはaggregate capabilityとmeasured endpoint performanceを扱う。
- exo adapterはまずOpenAI-compatible endpointとして接続し、内部parallelismをDSCCが再実装しない。

### 受入証拠

- single device vs multi-deviceのlatency/throughput/memory limitを実測。
- device dropout時の挙動を記録。
- Apple Silicon等で得た結果をNVIDIA consumer GPUへ外挿しない。

---

## 9. E07 — UALink: open scale-up accelerator island

一次資料:
- https://ualinkconsortium.org/specification/
- https://ualinkconsortium.org/resource_library/
- https://ualinkconsortium.org/blog/whats-next-for-ualink-400g-data-rate-optical-interconnects-end-to-end-resiliency-and-richer-management-features-1563/

### 確認できること

UALink 200G 1.0はaccelerator-to-accelerator/switch用のopen scale-up interconnectを定義し、最大1,024 accelerator規模を対象にする。Common 2.0はIn-Network Computeを追加し、分散training/inferenceの通信削減を狙う。2026年9月には400G、optical、resiliency等の将来方向も公開されている。

### DSCCへの意味

これはWAN participant protocolではない。DSCCの各compute island内部で、NVLink等のvendor-specific fabric以外のopen scale-up optionが増えることを意味する。

### 実装候補

DSCC側でUALink protocolを実装しない。capability profileに、

- interconnect class
- measured peer bandwidth/latency
- collective support
- topology
- isolation boundary

を記録し、UALink/NVLink/XGMI等をruntime-specific valueとして扱う。

### 受入証拠

hardwareが出た時点で実測する。spec上の200G/lane等を実効application bandwidthとして使わない。

---

## 10. E08 — Ultra Ethernet: open scale-out fabric

一次資料:
- https://ultraethernet.org/
- https://ultraethernet.org/specification-history/
- https://ultraethernet.org/accelerating-ai-with-open-standards-uecs-expanding-vision/

### 確認できること

Ultra Ethernet ConsortiumはAI/HPC向けのopen Ethernet stackを開発し、確認時点のcurrent published specificationは1.0.3（2026-07-16）。UETはRDMA系data movement、congestion control、tail latency等をAI/HPC向けに改善する。

### DSCCへの意味

T005のinternet P2P transportと、data center / lab island内のhigh-performance scale-out fabricは同じ層ではない。

```text
DSCC global control / artifact layer
          ↓
site gateway
          ↓
Ultra Ethernet / RoCE / InfiniBand island
```

という構成で、世界規模の弱い回線と施設内の強いfabricを分けられる。

### 実装候補

- network capabilityを `wan / lan / scale_out / scale_up` 等の意味で整理する。
- runtime adapterがUET/UCX/libfabric等を使っても、core DSCC artifact protocolは不変にする。

### 受入証拠

vendor/spec最大値でなく、job classごとのmeasured latency/bandwidth/tailを保存。

---

## 11. E09 — CXL 4.0: memory pooling / tieringを将来のworkerへ取り込む

一次資料:
- https://computeexpresslink.org/
- https://computeexpresslink.org/news/
- https://computeexpresslink.org/resource-library/

### 確認できること

CXL 4.0は2025年11月公開で、bandwidthを64 GT/sから128 GT/sへ増加しbundled portsを追加した。CXL ecosystemは以前からmemory pooling/sharingを持ち、2026年にはAI inferenceのmemory pooling/tieringを扱う業界資料が増えている。

### DSCCへの意味

consumer GPUのVRAMを無制限に共有できる技術ではないが、将来のserver/islandでは、

- model weights
- KV cache
- optimizer state
- dataset cache

をHBM/DRAM/CXL memory/NVMeへ階層化するruntimeが現実的になる。

WiCiのVRAM/RAM/NVMe tiering思想とも接続する。

### 実装候補

DSCCはCXLを直接制御せず、worker capabilityとしてmemory tiersを一般化する。

```text
memory_tiers:
  - hbm/vram
  - host_dram
  - fabric_memory
  - local_nvme
  - remote_storage
```

各tierにcapacity、measured bandwidth、latency、persistence、sharing/isolation classを記録する。

### 受入証拠

CXL hardwareなしのsimulationを実機性能と扱わない。将来、real deviceでmodel load/KV spill/checkpointの効果を測る。

---

## 12. E10 — 統合原則: protocolを一つにしない

上の技術から、DSCCのprotocol stackは次のように分けるのが自然である。

| 層 | 候補技術 | DSCCが保持する責任 |
|---|---|---|
| Agent/service discovery | DNS-AID, local discovery | endpoint候補、検証状態、owner consent |
| Agent invocation | MCP, A2A, HTTP/OpenAI-compatible | tool/request semanticsへのadapter |
| Asset sharing | OpenSharing | CID/provenance/license/policyとのbinding |
| Artifact transport | T005 P2P / HTTP / storage | immutable bytes、resume、availability |
| Inference data plane | NIXL, vLLM KV connector, LMCache | transfer evidence、runtime profile |
| Local GPU island | WiCi, exo, Dynamo | measured capability、queue、job receipts |
| Scale-out/up fabric | Ultra Ethernet, UALink, vendor fabrics | topology/capabilityの観測 |
| Memory fabric | CXL | tier capability、isolation、measurement |
| Research semantics | DSCC T010/T012 | hypothesis/evidence/failure/state/experience |
| Authority & verification | DSCC T001/T009 | permissions、integrity、scientific verification |

**発見できる ≠ 信頼できる ≠ 実行を許可する ≠ 科学的に正しい**、という既存原則を全層に適用する。

## 13. 今すぐ切り出せる実装lane

### Lane N1 — DNS-AID discovery adapter

接続: T002/T005/T009  
実機依存: 低

成果物:
- domainからMCP/A2A endpoint候補を取得するread-only adapter
- DNSSEC/JWS validation stateの記録
- manual invitationとの併用
- owner approvalを迂回しないtest

完了条件:
- discoveryだけではjob実行できない
- invalid DNSSEC/署名を明確に表示
- endpoint更新と失効を扱う

### Lane N2 — OpenSharing asset adapter

接続: T007/T011  
実機依存: 中

成果物:
- Model/Volume/AgentSkill metadata mapping
- ephemeral credential handling
- fetched bytesのCID検証
- provider unavailable/revocation test

完了条件:
- credentialをDSCC artifactへ保存しない
- mutable remote assetとimmutable DSCC CIDを混同しない
- source/license/provenanceが復元できる

### Lane N3 — KV transfer runtime abstraction

接続: T011 / Experience-State  
実機依存: 中

成果物:
- vLLM KV connector / NIXL adapter contract
- logical cache profileとtransport profileの分離
- digest/integrity test
- full-prefill fallback

完了条件:
- connector交換でartifact semanticsが変わらない
- transfer成功とquality保持を別評価
- unknown connectorを安全に扱う

### Lane N4 — Nearby GPU worker benchmark

接続: T006/T011  
実機依存: 高

参考: WiCi / exo

成果物:
- local API GPU worker prototype
- model residency/cache locality measurement
- scheduler cost model
- LAN fault/latency injection

完了条件:
- local/remote/model-not-residentを比較
- network bytes/RTT/TTFT/queue/model-loadを実測
- vendor claimではなくDSCC own measurementsを残す

### Lane N5 — Compute island abstraction

接続: T006/T011  
実機依存: 中→高

参考: exo / Dynamo / UALink / Ultra Ethernet / CXL

成果物:
- island-level capability profile
- aggregate endpoint vs individual deviceの区別
- interconnect/memory tier measurements
- internal implementationをDSCC coreから隠蔽

完了条件:
- island内部fabricを交換してもworld-facing contractは不変
- aggregate memoryを「一枚のGPU VRAM」と誤表示しない
- failure domainを記録する

## 14. DSCCロードマップへの影響

従来のイメージ:

```text
P2P
 → GPU sharing
 → distributed inference
 → distributed training
 → research lab
```

より、実装上は次の段階が自然。

```text
1. signed research / artifact layer               [既に一部実装]
2. external discovery + asset adapters            [DNS-AID/OpenSharing]
3. independent nearby GPU workers                 [WiCi型]
4. model/cache locality scheduling                [Dynamo/vLLM型]
5. compute islands                                [exo/cluster runtime]
6. disaggregated inference data plane             [NIXL/KV connectors]
7. tight local multi-accelerator                   [UALink/vendor fabric]
8. fast site scale-out                            [Ultra Ethernet]
9. memory composition/tiering                     [CXL]
10. WAN distributed training/research orchestration
```

Level 2–5だけでも、DSCCは「世界GPUを一枚のGPUにする」前に実用品になり得る。

## 15. 後任エージェントへのルール

1. 外部protocol/runtimeをcoreへコピーせず、adapterとして接続できないか先に検討する。
2. open specificationとvendor previewを同じ確度で扱わない。
3. spec最大帯域をapplication実測値として保存しない。
4. endpoint discovery、asset access、job authorization、scientific verificationを別stateにする。
5. third-party credential/private tokenをArtifactへ保存しない。
6. external projectのversion/licenseを実装時に再確認する。
7. hardware未入手ならcontract testまでとし、性能を推定で完了扱いしない。
8. 採用した技術が廃れたときにadapterだけ交換できる構造を守る。

## 16. 参考リンク

- WiCi Protocol: https://wici.ai/technology
- WiCi Developer Portal: https://developer.wici.ai/
- NVIDIA Dynamo: https://docs.nvidia.com/dynamo/
- NIXL: https://github.com/ai-dynamo/nixl
- vLLM KV transfer: https://docs.vllm.ai/en/latest/api/vllm/config/kv_transfer/
- OpenSharing: https://github.com/OpenSharing-IO/OpenSharing
- Linux Foundation OpenSharing announcement: https://www.linuxfoundation.org/press/linux-foundation-announces-opensharing-project-to-standardize-ai-asset-and-data-exchange
- DNS-AID: https://github.com/dns-aid/dns-aid-core
- DNS-AID IETF draft: https://datatracker.ietf.org/doc/draft-mozleywilliams-dnsop-dnsaid/
- exo: https://github.com/exo-explore/exo
- UALink: https://ualinkconsortium.org/specification/
- Ultra Ethernet: https://ultraethernet.org/specification-history/
- CXL: https://computeexpresslink.org/

この資料をマージしても、外部技術の採用、互換性、性能、安全性がDSCCで実証されたことにはならない。実装状態は各Task/Issue/validation reportで更新する。
