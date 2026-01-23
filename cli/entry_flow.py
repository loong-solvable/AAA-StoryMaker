#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一入口流程（玩家/开发者共用）

目标：执行流程一致，仅输出信息密度不同。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.settings import settings
from config.cli_config import PlayerConfig, DevConfig
from cli.world_manager import WorldManager, WorldInfo, RuntimeInfo
from cli.player_profile import prompt_player_profile, PlayerProfile
from cli.session_factory import SessionFactory
from utils.exception_handler import handle_exception
from utils.logger import setup_logger, mute_console_handlers
from utils.player_log_filter import setup_player_logging


@dataclass
class EntryModeConfig:
    name: str
    show_details: bool
    log_level: str
    engine_type: str
    max_turns: int


class OutputReporter:
    def __init__(self, mode: EntryModeConfig, logger: Optional[logging.Logger] = None):
        self.mode = mode
        self.logger = logger

    def info(self, message: str) -> None:
        print(message)
        if self.logger:
            self.logger.info(message)

    def detail(self, message: str) -> None:
        if not self.mode.show_details:
            return
        print(message)
        if self.logger:
            self.logger.debug(message)

    def error(self, message: str) -> None:
        print(message)
        if self.logger:
            self.logger.error(message)


def get_mode_config(mode: str) -> EntryModeConfig:
    if mode == "player":
        cfg = PlayerConfig()
        return EntryModeConfig(
            name="player",
            show_details=False,
            log_level=cfg.LOG_LEVEL,
            engine_type=cfg.ENGINE_TYPE,
            max_turns=cfg.DEFAULT_MAX_TURNS,
        )

    cfg = DevConfig()
    return EntryModeConfig(
        name="dev",
        show_details=True,
        log_level=cfg.LOG_LEVEL,
        engine_type=cfg.ENGINE_TYPE,
        max_turns=cfg.DEFAULT_MAX_TURNS,
    )


def setup_mode_logging(mode: str) -> Optional[logging.Logger]:
    if mode == "player":
        setup_player_logging()
        mute_console_handlers()
        return None

    logger = setup_logger("DevEntry", "dev_entry.log")
    logging.getLogger().setLevel(logging.DEBUG)
    return logger


def print_banner(reporter: OutputReporter) -> None:
    reporter.info("")
    reporter.info("=" * 68)
    title = "Infinite Story - 玩家入口" if reporter.mode.name == "player" else "Infinite Story - 开发者入口"
    reporter.info(f"  {title}")
    reporter.info("=" * 68)
    reporter.info("")


def print_main_menu(reporter: OutputReporter) -> None:
    reporter.info("  菜单:")
    if reporter.mode.name == "player":
        reporter.info("    [1] 新故事")
        reporter.info("    [2] 继续故事")
        reporter.info("    [3] 构建世界")
        reporter.info("    [0] 退出")
    else:
        reporter.info("    [1] 新故事 (初始化运行时)")
        reporter.info("    [2] 继续故事 (加载存档)")
        reporter.info("    [3] 从小说构建新世界")
        reporter.info("    [0] 退出")
    reporter.info("")


def print_help(reporter: OutputReporter) -> None:
    reporter.info("")
    reporter.info("  /help   - 帮助")
    reporter.info("  /status - 查看状态")
    reporter.info("  /save   - 保存进度")
    reporter.info("  /quit   - 退出游戏")
    reporter.info("")


