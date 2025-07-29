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
from ..mis_integration import MISCommandProcessor, MISMemoryBridge, MISPromptHandler, ContextBridgeSystem
from ..exceptions import BridgeException
from .commands import (
    init_command,
    analyze_command,
    generate_command, 
    status_command,
    clean_command
)
from .performance_commands import register_performance_commands


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
        
        # MIS Integration コンポーネントの初期化
        mis_memory_bridge = MISMemoryBridge()
        mis_command_processor = MISCommandProcessor(mis_memory_bridge)
        context_bridge_system = ContextBridgeSystem(mis_memory_bridge)
        
        # コンテキストに保存
        ctx.obj['bridge_fs'] = bridge_fs
        ctx.obj['registry'] = registry
        ctx.obj['context_loader'] = context_loader
        ctx.obj['task_generator'] = task_generator
        ctx.obj['desktop_connector'] = desktop_connector
        ctx.obj['sync_engine'] = sync_engine
        ctx.obj['mis_memory_bridge'] = mis_memory_bridge
        ctx.obj['mis_command_processor'] = mis_command_processor
        ctx.obj['context_bridge_system'] = context_bridge_system
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


@main.group()
def mis():
    """MIS特殊プロンプト連携コマンド"""
    pass


@main.group()
def context():
    """双方向コンテキスト転送コマンド"""
    pass


@context.command('desktop-to-code')
@click.argument('conversation_content', type=str)
@click.argument('target_project', type=str)
@click.option('--include-code', is_flag=True, default=True, help='コードスニペットを含める')
@click.option('--include-history', is_flag=True, default=True, help='履歴を含める')
@click.option('--output', '-o', type=click.Path(), help='結果出力ファイル')
@click.pass_context
def context_desktop_to_code(ctx, conversation_content, target_project, include_code, include_history, output):
    """Desktop会話コンテキストをCode環境に転送"""
    try:
        context_bridge = ctx.obj['context_bridge_system']
        
        click.echo(f"Transferring Desktop conversation to Code project: {target_project}")
        click.echo(f"Content length: {len(conversation_content)} characters")
        
        # 転送実行
        result = context_bridge.transfer_desktop_to_code(
            conversation_content=conversation_content,
            target_project=target_project,
            include_code_snippets=include_code,
            include_context_history=include_history
        )
        
        # 結果表示
        if result.success:
            click.echo(f"✅ Transfer completed successfully!")
            click.echo(f"Transfer ID: {result.transfer_id}")
            click.echo(f"Items transferred: {len(result.transferred_items)}")
            
            if ctx.obj['verbose']:
                click.echo("\n📦 Transferred items:")
                for i, item in enumerate(result.transferred_items, 1):
                    click.echo(f"  {i}. {item}")
        else:
            click.echo(f"❌ Transfer failed: {result.error_message}", err=True)
            sys.exit(1)
        
        # 結果をファイルに出力
        if output:
            import json
            from dataclasses import asdict
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Transfer result saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: Desktop→Code転送に失敗しました: {e}", err=True)
        sys.exit(1)


@context.command('code-to-desktop')
@click.argument('project_id', type=str)
@click.option('--include-sessions', is_flag=True, default=True, help='最近のセッションを含める')
@click.option('--include-status', is_flag=True, default=True, help='プロジェクト状況を含める')
@click.option('--session-id', help='特定のセッションID')
@click.option('--output', '-o', type=click.Path(), help='結果出力ファイル')
@click.pass_context
def context_code_to_desktop(ctx, project_id, include_sessions, include_status, session_id, output):
    """Code開発状況をDesktop環境に転送"""
    try:
        context_bridge = ctx.obj['context_bridge_system']
        
        click.echo(f"Transferring Code development status to Desktop: {project_id}")
        
        # 転送実行
        result = context_bridge.transfer_code_to_desktop(
            project_id=project_id,
            include_recent_sessions=include_sessions,
            include_project_status=include_status,
            session_id=session_id
        )
        
        # 結果表示
        if result.success:
            click.echo(f"✅ Transfer completed successfully!")
            click.echo(f"Transfer ID: {result.transfer_id}")
            click.echo(f"Items transferred: {len(result.transferred_items)}")
            
            if ctx.obj['verbose']:
                click.echo("\n📦 Transferred items:")
                for i, item in enumerate(result.transferred_items, 1):
                    click.echo(f"  {i}. {item}")
        else:
            click.echo(f"❌ Transfer failed: {result.error_message}", err=True)
            sys.exit(1)
        
        # 結果をファイルに出力
        if output:
            import json
            from dataclasses import asdict
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Transfer result saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: Code→Desktop転送に失敗しました: {e}", err=True)
        sys.exit(1)


