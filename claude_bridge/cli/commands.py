"""
Claude Bridge System - CLI Commands
個別コマンドの実装
"""

import json
import yaml
import click
import sys
from datetime import datetime
from pathlib import Path

from ..exceptions import BridgeException


def init_command(ctx, force: bool) -> None:
    """システム初期化コマンド"""
    try:
        bridge_fs = ctx.obj['bridge_fs']
        registry = ctx.obj['registry']
        
        click.echo("🚀 Claude Bridge System を初期化しています...")
        
        # ブリッジファイルシステムの初期化
        success = bridge_fs.initialize_structure(force=force)
        if success:
            click.echo("✅ ブリッジファイルシステム初期化完了")
        
        # プロジェクト設定の読み込み
        try:
            config = registry.load_config()
            project_count = len(config.get('projects', {}))
            click.echo(f"✅ プロジェクト設定読み込み完了 ({project_count}個のプロジェクト)")
        except Exception as e:
            click.echo(f"⚠️  プロジェクト設定の読み込みに失敗: {e}")
            click.echo("   デフォルト設定で続行します")
        
        # 初期化完了
        click.echo("\\n🎉 初期化が完了しました！")
        click.echo("\\n次のコマンドで使用を開始できます:")
        click.echo("  claude-bridge status          # システム状態確認")
        click.echo("  claude-bridge project list    # プロジェクト一覧")
        click.echo("  claude-bridge analyze \"[tech] APIを修正\"  # 会話分析")
        
    except BridgeException as e:
        click.echo(f"❌ 初期化に失敗しました: {e}", err=True)
        sys.exit(1)


def analyze_command(ctx, content: str, projects: list, output_format: str) -> None:
    """会話分析コマンド"""
    try:
        task_generator = ctx.obj['task_generator']
        
        click.echo(f"🔍 会話内容を分析しています...")
        
        # 分析実行
        analysis = task_generator.analyze_conversation(content, projects)
        
        if analysis['status'] == 'error':
            click.echo(f"❌ 分析に失敗しました: {analysis['error']}", err=True)
            sys.exit(1)
        
        # 結果出力
        if output_format == 'json':
            click.echo(json.dumps(analysis, ensure_ascii=False, indent=2))
        elif output_format == 'yaml':
            click.echo(yaml.dump(analysis, allow_unicode=True, default_flow_style=False))
        else:  # markdown
            _output_analysis_markdown(analysis)
        
    except BridgeException as e:
        click.echo(f"❌ 分析エラー: {e}", err=True)
        sys.exit(1)


def _output_analysis_markdown(analysis: dict) -> None:
    """分析結果のMarkdown出力"""
    click.echo("\\n# 📊 会話分析結果")
    click.echo("=" * 30)
    
    # 基本情報
    click.echo(f"**検出プロジェクト**: {', '.join(analysis['detected_projects']) if analysis['detected_projects'] else 'なし'}")
    click.echo(f"**複雑度スコア**: {analysis['complexity_score']}/10")
    click.echo(f"**信頼度**: {analysis['confidence']:.2f}")
    
    # タスク候補
    if analysis['task_candidates']:
        click.echo(f"\\n## 🎯 タスク候補 ({len(analysis['task_candidates'])}個)")
        for i, candidate in enumerate(analysis['task_candidates'], 1):
            click.echo(f"\\n### {i}. {candidate['description']}")
            click.echo(f"- タイプ: {candidate['type']}")
            click.echo(f"- 優先度: {candidate['priority']}")
            click.echo(f"- 信頼度: {candidate['confidence']:.2f}")
    
    # アクションアイテム
    if analysis['action_items']:
        click.echo(f"\\n## ⚡ アクションアイテム ({len(analysis['action_items'])}個)")
        for i, item in enumerate(analysis['action_items'], 1):
            click.echo(f"\\n### {i}. {item['description']}")
            click.echo(f"- 関連プロジェクト: {item['related_project'] or 'なし'}")
            click.echo(f"- 緊急度: {item['urgency']}")
            click.echo(f"- 実行可能性: {item['actionable']:.2f}")
    
    # 推奨事項
    if analysis['recommendations']:
        click.echo(f"\\n## 💡 推奨事項")
        for i, rec in enumerate(analysis['recommendations'], 1):
            click.echo(f"{i}. {rec}")