def select_world(world_manager: WorldManager, reporter: OutputReporter) -> Optional[WorldInfo]:
    worlds = world_manager.list_available_worlds()

    if not worlds:
        reporter.info("  暂无可用世界")
        return None

    reporter.info("-" * 68)
    reporter.info("  世界列表")
    reporter.info("-" * 68)
    reporter.info("")
    for i, world in enumerate(worlds, 1):
        reporter.info(f"  [{i}] {world.title or world.name}")
        if world.genre:
            reporter.detail(f"      类型: {world.genre} | 角色数: {world.character_count}")
        if world.description:
            reporter.detail(f"      简介: {world.description}")
        reporter.detail(f"      目录: {world.world_dir}")
        reporter.info("")

    reporter.info("  [0] 返回")

    while True:
        try:
            choice = input("  选择世界 > ").strip()
            if choice == "0":
                return None
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(worlds):
                    return worlds[idx]
            reporter.info("  (请输入有效的数字)")
        except (KeyboardInterrupt, EOFError):
            reporter.info("\n  已取消")
            return None


def select_runtime(world_manager: WorldManager, world_name: str, reporter: OutputReporter) -> Optional[RuntimeInfo]:
    runtimes = world_manager.list_runtimes(world_name)

    reporter.info("")
    reporter.info("-" * 68)
    reporter.info(f"  存档列表 - {world_name}")
    reporter.info("-" * 68)
    reporter.info("  [0] 返回")

    if runtimes:
        reporter.info("")
        for i, rt in enumerate(runtimes[:5], 1):
            reporter.info(f"  [{i}] {rt.name}")
            reporter.detail(f"      时间: {rt.initialized_at} | 场景: {rt.current_scene_id}")
            reporter.detail(f"      引擎: {rt.engine_type} | 模型: {rt.llm_model}")
            reporter.detail(f"      目录: {rt.path}")
            reporter.info("")

    while True:
        try:
            choice = input("  选择存档 > ").strip()
            if choice == "0":
                return None
            if choice.isdigit() and runtimes:
                idx = int(choice) - 1
                if 0 <= idx < len(runtimes[:5]):
                    return runtimes[idx]
            reporter.info("  (请输入有效的数字)")
        except (KeyboardInterrupt, EOFError):
            reporter.info("\n  已取消")
            return None


def list_novels(reporter: OutputReporter) -> list[Path]:
    novels_dir = settings.DATA_DIR / "novels"
    if not novels_dir.exists():
        novels_dir.mkdir(parents=True, exist_ok=True)
        reporter.info(f"  已创建小说目录: {novels_dir}")
        return []

    novels = list(novels_dir.glob("*.txt"))
    if not novels:
        reporter.info("  暂无小说文件")
        reporter.info(f"  请将 .txt 小说文件放入: {novels_dir}")
        return []

    reporter.info("-" * 68)
    reporter.info("  小说列表")
    reporter.info("-" * 68)
    for i, novel in enumerate(novels, 1):
        size = novel.stat().st_size / 1024
        reporter.info(f"  [{i}] {novel.name} ({size:.1f} KB)")
    reporter.info("  [0] 返回")
    reporter.info("")

    return novels


def build_world_from_novel(reporter: OutputReporter) -> bool:
    novels = list_novels(reporter)
    if not novels:
        return False

    selected = None
    while True:
        try:
            choice = input("  选择小说 > ").strip()
            if choice == "0":
                return False
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(novels):
                    selected = novels[idx]
                    break
            reporter.info("  (请输入有效的数字)")
        except (KeyboardInterrupt, EOFError):
            reporter.info("\n  已取消")
            return False

    reporter.info("")
    reporter.info(f"  已选择: {selected.name}")
    reporter.info("  正在构建世界，请耐心等待...")

    try:
        from run_world_builder_old import WorldBuilder

        builder = WorldBuilder(
            novel_filename=selected.name,
            world_name=None,
            parallel=True,
        )
        world_dir = builder.run()
        reporter.info("\n  ✓ 世界构建完成")
        reporter.detail(f"  世界目录: {world_dir}")
        return True
    except Exception as e:
        reporter.error(f"\n  ✗ 构建失败: {e}")
        return False


