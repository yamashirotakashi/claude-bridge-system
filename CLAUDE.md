# グローバルルールの継承
@../CLAUDE.md

# ClaudeCode-ClaudeDesktop連携ブリッジプロジェクト

## 📋 プロジェクト概要
- **プロジェクト名**: ClaudeCode-ClaudeDesktop連携ブリッジ
- **特殊プロンプト**: `[claudebg]`
- **プロジェクトディレクトリ**: `/mnt/c/Users/tky99/dev/claude_dc`
- **目的**: Claude Code CLIとClaude Desktopの統合連携システム実装

## 🎯 プロジェクトミッション
Claude Code CLIとClaude Desktopの間でシームレスな連携を実現し、
両プラットフォームの利点を最大化する統合開発環境を構築する。

## 🏗️ アーキテクチャ設計
### 基本構成
- **Bridge Service**: 中央ハブとして動作する連携サービス
- **CLI Adapter**: Claude Code固有の機能をブリッジサービスに接続
- **Desktop Connector**: Claude Desktop固有の機能をブリッジサービスに接続
- **Sync Engine**: 状態同期とデータ一貫性を管理

### 技術スタック
- **言語**: Python (メインロジック), TypeScript (Desktop連携)
- **通信**: WebSocket, REST API, IPC
- **データ同期**: SQLite, JSON
- **設定管理**: YAML, Environment Variables

## 🔧 主要機能
1. **双方向状態同期**
   - Claude Codeの作業状態をClaude Desktopで参照
   - Claude Desktopでの作業をClaude Codeに反映

2. **統合ワークフロー**
   - プロジェクト切り替えの同期
   - ファイル編集状態の共有
   - TODO管理の統合

3. **リアルタイム通信**
   - 変更の即座な通知
   - 競合状態の検出と解決
   - セッション状態の管理

## 📁 ディレクトリ構造
```
claude_dc/
├── CLAUDE.md                      # このファイル
├── README.md                      # プロジェクト説明
├── src/
│   ├── bridge/                    # ブリッジサービス
│   ├── cli_adapter/               # Claude Code連携
│   ├── desktop_connector/         # Claude Desktop連携
│   └── sync_engine/               # 同期エンジン
├── config/
│   └── bridge_config.yaml         # 設定ファイル
├── docs/                          # ドキュメント
└── tests/                         # テストファイル
```

## 🚀 開発フェーズ
### Phase 1: 基盤構築
- [ ] プロジェクト構造の初期化
- [ ] 基本的な通信インフラの実装
- [ ] 設定管理システムの構築

### Phase 2: CLI連携
- [ ] Claude Code CLIとの接続確立
- [ ] 基本的な状態取得・送信機能
- [ ] コマンド実行のプロキシ機能

### Phase 3: Desktop連携
- [ ] Claude Desktop APIの調査・実装
- [ ] 双方向通信の確立
- [ ] UI状態の同期機能

### Phase 4: 統合機能
- [ ] リアルタイム同期の実装
- [ ] 競合解決メカニズム
- [ ] パフォーマンス最適化

### Phase 5: 運用・保守
- [ ] 監視・ログ機能
- [ ] エラーハンドリング強化
- [ ] ドキュメント整備

## 🔧 特殊プロンプト対応
### [claudebg] コマンド
```bash
[claudebg]                # プロジェクト切り替え
[claudebg] bridge         # ブリッジサービス起動
[claudebg] desktop        # Desktop連携機能テスト
[claudebg] sync           # 同期処理実行
[claudebg] status         # 連携状態確認
```

## 📋 開発規約
1. **コーディング標準**
   - PEP 8準拠（Python）
   - TypeScript ESLint設定準拠
   - 型ヒント必須

2. **テスト要件**
   - ユニットテストカバレッジ: 80%以上
   - 統合テスト必須
   - パフォーマンステスト実装

3. **ドキュメント要件**
   - API仕様書の作成
   - 運用手順書の整備
   - トラブルシューティングガイド

## 🔗 関連プロジェクト
- **Claude Code CLI**: メインの連携対象
- **Claude Desktop**: 連携対象プラットフォーム
- **MIS Integration**: 仕様駆動開発フレームワーク
- **VIBEZEN**: 品質保証システム

## 📝 メモ・備考
- 実装前にClaudeDesktopによって作成された計画文書を精読
- セキュリティ要件の詳細検討が必要
- パフォーマンス要件の定義と測定基準の設定