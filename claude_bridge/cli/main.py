"""
Claude Bridge System - CLI Main Entry Point
メインCLIエントリーポイント
"""

import click
import logging
import sys
from pathlib import Path

from ..core import BridgeFileSystem, ProjectRegistry, ProjectContextLoader, TaskGenerator
from ..desktop_api import DesktopConnector, SyncEngine, BridgeProtocol
from ..exceptions import BridgeException
from .commands import (
    init_command,
    analyze_command,
    generate_command, 
    status_command,
    clean_command
)


def setup_logging(level: str = "INFO") -> None:
    """ログ設定の初期化"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='詳細ログを表示')
@click.option('--quiet', '-q', is_flag=True, help='エラーのみ表示')
@click.option('--bridge-root', type=click.Path(), help='Bridgeルートディレクトリ')
@click.pass_context
def main(ctx, verbose, quiet, bridge_root):
    """
    Claude Bridge System CLI
    
    Claude Code CLIとClaude Desktopの統合連携システム
    """
    # ログレベル設定
    if quiet:
        log_level = "ERROR"
    elif verbose:
        log_level = "DEBUG"
    else:
        log_level = "INFO"
    
    setup_logging(log_level)
    
    # コンテキストオブジェクトの初期化
    ctx.ensure_object(dict)
    
    try:
        # コアコンポーネントの初期化
        bridge_fs = BridgeFileSystem(bridge_root) if bridge_root else BridgeFileSystem()
        registry = ProjectRegistry()
        context_loader = ProjectContextLoader(registry)
        task_generator = TaskGenerator(context_loader, bridge_fs)
        
        # Desktop API コンポーネントの初期化
        desktop_connector = DesktopConnector()
        sync_engine = SyncEngine(bridge_fs, registry, desktop_connector)
        
        # コンテキストに保存
        ctx.obj['bridge_fs'] = bridge_fs
        ctx.obj['registry'] = registry
        ctx.obj['context_loader'] = context_loader
        ctx.obj['task_generator'] = task_generator
        ctx.obj['desktop_connector'] = desktop_connector
        ctx.obj['sync_engine'] = sync_engine
        ctx.obj['verbose'] = verbose
        
    except Exception as e:
        click.echo(f"Error: 初期化に失敗しました: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--force', is_flag=True, help='既存設定を上書き')
@click.pass_context
def init(ctx, force):
    """システムの初期化"""
    init_command(ctx, force)


@main.command()
@click.argument('content', type=str)
@click.option('--projects', '-p', multiple=True, help='対象プロジェクト指定')
@click.option('--format', 'output_format', 
              type=click.Choice(['json', 'yaml', 'markdown']), 
              default='markdown', help='出力形式')
@click.pass_context  
def analyze(ctx, content, projects, output_format):
    """会話内容の分析"""
    analyze_command(ctx, content, list(projects), output_format)


@main.command()
@click.argument('content', type=str)
@click.option('--projects', '-p', multiple=True, help='対象プロジェクト指定')
@click.option('--output', '-o', type=click.Path(), help='出力ファイルパス')
@click.option('--metadata', type=str, help='追加メタデータ（JSON形式）')
@click.pass_context
def generate(ctx, content, projects, output, metadata):
    """タスクファイルの生成"""
    generate_command(ctx, content, list(projects), output, metadata)


@main.command()
@click.option('--detailed', is_flag=True, help='詳細情報を表示')
@click.pass_context
def status(ctx, detailed):
    """システム状態の確認"""
    status_command(ctx, detailed)


@main.command()
@click.option('--days', type=int, default=7, help='保持日数')
@click.option('--dry-run', is_flag=True, help='実行せずに表示のみ')
@click.confirmation_option(prompt='古いファイルを削除しますか？')
@click.pass_context
def clean(ctx, days, dry_run):
    """古いファイルのクリーンアップ"""
    clean_command(ctx, days, dry_run)


@main.group()
def project():
    """プロジェクト管理コマンド"""
    pass


@project.command('list')
@click.option('--active-only', is_flag=True, help='アクティブなプロジェクトのみ')
@click.pass_context
def project_list(ctx, active_only):
    """プロジェクト一覧表示"""
    try:
        registry = ctx.obj['registry']
        projects = registry.list_projects(active_only)
        
        if not projects:
            click.echo("プロジェクトが見つかりませんでした。")
            return
        
        click.echo(f"\\n{'アクティブな' if active_only else ''}プロジェクト一覧:")
        click.echo("-" * 50)
        
        for project_id, config in projects.items():
            status = "🟢" if config.active else "🔴"
            click.echo(f"{status} {config.shortcut} {config.name}")
            if ctx.obj['verbose']:
                click.echo(f"   Path: {config.path}")
                click.echo(f"   Tech: {', '.join(config.tech_stack)}")
                click.echo()
        
    except BridgeException as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@project.command('show')
@click.argument('project_id', type=str)
@click.pass_context
def project_show(ctx, project_id):
    """プロジェクト詳細表示"""
    try:
        context_loader = ctx.obj['context_loader']
        context = context_loader.load_project_context(project_id)
        
        basic_info = context['basic_info']
        claude_md = context['claude_md_content']
        structure = context['project_structure']
        related = context['related_projects']
        
        click.echo(f"\\n📁 {basic_info['name']} {basic_info['shortcut']}")
        click.echo("=" * 50)
        click.echo(f"説明: {basic_info['description']}")
        click.echo(f"パス: {basic_info['path']}")
        click.echo(f"技術スタック: {', '.join(basic_info['tech_stack'])}")
        click.echo(f"アクティブ: {'Yes' if basic_info['active'] else 'No'}")
        
        if claude_md['status'] == 'success':
            click.echo(f"\\nClaude.md要約: {claude_md['summary']}")
        
        if structure['status'] == 'success':
            click.echo(f"\\nプロジェクト構造:")
            click.echo(f"  ファイル数: {structure['total_files']}")
            click.echo(f"  Pythonファイル: {len(structure['python_files'])}")
            click.echo(f"  ディレクトリ: {len(structure['directories'])}")
        
        if related:
            click.echo(f"\\n関連プロジェクト:")
            for rel_id, rel_info in related.items():
                click.echo(f"  • {rel_info['name']} ({rel_info['relationship_type']})")
        
    except BridgeException as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.group()
def task():
    """タスク管理コマンド"""
    pass


@task.command('list')
@click.option('--status', type=click.Choice(['pending', 'processing', 'completed']),
              help='ステータスでフィルタ')
@click.pass_context
def task_list(ctx, status):
    """タスク一覧表示"""
    try:
        bridge_fs = ctx.obj['bridge_fs']
        
        if not status or status == 'pending':
            pending_tasks = bridge_fs.list_pending_tasks()
            if pending_tasks:
                click.echo("\\n📋 未処理タスク:")
                click.echo("-" * 30)
                for task in pending_tasks:
                    click.echo(f"• {task['file_path'].name}")
                    click.echo(f"  プロジェクト: {task['project_id']}")
                    click.echo(f"  作成日時: {task['created_at']}")
                    click.echo()
        
        # システム統計も表示
        stats = bridge_fs.get_system_stats()
        click.echo(f"\\n統計情報:")
        click.echo(f"  未処理: {stats['pending_tasks']}")
        click.echo(f"  処理中: {stats['processing_tasks']}")
        click.echo(f"  完了: {stats['completed_tasks']}")
        
    except BridgeException as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.group()
def desktop():
    """Desktop API連携コマンド"""
    pass


@desktop.command('connect')
@click.option('--url', default='ws://localhost:8765', help='WebSocket URL')
@click.option('--timeout', default=30, help='接続タイムアウト（秒）')
@click.pass_context
def desktop_connect(ctx, url, timeout):
    """Claude Desktopに接続"""
    try:
        desktop_connector = ctx.obj['desktop_connector']
        desktop_connector.websocket_url = url
        desktop_connector.connection_timeout = timeout
        
        click.echo(f"Connecting to Claude Desktop at {url}...")
        
        import asyncio
        success = asyncio.run(desktop_connector.connect())
        
        if success:
            click.echo("✅ Successfully connected to Claude Desktop!")
            
            # 接続状態表示
            status = desktop_connector.get_connection_status()
            click.echo(f"Connection uptime: {status.get('uptime_seconds', 0):.1f}s")
            click.echo(f"Active handlers: {len(status.get('active_handlers', {}))}")
        else:
            click.echo("❌ Failed to connect to Claude Desktop", err=True)
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"Error: 接続に失敗しました: {e}", err=True)
        sys.exit(1)


@desktop.command('disconnect')
@click.pass_context
def desktop_disconnect(ctx):
    """Claude Desktopから切断"""
    try:
        desktop_connector = ctx.obj['desktop_connector']
        
        if not desktop_connector.is_connected:
            click.echo("Claude Desktopに接続されていません")
            return
        
        click.echo("Disconnecting from Claude Desktop...")
        
        import asyncio
        asyncio.run(desktop_connector.disconnect())
        
        click.echo("✅ Successfully disconnected from Claude Desktop")
        
    except Exception as e:
        click.echo(f"Error: 切断に失敗しました: {e}", err=True)
        sys.exit(1)


@desktop.command('status')
@click.pass_context
def desktop_status(ctx):
    """Desktop連携状態確認"""
    try:
        desktop_connector = ctx.obj['desktop_connector']
        sync_engine = ctx.obj['sync_engine']
        
        # Desktop Connector 状態
        conn_status = desktop_connector.get_connection_status()
        click.echo("🖥️  Desktop Connector Status:")
        click.echo(f"  Connection: {'🟢 Connected' if conn_status['is_connected'] else '🔴 Disconnected'}")
        click.echo(f"  URL: {conn_status['websocket_url']}")
        
        if conn_status['is_connected']:
            click.echo(f"  Uptime: {conn_status.get('uptime_seconds', 0):.1f}s")
            click.echo(f"  Messages sent: {conn_status['connection_stats']['messages_sent']}")
            click.echo(f"  Messages received: {conn_status['connection_stats']['messages_received']}")
            click.echo(f"  Active handlers: {len(conn_status['active_handlers'])}")
        
        # Sync Engine 状態
        sync_status = sync_engine.get_sync_status()
        click.echo("\\n🔄 Sync Engine Status:")
        click.echo(f"  Status: {'🟢 Running' if sync_status['is_running'] else '🔴 Stopped'}")
        click.echo(f"  Sync interval: {sync_status['sync_interval']}s")
        click.echo(f"  Conflict resolution: {sync_status['conflict_resolution']}")
        click.echo(f"  Watched paths: {sync_status['watched_paths_count']}")
        click.echo(f"  Tracked files: {sync_status['tracked_files_count']}")
        
        if sync_status.get('uptime_seconds'):
            click.echo(f"  Uptime: {sync_status['uptime_seconds']:.1f}s")
        
        # 同期統計
        stats = sync_status['sync_stats']
        click.echo("\\n📊 Sync Statistics:")
        click.echo(f"  Files synced: {stats['files_synced']}")
        click.echo(f"  Conflicts detected: {stats['conflicts_detected']}")
        click.echo(f"  Conflicts resolved: {stats['conflicts_resolved']}")
        click.echo(f"  Sync errors: {stats['sync_errors']}")
        
        if stats['last_sync_time']:
            click.echo(f"  Last sync: {stats['last_sync_time']}")
        
    except Exception as e:
        click.echo(f"Error: 状態取得に失敗しました: {e}", err=True)
        sys.exit(1)


@desktop.command('sync')
@click.option('--start', 'action', flag_value='start', help='同期エンジン開始')
@click.option('--stop', 'action', flag_value='stop', help='同期エンジン停止')
@click.option('--restart', 'action', flag_value='restart', help='同期エンジン再起動')
@click.pass_context
def desktop_sync(ctx, action):
    """同期エンジン制御"""
    try:
        sync_engine = ctx.obj['sync_engine']
        
        import asyncio
        
        if action == 'start':
            if sync_engine.is_running:
                click.echo("同期エンジンは既に動作中です")
                return
            
            click.echo("Starting sync engine...")
            asyncio.run(sync_engine.start())
            click.echo("✅ Sync engine started successfully")
            
        elif action == 'stop':
            if not sync_engine.is_running:
                click.echo("同期エンジンは停止中です")
                return
            
            click.echo("Stopping sync engine...")
            asyncio.run(sync_engine.stop())
            click.echo("✅ Sync engine stopped successfully")
            
        elif action == 'restart':
            click.echo("Restarting sync engine...")
            if sync_engine.is_running:
                asyncio.run(sync_engine.stop())
            asyncio.run(sync_engine.start())
            click.echo("✅ Sync engine restarted successfully")
            
        else:
            click.echo("アクション指定が必要です: --start, --stop, または --restart")
            sys.exit(1)
        
    except Exception as e:
        click.echo(f"Error: 同期エンジン制御に失敗しました: {e}", err=True)
        sys.exit(1)


@desktop.command('notify')
@click.argument('message', type=str)
@click.option('--title', default='Claude Bridge', help='通知タイトル')
@click.option('--level', type=click.Choice(['info', 'warning', 'error']), 
              default='info', help='通知レベル')
@click.pass_context
def desktop_notify(ctx, message, title, level):
    """Claude Desktopに通知送信"""
    try:
        desktop_connector = ctx.obj['desktop_connector']
        
        if not desktop_connector.is_connected:
            click.echo("Claude Desktopに接続されていません。先に 'desktop connect' を実行してください。", err=True)
            sys.exit(1)
        
        click.echo(f"Sending notification to Claude Desktop...")
        
        import asyncio
        response = asyncio.run(desktop_connector.send_notification(title, message, level))
        
        click.echo("✅ Notification sent successfully")
        
        if response:
            click.echo(f"Response: {response.payload.get('status', 'No response')}")
        
    except Exception as e:
        click.echo(f"Error: 通知送信に失敗しました: {e}", err=True)
        sys.exit(1)


@desktop.command('switch-project')
@click.argument('project_id', type=str)
@click.pass_context
def desktop_switch_project(ctx, project_id):
    """プロジェクト切り替えをDesktopに通知"""
    try:
        desktop_connector = ctx.obj['desktop_connector']
        context_loader = ctx.obj['context_loader']
        
        if not desktop_connector.is_connected:
            click.echo("Claude Desktopに接続されていません。先に 'desktop connect' を実行してください。", err=True)
            sys.exit(1)
        
        # プロジェクトコンテキスト取得
        click.echo(f"Loading project context for {project_id}...")
        context = context_loader.load_project_context(project_id)
        
        # Desktop に通知
        click.echo(f"Notifying Claude Desktop of project switch...")
        
        import asyncio
        response = asyncio.run(desktop_connector.send_project_switch(project_id, context))
        
        click.echo(f"✅ Project switch notification sent for {project_id}")
        
        if response:
            click.echo(f"Response: {response.payload.get('status', 'No response')}")
        
    except BridgeException as e:
        click.echo(f"Error: プロジェクト切り替えに失敗しました: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: 予期しないエラーが発生しました: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()