def initialize_new_game(world_name: str, profile: PlayerProfile, reporter: OutputReporter) -> Optional[Path]:
    from initial_Illuminati import IlluminatiInitializer

    reporter.info("")
    reporter.info("  正在初始化世界...")

    try:
        initializer = IlluminatiInitializer(world_name, player_profile=profile.to_dict())
        runtime_dir = initializer.run()

        genesis_path = runtime_dir / "genesis.json"
        with open(genesis_path, "w", encoding="utf-8") as f:
            json.dump(initializer.genesis_data, f, ensure_ascii=False, indent=2)

        reporter.info("  ✓ 初始化完成")
        reporter.detail(f"  运行时目录: {runtime_dir}")
        return runtime_dir
    except Exception as e:
        reporter.error(f"\n  ✗ 初始化失败: {e}")
        return None


def run_game_session(runtime_dir: Path, world_dir: Path, mode: EntryModeConfig, reporter: OutputReporter) -> None:
    if mode.engine_type == "osagent":
        run_osagent_loop(runtime_dir, world_dir, mode, reporter)
        return

    session = SessionFactory.create(
        runtime_dir=runtime_dir,
        world_dir=world_dir,
        engine_type=mode.engine_type,
    )

    try:
        if mode.show_details:
            reporter.detail(f"  [DEV] Engine: {mode.engine_type} | Max turns: {mode.max_turns}")
            reporter.detail(f"  [DEV] Runtime: {runtime_dir}")
            reporter.detail(f"  [DEV] World: {world_dir}")

        if session.can_resume():
            reporter.detail("  检测到可恢复进度，正在恢复...")
            msg = session.resume()
            if msg:
                reporter.info(f"\n  {msg}")
        else:
            reporter.detail("  启动新会话...")
            msg = session.start()
            if msg:
                reporter.info(f"\n  {msg}")

        print_help(reporter)
        turn_count = 0

        while turn_count < mode.max_turns:
            try:
                user_input = input("\n  > ").strip()
                if not user_input:
                    continue

                if user_input.startswith("/"):
                    command = user_input.lower()
                    if command == "/help":
                        print_help(reporter)
                        continue
                    if command == "/status":
                        status = session.get_status()
                        if mode.name == "player":
                            reporter.info(f"\n  场景: {status.scene_id}")
                        else:
                            reporter.info(f"\n  场景: {status.scene_id} | 回合: {status.turn_id}")
                            reporter.info(f"  位置: {status.location} | 时间: {status.current_time}")
                            reporter.detail(f"  角色: {status.present_characters}")
                        continue
                    if command == "/save":
                        save_path = session.save("manual_save", at_boundary=False)
                        reporter.info("\n  已保存")
                        reporter.detail(f"  存档路径: {save_path}")
                        continue
                    if command == "/quit":
                        session.save("autosave", at_boundary=False)
                        reporter.info("\n  已自动保存，退出游戏")
                        return
                    reporter.info("  (未知命令，输入 /help 查看帮助)")
                    continue

                result = session.process_turn(user_input)
                turn_count = result.turn_id or (turn_count + 1)

                if result.error:
                    if mode.name == "player":
                        reporter.error("\n  " + handle_exception(RuntimeError(result.error), "Game"))
                    else:
                        reporter.error(f"\n  [ERROR] {result.error}")
                    continue

                if mode.engine_type == "gameengine" and result.text:
                    reporter.info(f"\n{result.text}")

                if mode.show_details:
                    reporter.detail(f"  [DEV] Scene {result.scene_id} Turn {result.turn_id}")
                    if result.npc_reactions:
                        reporter.detail("  [DEV] NPC Reactions:")
                        reporter.detail(json.dumps(result.npc_reactions, ensure_ascii=False, indent=2))

            except KeyboardInterrupt:
                reporter.info("\n  已请求退出，正在保存...")
                session.save("autosave", at_boundary=False)
                reporter.info("  已保存，退出游戏")
                return
    except Exception as e:
        reporter.error("\n  " + handle_exception(e, "Game session"))


