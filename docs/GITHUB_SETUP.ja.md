# GitHubで共同開発を続ける

リポジトリ: https://github.com/AwakeningOS/DSCC

アプリ名とPythonパッケージ名は `dscc-desktop`、GitHubリポジトリ名は `DSCC` です。新しいリポジトリを作り直す必要はありません。

## 取得と確認

```sh
git clone git@github.com:AwakeningOS/DSCC.git
cd DSCC
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m dscc demo
python scripts/check_repository.py
```

Windowsでは仮想環境の有効化を `.venv\Scripts\Activate.ps1` に置き換えます。鍵や実データをリポジトリ内へ置かないでください。

## エージェントに一つの課題を渡す

`AGENTS.md` と `docs/TASKS.md` を読ませ、対応するIssueで担当を宣言します。課題ごとに専用ブランチを作り、同時作業には別worktreeを使います。

```sh
git switch -c feat/T002-sdk-mcp
```

コード、テスト、引き継ぎをコミットして、そのブランチをpushし、`main`向けのPull Requestを作成します。レビュー担当は実装担当と分け、未検証事項はそのまま記録します。エージェントへアクセス権を与える際は、実際に必要なリポジトリだけを選んでください。

## 最初の担当候補

T001はローカルサービスと所有者権限、T002は公式MCP SDKとLM Studio/Codex接続、T003は隔離実行、T005はノード間通信、T009は独立検証です。UIとGPU workerには先行課題があります。詳しい依存関係と合格条件は各taskファイルにあります。

## GitHub側で別途設定する項目

CI用YAMLとPRテンプレートはリポジトリ内にあります。必須レビュー、必須チェック、branch protection、セキュリティ報告窓口、協力者へのアクセス権はリポジトリ管理画面で別途設定する必要があります。これらが既に有効になっているとは仮定しません。

`scripts/publish_github.py` は別の空のリポジトリを新規作成する場合の汎用補助です。既存の `AwakeningOS/DSCC` には使わず、通常のブランチとPRで更新してください。`scripts/seed_issues.py` は課題登録をプレビューできますが、既存Issueを確認し重複を作らないでください。