@context.command('get-for-code')
@click.argument('project_id', type=str)
@click.option('--types', help='取得するコンテキスト種別（カンマ区切り）')
@click.option('--output', '-o', type=click.Path(), help='結果出力ファイル')
@click.pass_context
def context_get_for_code(ctx, project_id, types, output):
    """Code環境向けの関連コンテキストを取得"""
    try:
        context_bridge = ctx.obj['context_bridge_system']
        
        context_types = types.split(',') if types else None
        click.echo(f"Getting context for Code session: {project_id}")
        if context_types:
            click.echo(f"Context types: {', '.join(context_types)}")
        
        # コンテキスト取得
        context = context_bridge.get_context_for_code_session(project_id, context_types)
        
        # 結果表示
        click.echo(f"\n📋 Context for {project_id}:")
        click.echo(f"Timestamp: {context['timestamp']}")
        
        available_contexts = context.get('available_contexts', {})
        for context_type, items in available_contexts.items():
            click.echo(f"\n🔍 {context_type.replace('_', ' ').title()} ({len(items)} items):")
            for i, item in enumerate(items[:3], 1):  # 最初の3個のみ表示
                if isinstance(item, dict):
                    summary = item.get('summary', item.get('content', str(item)))[:100]
                    timestamp = item.get('timestamp', '')
                    click.echo(f"  {i}. {summary}{'...' if len(summary) == 100 else ''}")
                    if timestamp:
                        click.echo(f"     {timestamp}")
                else:
                    click.echo(f"  {i}. {str(item)[:100]}{'...' if len(str(item)) > 100 else ''}")
            
            if len(items) > 3:
                click.echo(f"     ... and {len(items) - 3} more items")
        
        if context.get('error'):
            click.echo(f"\n⚠️  Error: {context['error']}", err=True)
        
        # 結果をファイルに出力
        if output:
            import json
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(context, f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Context saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: Code向けコンテキスト取得に失敗しました: {e}", err=True)
        sys.exit(1)


@context.command('get-for-desktop')
@click.option('--project-hint', help='プロジェクトヒント')
@click.option('--output', '-o', type=click.Path(), help='結果出力ファイル')
@click.pass_context
def context_get_for_desktop(ctx, project_hint, output):
    """Desktop環境向けの関連コンテキストを取得"""
    try:
        context_bridge = ctx.obj['context_bridge_system']
        
        click.echo("Getting context for Desktop session")
        if project_hint:
            click.echo(f"Project hint: {project_hint}")
        
        # コンテキスト取得
        context = context_bridge.get_context_for_desktop_session(project_hint)
        
        # 結果表示
        click.echo(f"\n📋 Context for Desktop session:")
        click.echo(f"Timestamp: {context['timestamp']}")
        
        available_contexts = context.get('available_contexts', {})
        for context_type, items in available_contexts.items():
            if context_type == 'active_projects':
                click.echo(f"\n🚀 Active Projects ({len(items)}):")
                for project in items:
                    click.echo(f"  • {project}")
            else:
                click.echo(f"\n🔍 {context_type.replace('_', ' ').title()} ({len(items)} items):")
                for i, item in enumerate(items[:3], 1):  # 最初の3個のみ表示
                    if isinstance(item, dict):
                        summary = item.get('summary', item.get('content', str(item)))[:100]
                        project = item.get('project', '')
                        timestamp = item.get('timestamp', '')
                        click.echo(f"  {i}. {summary}{'...' if len(summary) == 100 else ''}")
                        if project:
                            click.echo(f"     Project: {project}")
                        if timestamp:
                            click.echo(f"     {timestamp}")
                    else:
                        click.echo(f"  {i}. {str(item)[:100]}{'...' if len(str(item)) > 100 else ''}")
                
                if len(items) > 3:
                    click.echo(f"     ... and {len(items) - 3} more items")
        
        if context.get('error'):
            click.echo(f"\n⚠️  Error: {context['error']}", err=True)
        
        # 結果をファイルに出力
        if output:
            import json
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(context, f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Context saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: Desktop向けコンテキスト取得に失敗しました: {e}", err=True)
        sys.exit(1)


@mis.command('process')
@click.argument('text', type=str)
@click.option('--project-id', help='プロジェクトID')
@click.option('--output', '-o', type=click.Path(), help='結果出力ファイル')
@click.pass_context
def mis_process(ctx, text, project_id, output):
    """MIS特殊プロンプトを含むテキストを処理"""
    try:
        mis_processor = ctx.obj['mis_command_processor']
        
        click.echo("Processing MIS prompts...")
        result = mis_processor.process_conversation(text, project_id)
        
        # 結果を表示
        click.echo(f"\n🔍 Processing Results:")
        click.echo(f"Status: {result['status']}")
        click.echo(f"Detected prompts: {result['detected_prompts']}")
        click.echo(f"Processed prompts: {result['processed_prompts']}")
        
        if result.get('failed_prompts', 0) > 0:
            click.echo(f"Failed prompts: {result['failed_prompts']}", fg='red')
        
        # Desktop アクションがある場合は表示
        if result.get('desktop_actions'):
            click.echo(f"\n📡 Desktop Actions ({len(result['desktop_actions'])}):")
            for i, action in enumerate(result['desktop_actions'], 1):
                click.echo(f"  {i}. {action['type']}")
        
        # 詳細を表示（verbose モード）
        if ctx.obj['verbose'] and result.get('processing_results'):
            click.echo(f"\n📋 Detailed Results:")
            for i, proc_result in enumerate(result['processing_results'], 1):
                click.echo(f"  {i}. {proc_result['prompt_type']}")
                click.echo(f"     Content: {proc_result['content'][:50]}...")
                if proc_result.get('memory_operation'):
                    mem_op = proc_result['memory_operation']
                    if mem_op['success']:
                        click.echo(f"     Memory: {mem_op['operation']} ✅")
                    else:
                        click.echo(f"     Memory: {mem_op['operation']} ❌")
        
        # 結果をファイルに出力
        if output:
            import json
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Results saved to: {output}")
        
    except Exception as e:
        click.echo(f"Error: MIS処理に失敗しました: {e}", err=True)
        sys.exit(1)


@mis.command('memory')
@click.argument('action', type=click.Choice(['save', 'recall', 'stats', 'export']))
@click.argument('content_or_query', type=str, required=False)
@click.option('--project-id', help='プロジェクトID')
@click.option('--tags', help='タグ（カンマ区切り）')
@click.option('--format', 'export_format', type=click.Choice(['json', 'csv', 'markdown']), 
              default='json', help='エクスポート形式')
@click.option('--output', '-o', type=click.Path(), help='出力ファイル')
@click.pass_context
def mis_memory(ctx, action, content_or_query, project_id, tags, export_format, output):
    """MIS記憶システムの操作"""
    try:
        mis_bridge = ctx.obj['mis_memory_bridge']
        
        if action == 'save':
            if not content_or_query:
                click.echo("Error: 保存する内容を指定してください", err=True)
                sys.exit(1)
            
            tag_list = tags.split(',') if tags else []
            memory_id = mis_bridge.save_memory(
                content=content_or_query,
                tags=tag_list,
                project_id=project_id,
                entry_type="cli_save"
            )
            
            click.echo(f"✅ Memory saved with ID: {memory_id}")
            if tag_list:
                click.echo(f"   Tags: {', '.join(tag_list)}")
            if project_id:
                click.echo(f"   Project: {project_id}")
        
        elif action == 'recall':
            if not content_or_query:
                click.echo("Error: 検索クエリを指定してください", err=True)
                sys.exit(1)
            
            from ..mis_integration.mis_memory_bridge import MISMemoryQuery
            query = MISMemoryQuery(
                query=content_or_query,
                max_results=10,
                project_id=project_id,
                tags=tags.split(',') if tags else None
            )
            
            memories = mis_bridge.recall_memory(query)
            
            click.echo(f"🔍 Found {len(memories)} memories:")
            for i, memory in enumerate(memories, 1):
                click.echo(f"\n{i}. {memory.id}")
                click.echo(f"   Type: {memory.entry_type}")
                click.echo(f"   Time: {memory.timestamp}")
                if memory.tags:
                    click.echo(f"   Tags: {', '.join(memory.tags)}")
                if memory.project_id:
                    click.echo(f"   Project: {memory.project_id}")
                
                # コンテンツの最初の200文字を表示
                content_preview = memory.content[:200]
                if len(memory.content) > 200:
                    content_preview += "..."
                click.echo(f"   Content: {content_preview}")
        
        elif action == 'stats':
            stats = mis_bridge.get_memory_stats()
            
            click.echo("📊 MIS Memory Statistics:")
            click.echo(f"Total memories: {stats['total_memories']}")
            
            if stats['type_distribution']:
                click.echo(f"\nType distribution:")
                for mem_type, count in stats['type_distribution'].items():
                    click.echo(f"  {mem_type}: {count}")
            
            if stats['tag_distribution']:
                click.echo(f"\nTop tags:")
                sorted_tags = sorted(stats['tag_distribution'].items(), 
                                   key=lambda x: x[1], reverse=True)[:10]
                for tag, count in sorted_tags:
                    click.echo(f"  {tag}: {count}")
            
            if stats['project_distribution']:
                click.echo(f"\nProject distribution:")
                for project, count in stats['project_distribution'].items():
                    click.echo(f"  {project}: {count}")
            
            if stats['latest_memory']:
                click.echo(f"\nLatest memory: {stats['latest_memory']}")
            if stats['oldest_memory']:
                click.echo(f"Oldest memory: {stats['oldest_memory']}")
            
            file_size = stats.get('memory_file_size', 0)
            click.echo(f"Memory file size: {file_size:,} bytes")
        
        elif action == 'export':
            if not output:
                output = f"mis_memory_export.{export_format}"
            
            success = mis_bridge.export_memories(Path(output), export_format)
            
            if success:
                click.echo(f"✅ Memories exported to: {output}")
            else:
                click.echo(f"❌ Export failed", err=True)
                sys.exit(1)
        
    except Exception as e:
        click.echo(f"Error: MIS記憶操作に失敗しました: {e}", err=True)
        sys.exit(1)


@mis.command('detect')
@click.argument('text', type=str)
@click.pass_context
def mis_detect(ctx, text):
    """テキスト内のMIS特殊プロンプトを検出"""
    try:
        mis_processor = ctx.obj['mis_command_processor']
        detected_prompts = mis_processor.prompt_handler.detect_mis_prompts(text)
        
        if not detected_prompts:
            click.echo("MIS特殊プロンプトは検出されませんでした")
            return
        
        click.echo(f"🔍 Detected {len(detected_prompts)} MIS prompts:")
        
        for i, (prompt_type, content) in enumerate(detected_prompts, 1):
            click.echo(f"\n{i}. {prompt_type.value}")
            click.echo(f"   Content: {content[:100]}{'...' if len(content) > 100 else ''}")
            
            # プロンプトの種類に応じた説明
            if prompt_type.value == "mis_memory_save":
                click.echo("   Action: 記憶を保存します")
            elif prompt_type.value == "mis_memory_recall":
                click.echo("   Action: 記憶を検索・呼び出します")
            elif prompt_type.value == "mis_spec_update":
                click.echo("   Action: 仕様を更新します")
            elif prompt_type.value == "mis_context_share":
                click.echo("   Action: コンテキストを共有します")
        
    except Exception as e:
        click.echo(f"Error: MIS検出に失敗しました: {e}", err=True)
        sys.exit(1)


# 監視システムコマンドグループ
@main.group()
def monitor():
    """System monitoring and metrics commands"""
    pass


@monitor.command('start-metrics')
@click.option('--interval', default=60, help='Collection interval in seconds')
@click.option('--duration', default=3600, help='Collection duration in seconds')
@click.pass_context
def monitor_start_metrics(ctx, interval: int, duration: int):
    """Start metrics collection"""
    try:
        from ..monitoring import MetricsCollector
        
        collector = MetricsCollector(collection_interval=interval)
        collector.start_collection()
        
        click.echo(f"📊 Metrics collection started (interval: {interval}s)")
        click.echo(f"Collection will run for {duration}s. Press Ctrl+C to stop.")
        
        import time
        try:
            time.sleep(duration)
        except KeyboardInterrupt:
            click.echo("\n⏹️  Collection interrupted by user")
        
        collector.stop_collection()
        click.echo("📊 Metrics collection stopped")
        
    except Exception as e:
        click.echo(f"❌ Error starting metrics collection: {e}", err=True)
        sys.exit(1)


@monitor.command('health')
@click.option('--component', help='Check specific component')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.pass_context
def monitor_health(ctx, component: str, output):
    """Run system health check"""
    try:
        from ..monitoring import HealthChecker
        import asyncio
        import json
        
        checker = HealthChecker()
        
        if component:
            # 特定コンポーネントのみチェック
            click.echo(f"🔍 Checking component: {component}")
            health = checker.check_component(component)
            
            if health is None:
                click.echo(f"❌ Component '{component}' not found")
                available = list(checker.health_checks.keys())
                click.echo(f"Available components: {', '.join(available)}")
                sys.exit(1)
            
            status_emoji = {
                "healthy": "✅",
                "degraded": "⚠️",
                "unhealthy": "❌",
                "unknown": "❓"
            }
            
            emoji = status_emoji.get(health.status.value, "❓")
            click.echo(f"{emoji} {health.name}: {health.message}")
            if health.response_time_ms > 0:
                click.echo(f"   Response time: {health.response_time_ms:.1f}ms")
            
            if health.details and ctx.obj['verbose']:
                click.echo("   Details:")
                for key, value in health.details.items():
                    click.echo(f"     {key}: {value}")
        
        else:
            # 全コンポーネントをチェック
            click.echo("🔍 Running comprehensive health check...")
            
            # 非同期でヘルスチェック実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                health = loop.run_until_complete(checker.check_all_components())
            finally:
                loop.close()
            
            # 結果表示
            status_emoji = {
                "healthy": "✅",
                "degraded": "⚠️", 
                "unhealthy": "❌",
                "unknown": "❓"
            }
            
            emoji = status_emoji.get(health.overall_status.value, "❓")
            click.echo(f"\n{emoji} Overall Status: {health.overall_status.value.upper()}")
            click.echo(f"🕐 Uptime: {health.uptime_seconds:.1f}s")
            click.echo(f"📋 Components checked: {len(health.components)}")
            
            # コンポーネント詳細
            click.echo("\n📊 Component Details:")
            for component in health.components:
                comp_emoji = status_emoji.get(component.status.value, "❓")
                click.echo(f"  {comp_emoji} {component.name}: {component.message}")
                if component.response_time_ms > 0:
                    click.echo(f"    Response time: {component.response_time_ms:.1f}ms")
            
            # アラート
            if health.alerts:
                click.echo(f"\n🚨 Alerts ({len(health.alerts)}):")
                for alert in health.alerts:
                    severity_emoji = "🔴" if alert.get("severity") == "critical" else "🟡"
                    click.echo(f"  {severity_emoji} {alert.get('message', 'No message')}")
            
            # システム情報
            if health.system_info:
                cpu = health.system_info.get('cpu_percent', 0)
                memory_gb = health.system_info.get('memory_available_gb', 0)
                disk_gb = health.system_info.get('disk_free_gb', 0)
                
                click.echo(f"\n💻 System Resources:")
                click.echo(f"  CPU: {cpu:.1f}%")
                click.echo(f"  Available Memory: {memory_gb:.1f}GB")
                click.echo(f"  Free Disk: {disk_gb:.1f}GB")
            
            # 結果をファイルに出力
            if output:
                from dataclasses import asdict
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(asdict(health), f, ensure_ascii=False, indent=2)
                click.echo(f"\n💾 Health check results saved to: {output}")
        
    except Exception as e:
        click.echo(f"❌ Error running health check: {e}", err=True)
        sys.exit(1)


@monitor.command('performance')
@click.option('--operation', help='Filter by operation name')
@click.option('--limit', default=10, help='Number of entries to show')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.pass_context
def monitor_performance(ctx, operation: str, limit: int, output):
    """Show performance statistics"""
    try:
        from ..monitoring import PerformanceMonitor
        import json
        
        monitor = PerformanceMonitor()
        
        if operation:
            # 特定操作の統計
            stats = monitor.get_operation_stats(operation, limit=limit)
            
            if "error" in stats:
                click.echo(f"❌ {stats['error']}")
                return 1
            
            click.echo(f"📈 Performance Stats: {operation}")
            click.echo(f"Total operations: {stats['total_operations']}")
            click.echo(f"Success rate: {stats['success_rate']:.2%}")
            click.echo(f"Average duration: {stats['avg_duration_ms']:.2f}ms")
            click.echo(f"Min/Max duration: {stats['min_duration_ms']:.2f}ms / {stats['max_duration_ms']:.2f}ms")
            click.echo(f"95th percentile: {stats['percentile_95_ms']:.2f}ms")
            click.echo(f"Operations per second: {stats['operations_per_second']:.2f}")
            
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(stats, f, ensure_ascii=False, indent=2)
                click.echo(f"\n💾 Performance stats saved to: {output}")
            
        else:
            # 全操作のサマリー
            summary = monitor.get_all_operations_summary()
            
            click.echo(f"📈 Performance Summary")
            click.echo(f"Total operations: {summary['total_operations']}")
            click.echo(f"Unique operations: {summary['unique_operations']}")
            
            if summary.get('overall_stats'):
                overall = summary['overall_stats']
                click.echo(f"Overall success rate: {overall['overall_success_rate']:.2%}")
                click.echo(f"Average duration: {overall['avg_duration_ms']:.2f}ms")
            
            if summary.get('operations'):
                click.echo(f"\n📊 Top Operations:")
                sorted_ops = sorted(
                    summary['operations'].items(),
                    key=lambda x: x[1]['total_ops'],
                    reverse=True
                )[:limit]
                
                for op_name, op_stats in sorted_ops:
                    click.echo(f"  • {op_name}: {op_stats['total_ops']} ops, "
                              f"{op_stats['success_rate']:.2%} success, "
                              f"{op_stats['avg_duration_ms']:.2f}ms avg")
            
            if output:
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
                click.echo(f"\n💾 Performance summary saved to: {output}")
        
    except Exception as e:
        click.echo(f"❌ Error getting performance stats: {e}", err=True)
        sys.exit(1)


@monitor.command('benchmark')
@click.option('--name', required=True, help='Benchmark name')
@click.option('--operation', required=True, 
              type=click.Choice(['file_write', 'file_read', 'memory_allocation', 'cpu_calculation']),
              help='Operation to benchmark')
@click.option('--iterations', default=100, help='Number of iterations')
@click.option('--concurrent/--sequential', default=False, help='Run concurrent benchmark')
@click.option('--output', '-o', type=click.Path(), help='Output file for results')
@click.pass_context
def monitor_benchmark(ctx, name: str, operation: str, iterations: int, concurrent: bool, output):
    """Run performance benchmark"""
    try:
        from ..monitoring import PerformanceMonitor
        import asyncio
        import json
        from dataclasses import asdict
        
        monitor = PerformanceMonitor()
        
        # ベンチマーク対象の操作を定義
        benchmark_operations = {
            "file_write": lambda: Path("benchmark_test.txt").write_text("test"),
            "file_read": lambda: Path("benchmark_test.txt").read_text() if Path("benchmark_test.txt").exists() else "",
            "memory_allocation": lambda: [i for i in range(1000)],
            "cpu_calculation": lambda: sum(i * i for i in range(1000))
        }
        
        click.echo(f"🏃 Running benchmark: {name}")
        click.echo(f"Operation: {operation}")
        click.echo(f"Iterations: {iterations}")
        click.echo(f"Mode: {'Concurrent' if concurrent else 'Sequential'}")
        
        # ベンチマーク実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                monitor.run_benchmark(
                    name=name,
                    operation_func=benchmark_operations[operation],
                    iterations=iterations,
                    concurrent=concurrent
                )
            )
        finally:
            loop.close()
        
        # 結果表示
        click.echo(f"\n📊 Benchmark Results: {name}")
        click.echo(f"Total operations: {result.total_operations}")
        click.echo(f"Successful: {result.successful_operations}")
        click.echo(f"Failed: {result.failed_operations}")
        click.echo(f"Success rate: {(result.successful_operations / result.total_operations):.2%}")
        click.echo(f"Total time: {result.total_duration_ms:.2f}ms")
        click.echo(f"Average time: {result.avg_duration_ms:.2f}ms")
        click.echo(f"Min/Max time: {result.min_duration_ms:.2f}ms / {result.max_duration_ms:.2f}ms")
        click.echo(f"95th percentile: {result.percentile_95_ms:.2f}ms")
        click.echo(f"Operations per second: {result.operations_per_second:.2f}")
        
        # クリーンアップ
        test_file = Path("benchmark_test.txt")
        if test_file.exists():
            test_file.unlink()
        
        # 結果をファイルに出力
        if output:
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(asdict(result), f, ensure_ascii=False, indent=2)
            click.echo(f"\n💾 Benchmark results saved to: {output}")
        
    except Exception as e:
        click.echo(f"❌ Error running benchmark: {e}", err=True)
        sys.exit(1)