def run_osagent_loop(runtime_dir: Path, world_dir: Path, mode: EntryModeConfig, reporter: OutputReporter) -> None:
    import importlib.util
    from utils.scene_memory import create_scene_memory
    from agents.online.layer3.screen_agent import ScreenAgent
    from utils.progress_tracker import ProgressTracker

    reporter.info("")
    reporter.info("  正在加载场景...")

    try:
        os_file = Path(__file__).parent.parent / "agents" / "online" / "layer1" / "os_agent.py"
        spec = importlib.util.spec_from_file_location("os_agent", os_file)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"无法加载 OS Agent 模块: {os_file}")
        os_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(os_module)

        genesis_path = runtime_dir / "genesis.json"
        if genesis_path.exists():
            os_agent = os_module.OperatingSystem(genesis_path)
        else:
            os_agent = os_module.OperatingSystem()

        world_name = world_dir.name if world_dir else ""
        screen_agent = ScreenAgent(runtime_dir=runtime_dir, world_name=world_name)

        progress_tracker = ProgressTracker()
        progress = progress_tracker.load_progress(runtime_dir)
        current_scene_id = progress.current_scene_id

        def screen_callback(event: str, data: dict) -> None:
            if event == "scene_start":
                screen_agent.render_scene_header(
                    scene_id=data.get("scene_id", current_scene_id),
                    location_name=data.get("location", ""),
                    description=data.get("description", "")
                )
                if mode.show_details:
                    reporter.detail(f"  [DEV] scene_start: {data}")
            elif event in {"dialogue", "player_input"}:
                screen_agent.render_single_dialogue(
                    speaker=data.get("speaker", ""),
                    content=data.get("content", ""),
                    action=data.get("action", ""),
                    emotion=data.get("emotion", ""),
                    is_player=(event == "player_input"),
                )
                if mode.show_details:
                    reporter.detail(f"  [DEV] {event}: {data.get('speaker', '')}")

        def get_user_input(_: str) -> str:
            while True:
                try:
                    prompt = "\n  你的行动 > " if mode.name == "player" else "\n  你的行动 > "
                    user_input = input(prompt).strip()

                    if not user_input:
                        return "look around"

                    if user_input.startswith("/"):
                        command = user_input.lower()
                        if command == "/help":
                            print_help(reporter)
                            continue
                        if command == "/status":
                            if mode.name == "player":
                                reporter.info(f"\n  场景: {current_scene_id}")
                            else:
                                reporter.info(f"\n  场景: {current_scene_id} | 世界: {world_name}")
                            continue
                        if command == "/save":
                            progress_tracker.save_progress(
                                runtime_dir=runtime_dir,
                                current_scene_id=current_scene_id,
                                next_scene_id=current_scene_id + 1,
                                turn_count=0,
                                engine_type="osagent",
                                can_switch_engine=False
                            )
                            reporter.info("\n  💾 进度已保存")
                            continue
                        if command == "/quit":
                            raise KeyboardInterrupt("用户退出")
                        if command == "/skip":
                            return "__SKIP_SCENE__"
                        reporter.info("  (未知命令，输入 /help 查看帮助)")
                        continue

                    return user_input
                except EOFError:
                    raise KeyboardInterrupt("EOF")

        reporter.info("  ✓ 载入完成\n")
        print_help(reporter)

        loop_count = 0
        max_loops = 10

        while loop_count < max_loops:
            init_result = os_agent.ensure_scene_characters_initialized(
                runtime_dir=runtime_dir,
                world_dir=world_dir
            )
            if mode.show_details and isinstance(init_result, dict):
                reporter.detail(f"  [DEV] init_characters: {init_result}")

            try:
                os_agent.dispatch_script_to_actors(runtime_dir)
            except Exception as e:
                if mode.show_details:
                    reporter.detail(f"  [DEV] dispatch_script failed: {e}")

            try:
                loop_result = os_agent.run_scene_loop(
                    runtime_dir=runtime_dir,
                    world_dir=world_dir,
                    max_turns=15,
                    user_input_callback=get_user_input,
                    screen_callback=screen_callback
                )
                if mode.show_details:
                    reporter.detail(f"  [DEV] loop_result: {loop_result}")

            except KeyboardInterrupt:
                reporter.info("\n  退出游戏？(y/n) > ")
                confirm = input().lower()
                if confirm == "y":
                    progress_tracker.save_progress(
                        runtime_dir=runtime_dir,
                        current_scene_id=current_scene_id,
                        next_scene_id=current_scene_id + 1,
                        turn_count=0,
                        engine_type="osagent",
                        can_switch_engine=False
                    )
                    reporter.info("\n  💾 进度已自动保存")
                    reporter.info("  再见！")
                    return
                continue

            if loop_result.get("scene_finished", False):
                reporter.info("")
                reporter.info("  " + "═" * 50)
                reporter.info(f"         ✨ 第 {current_scene_id} 幕 结束 ✨")
                reporter.info("  " + "═" * 50)

                scene_memory = create_scene_memory(runtime_dir, scene_id=current_scene_id)

                try:
                    transition_result = os_agent.process_scene_transition(
                        runtime_dir=runtime_dir,
                        world_dir=world_dir,
                        scene_memory=scene_memory,
                        scene_summary=f"Scene {current_scene_id} completed."
                    )
                    next_scene_id = transition_result.get("next_scene_id") or (current_scene_id + 1)
                    progress_tracker.save_progress(
                        runtime_dir=runtime_dir,
                        current_scene_id=current_scene_id,
                        next_scene_id=next_scene_id,
                        turn_count=0,
                        engine_type="osagent",
                        can_switch_engine=True
                    )
                    current_scene_id = next_scene_id
                    if mode.show_details:
                        reporter.detail(f"  [DEV] transition: {transition_result}")
                except Exception as e:
                    current_scene_id += 1
                    if mode.show_details:
                        reporter.detail(f"  [DEV] transition failed: {e}")

                reporter.info("")
                choice = input("  继续下一幕？(回车继续 / n退出) > ").strip().lower()
                if choice == "n":
                    reporter.info("\n  再见！")
                    return

            loop_count += 1

        reporter.info("")
        reporter.info("  " + "═" * 50)
        reporter.info("         🎭 故事结束 🎭")
        reporter.info("  " + "═" * 50)

    except Exception as e:
        reporter.error("\n  " + handle_exception(e, "OSAgent loop"))


