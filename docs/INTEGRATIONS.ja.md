# LM Studio / Codex 接続

## 構造

AIアプリがstdio MCPプロセスを起動し、そのプロセスが指定されたDSCC保存領域へ接続する。二つのアプリで同じ`--home`を指定すれば、同じ研究記録を利用できる。学習済みモデルの重みを書き換える接続ではない。

## 設定生成

```sh
python -m dscc --home ~/.dscc init
python scripts/make_client_config.py --home ~/.dscc --out ./client-config
```

生成された `lmstudio.mcp.json` の `dscc` 項目を、LM Studioの `mcp.json` に追加する。公式ドキュメントではProgramパネルのInstallから編集できる。既存のサーバー設定を消さず、項目を追加する。

Codexには生成された `codex.config.toml` の `[mcp_servers.dscc]` 項目を追加する。既定の設定ファイルは `~/.codex/config.toml`。アプリの名称・設定画面は導入バージョンによって確認する。標準入力/標準出力の接続なのでポート番号は不要。

## 使い始めの指示例

「DSCCの状態を確認し、materialsを含む研究記録を検索して。見つかった記録の出典と親CIDを示して。新しい観察は、それまでの記録を親としてDSCCへ保存して。」

利用できる基本ツールは `node_status`、`search_assets`、`fetch_artifact`、`record_artifact`、`verify_artifact`、`inspect_tools`、`submit_job`、`job_status`。Open Model Commons向けに `record_open_model`、`inspect_open_model`、`record_compute_capability`、`record_training_run`、`plan_open_model_inference` も使える。これらはmetadataの記録・検査・配置案の作成だけを行う。weight blockの追加、ジョブ承認、model実行、GPU割当、外部公開はMCP経由では提供しない。

## 受入確認

モデルがツールを列挙できること、検索できること、記録を作れること、別アプリから同じCIDを読めることを確認する。ツール利用能力はローカルモデルにも依存する。設定ファイルの構文テストとstdio通信は今回検証するが、LM Studio/Codex本体との実機試験はT002の受入作業として残す。
