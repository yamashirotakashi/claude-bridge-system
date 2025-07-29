# Claude Bridge System

Claude Code CLI と Claude Desktop の統合連携システム

## 📋 概要

Claude Bridge Systemは、Claude Code CLIとClaude Desktopの間でシームレスな連携を実現する統合開発環境です。ファイルベース通信により、両プラットフォームの利点を最大化します。

## 🏗️ アーキテクチャ

### 主要コンポーネント
- **BridgeFileSystem**: タスクファイルとリザルトファイルの管理
- **ProjectRegistry**: プロジェクト設定とメタデータの管理  
- **ProjectContextLoader**: プロジェクト情報の自動検出と読み込み
- **TaskGenerator**: 会話分析とタスク生成（開発中）

### 技術スタック
- **言語**: Python 3.8+
- **データ検証**: Pydantic
- **設定管理**: JSON
- **ファイル監視**: Watchdog
- **テスト**: pytest

## 🚀 機能

### ✅ 実装済み
- プロジェクトショートカット検出（`[tech]`, `[webapp]`等）
- プロジェクト間の依存関係分析
- ファイルベースタスク管理システム
- 統合コンテキストサマリ生成
- Pydantic設定検証

### 🚧 開発中
- タスク自動生成システム
- Claude Desktop連携API
- リアルタイム同期機能
- CLIインターフェース

## 📁 プロジェクト構造

```
claude_dc/
├── CLAUDE.md                 # プロジェクト設定
├── README.md                 # このファイル
├── requirements.txt          # Python依存関係
├── claude_bridge/            # メインパッケージ
│   ├── __init__.py
│   ├── exceptions.py         # カスタム例外
│   └── core/                 # コアモジュール
│       ├── bridge_filesystem.py
│       ├── project_registry.py
│       └── project_context_loader.py
├── config/                   # 設定ファイル
│   └── projects.json         # プロジェクト設定
├── bridge_data/              # 動的データ（.gitignore）
│   ├── tasks/               # タスクファイル
│   ├── results/             # 実行結果
│   └── cache/               # キャッシュ
├── docs/spec/                # 設計ドキュメント
└── tests/                    # テストファイル（予定）
```

## 🛠️ セットアップ

```bash
# リポジトリクローン
git clone https://github.com/yamashirotakashi/claude-bridge-system.git
cd claude-bridge-system

# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または venv\Scripts\activate  # Windows

# 依存関係インストール
pip install -r requirements.txt

# 基本テスト実行
python -c "from claude_bridge import BridgeFileSystem, ProjectRegistry, ProjectContextLoader; print('インポート成功')"
```

## 📖 使用例

```python
from claude_bridge import BridgeFileSystem, ProjectRegistry, ProjectContextLoader

# システム初期化
bridge_fs = BridgeFileSystem()
bridge_fs.initialize_structure()

registry = ProjectRegistry()
registry.load_config()

context_loader = ProjectContextLoader(registry)

# プロジェクト検出
message = "[tech] APIエンドポイントを修正してください"
detected_projects = context_loader.detect_project_shortcuts(message)
print(f"検出されたプロジェクト: {detected_projects}")

# コンテキスト生成
summary = context_loader.generate_context_summary(detected_projects)
print(summary)
```

## 🎯 ロードマップ

### Phase 1: 基盤構築 ✅
- [x] BridgeFileSystem実装
- [x] ProjectRegistry実装  
- [x] ProjectContextLoader実装
- [x] 基本品質テスト

### Phase 2: 機能拡張
- [ ] TaskGenerator実装
- [ ] CLIインターフェース
- [ ] ユニットテスト整備

### Phase 3: 統合機能
- [ ] Claude Desktop連携
- [ ] リアルタイム同期
- [ ] エラーハンドリング強化

### Phase 4: 運用対応
- [ ] 監視・ログ機能
- [ ] パフォーマンス最適化
- [ ] ドキュメント整備

## 🤝 コントリビューション

このプロジェクトは現在アクティブに開発中です。Issues、Pull Request、フィードバックを歓迎します。

## 📄 ライセンス

MIT License - 詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 🔗 関連プロジェクト

- [Claude Code CLI](https://docs.anthropic.com/claude/docs/claude-code)
- [Claude Desktop](https://claude.ai/desktop)

---

**Generated with Claude Bridge System MVP v1.0.0**