def run_entry(mode: str) -> None:
    mode_config = get_mode_config(mode)
    logger = setup_mode_logging(mode)
    reporter = OutputReporter(mode_config, logger=logger)

    print_banner(reporter)

    world_manager = WorldManager()

    while True:
        print_main_menu(reporter)

        try:
            choice = input("  选择 > ").strip()

            if choice == "0":
                reporter.info("\n  再见！")
                break

            if choice == "1":
                world = select_world(world_manager, reporter)
                if world is None:
                    continue

                profile = prompt_player_profile()
                runtime_dir = initialize_new_game(world.name, profile, reporter)
                if runtime_dir is None:
                    continue

                run_game_session(runtime_dir, world.world_dir, mode_config, reporter)

            elif choice == "2":
                world = select_world(world_manager, reporter)
                if world is None:
                    continue

                runtimes = world_manager.list_runtimes(world.name)
                if not runtimes:
                    reporter.info("\n  该世界暂无存档，请先开始新游戏")
                    continue

                runtime = select_runtime(world_manager, world.name, reporter)
                if runtime is None:
                    continue

                run_game_session(runtime.path, world.world_dir, mode_config, reporter)

            elif choice == "3":
                build_world_from_novel(reporter)

            else:
                reporter.info("\n  (请输入有效的选项)")

        except (KeyboardInterrupt, EOFError):
            reporter.info("\n\n  再见！")
            break
        except Exception as e:
            reporter.error("\n  " + handle_exception(e, "Entry"))