@monitor.command('export')
@click.option('--output', default='metrics_export.json', help='Output file path')
@click.option('--format', default='json', type=click.Choice(['json', 'csv']), help='Export format')
@click.option('--type', 'export_type', type=click.Choice(['metrics', 'performance', 'all']), 
              default='all', help='Data type to export')
@click.pass_context
def monitor_export(ctx, output: str, format: str, export_type: str):
    """Export monitoring data"""
    try:
        from ..monitoring import MetricsCollector, PerformanceMonitor
        
        output_path = Path(output)
        success = False
        
        if export_type in ['metrics', 'all']:
            collector = MetricsCollector()
            success = collector.export_metrics(output_path, format)
            
            if success:
                click.echo(f"✅ Metrics exported to {output_path}")
        
        if export_type in ['performance', 'all']:
            # パフォーマンスデータの場合は別ファイル名
            if export_type == 'performance':
                perf_output = output_path
            else:
                perf_output = output_path.with_stem(f"{output_path.stem}_performance")
            
            monitor = PerformanceMonitor()
            success = monitor.export_performance_data(perf_output, format)
            
            if success:
                click.echo(f"✅ Performance data exported to {perf_output}")
        
        if not success:
            click.echo(f"❌ Failed to export monitoring data")
            sys.exit(1)
            
    except Exception as e:
        click.echo(f"❌ Error exporting monitoring data: {e}", err=True)
        sys.exit(1)


# パフォーマンスコマンドを登録
register_performance_commands(main)

if __name__ == '__main__':
    main()