def generate_command(ctx, content: str, projects: list, output: str, metadata: str) -> None:
    """タスク生成コマンド"""
    try:
        task_generator = ctx.obj['task_generator']
        
        click.echo("⚙️  タスクファイルを生成しています...")
        
        # メタデータの解析
        metadata_dict = None
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
            except json.JSONDecodeError as e:
                click.echo(f"⚠️  メタデータの解析に失敗: {e}")
        
        # タスク生成実行
        task_file = task_generator.generate_task_file(content, projects, metadata_dict)
        
        # 出力ファイル指定がある場合はコピー
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(task_file, 'r', encoding='utf-8') as src:
                with open(output_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            click.echo(f"✅ タスクファイル生成完了: {output_path}")
        else:
            click.echo(f"✅ タスクファイル生成完了: {task_file}")
        
        # 内容のプレビュー
        if ctx.obj['verbose']:
            click.echo("\\n📄 生成されたタスクファイル:")
            click.echo("-" * 40)
            with open(task_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for i, line in enumerate(lines[:20]):  # 最初の20行のみ
                    click.echo(line.rstrip())
                
                if len(lines) > 20:
                    click.echo(f"... (残り {len(lines) - 20} 行)")
        
    except BridgeException as e:
        click.echo(f"❌ タスク生成エラー: {e}", err=True)
        sys.exit(1)


def status_command(ctx, detailed: bool) -> None:
    """システム状態確認コマンド"""
    try:
        bridge_fs = ctx.obj['bridge_fs']
        registry = ctx.obj['registry']
        task_generator = ctx.obj['task_generator']
        
        click.echo("🔍 Claude Bridge System 状態確認")
        click.echo("=" * 50)
        
        # ブリッジファイルシステム状態
        fs_stats = bridge_fs.get_system_stats()
        click.echo(f"\\n📁 ファイルシステム:")
        click.echo(f"  ルートディレクトリ: {fs_stats['bridge_root']}")
        click.echo(f"  初期化状態: {'✅ 完了' if fs_stats['initialized'] else '❌ 未完了'}")
        click.echo(f"  未処理タスク: {fs_stats['pending_tasks']}")
        click.echo(f"  処理中タスク: {fs_stats['processing_tasks']}")
        click.echo(f"  完了タスク: {fs_stats['completed_tasks']}")
        click.echo(f"  成功結果: {fs_stats['success_results']}")
        click.echo(f"  エラー結果: {fs_stats['error_results']}")
        
        # プロジェクト設定状態
        try:
            projects = registry.list_projects(active_only=False)
            active_count = len(registry.list_projects(active_only=True))
            
            click.echo(f"\\n🗂️  プロジェクト設定:")
            click.echo(f"  総プロジェクト数: {len(projects)}")
            click.echo(f"  アクティブ: {active_count}")
            click.echo(f"  非アクティブ: {len(projects) - active_count}")
            
            if detailed and projects:
                click.echo(f"\\n  プロジェクト一覧:")
                for project_id, config in projects.items():
                    status_icon = "🟢" if config.active else "🔴"
                    click.echo(f"    {status_icon} {config.shortcut} {config.name}")
        
        except Exception as e:
            click.echo(f"\\n🗂️  プロジェクト設定: ❌ エラー ({e})")
        
        # タスク生成統計
        try:
            gen_stats = task_generator.get_generation_stats()
            if 'error' not in gen_stats:
                click.echo(f"\\n⚙️  タスク生成:")
                click.echo(f"  生成パターン数: {gen_stats['task_patterns']}")
                
                if 'cache' in gen_stats:
                    cache_stats = gen_stats['cache']
                    click.echo(f"  キャッシュプロジェクト数: {cache_stats['cached_projects']}")
        
        except Exception as e:
            click.echo(f"\\n⚙️  タスク生成: ❌ エラー ({e})")
        
        # システム全体の健全性
        issues = []
        if not fs_stats['initialized']:
            issues.append("ファイルシステムが初期化されていません")
        
        if len(projects) == 0:
            issues.append("プロジェクトが設定されていません")
        
        click.echo(f"\\n🏥 システム健全性:")
        if issues:
            click.echo("  ⚠️  以下の問題があります:")
            for issue in issues:
                click.echo(f"    • {issue}")
            click.echo("\\n  解決方法: claude-bridge init を実行してください")
        else:
            click.echo("  ✅ 正常に動作しています")
        
        click.echo(f"\\n最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except BridgeException as e:
        click.echo(f"❌ 状態確認エラー: {e}", err=True)
        sys.exit(1)


def clean_command(ctx, days: int, dry_run: bool) -> None:
    """クリーンアップコマンド"""
    try:
        bridge_fs = ctx.obj['bridge_fs']
        
        if dry_run:
            click.echo(f"🧹 {days}日より古いファイルの削除予定 (Dry Run)")
        else:
            click.echo(f"🧹 {days}日より古いファイルを削除しています...")
        
        if not dry_run:
            cleanup_stats = bridge_fs.cleanup_old_files(days)
            
            click.echo("\\n削除完了:")
            click.echo(f"  完了タスク: {cleanup_stats['completed_tasks']} ファイル")
            click.echo(f"  結果ファイル: {cleanup_stats['results']} ファイル")
            click.echo(f"  キャッシュ: {cleanup_stats['cache']} ファイル")
            
            total_deleted = sum(cleanup_stats.values())
            click.echo(f"\\n合計 {total_deleted} ファイルを削除しました。")
        else:
            # Dry runの場合は統計のみ表示
            stats = bridge_fs.get_system_stats()
            click.echo("\\n現在のファイル数:")
            click.echo(f"  完了タスク: {stats['completed_tasks']}")
            click.echo(f"  成功結果: {stats['success_results']}")
            click.echo(f"  エラー結果: {stats['error_results']}")
            click.echo("\\n実際に削除するには --dry-run フラグを外してください。")
        
    except BridgeException as e:
        click.echo(f"❌ クリーンアップエラー: {e}", err=True)
        sys.exit(1)