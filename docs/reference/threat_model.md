# DSCC Threat Model v0.1

## 1. 保護対象

- 利用者のローカルデータと秘密鍵
- 科学成果物の完全性と来歴
- 計算ノードのホストOSと個人データ
- ジョブ入力、出力、未公開研究
- 信用・計算クレジット
- 検索索引の多様性と可用性
- 研究履歴、世界状態、未解決課題の連続性

## 2. 信頼しないもの

- 自然言語のツール説明
- 未署名のコンテナやWASM
- 検索順位
- 単一の計算結果
- 新規ノードの自己申告性能
- 単一検証者
- 外部データ内の命令文
- 公開P2Pノードが扱う中間activation
- 信用スコアだけに基づく正しさ

## 3. 主要攻撃と対策

| 攻撃 | 影響 | 主要対策 |
|---|---|---|
| 悪意あるジョブ | ホスト侵害、暗号採掘、DDoS | WASM/gVisor/microVM、network deny、quota、署名policy |
| 悪意あるworker | 虚偽結果、結果改変 | 冗長計算、spot check、invariant、署名receipt |
| Tool substitution | 別image実行 | OCI digest pin、Sigstore、in-toto、TUF |
| Prompt injection | AIの誤操作 | data/instruction分離、capability policy、人間承認 |
| Sybil attack | 索引・信用操作 | 新規node高検証率、diversity ranking、trust roots、rate limit |
| Eclipse attack | 偏ったpeerしか見えない | 複数bootstrap、connection diversity、外部monitor |
| Collusion | 複数workerが同じ虚偽 | ランダム監査、組織・ASN・鍵履歴の多様性 |
| Data poisoning | 誤データ拡散 | provenance、claim/evidence分離、replication、retraction |
| Privacy leakage | 秘密入力復元 | local-first、TEE、暗号化、公開collaborative inference禁止 |
| Credit fraud | 貢献水増し | requester/verifier共同署名、検証成功後に発行 |
| License laundering | 違法再配布 | SPDX、source attestations、access policy |
| Availability attack | 資産消失 | multi-pinning、retrieval audit、erasure coding |
| Index censorship | 発見不能 | 複数indexer、local index、CID直接共有 |
| Rollback/stale head | 古い状態へ誘導 | sequence number、expiry、signed head、gossip comparison |

## 4. 残存リスク

- GPUドライバとホストkernelの脆弱性
- TEE実装とサイドチャネル
- 複雑な科学計算の安価な検証不能性
- 人間が署名した悪質ツール
- 法的削除要求と不変保存の衝突
- 長期的な信用システムのゲーム化
- 高度な意味汚染と論文工場
- 公開ネットワークの資源集中

## 5. 安全上の境界

DSCCは参加者の明示許可を受けた資源のみを使用する。外部ホストへの侵入、資格情報の回避、無断計算、無断複製をprotocol上の機能にしない。ローカルnode ownerは、仕事の種類、最大時間、電力、network、データ範囲を常に制御できる。
