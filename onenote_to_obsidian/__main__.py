"""CLI entry point: python -m onenote_to_obsidian"""

import argparse
import logging
import sys

from .config import Config, DEFAULT_VAULT_PATH, DEFAULT_CONFIG_DIR
from .exporter import OneNoteExporter


def main():
    parser = argparse.ArgumentParser(
        description="Экспорт блокнотов OneNote в Obsidian Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Примеры:
  python -m onenote_to_obsidian                  Экспорт всех блокнотов
  python -m onenote_to_obsidian --list           Показать список блокнотов
  python -m onenote_to_obsidian --notebook Asaka Экспорт конкретного блокнота
  python -m onenote_to_obsidian --reset-state    Сброс состояния (ре-экспорт всего)
  python -m onenote_to_obsidian --setup          Настройка кастомного client_id

При первом запуске конфигурация создаётся автоматически.
Регистрация приложения в Azure AD НЕ требуется — используется
публичный client_id Microsoft Office.
""",
    )
    parser.add_argument(
        "--vault",
        type=str,
        default=DEFAULT_VAULT_PATH,
        help="Путь к Obsidian vault (по умолчанию: %(default)s)",
    )
    parser.add_argument(
        "--notebook",
        type=str,
        help="Экспортировать только указанный блокнот (по имени)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Настроить кастомный client_id (только если дефолтный не работает)",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Сбросить состояние экспорта (все страницы будут экспортированы заново)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Показать список доступных блокнотов и выйти",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Подробный вывод (DEBUG-уровень логирования)",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load or create config
    config = Config.load_or_setup(
        vault_path=args.vault,
        config_dir=DEFAULT_CONFIG_DIR,
        force_setup=args.setup,
    )

    if args.setup:
        print("Настройка завершена. Запустите без --setup для экспорта.")
        return

    # Reset state if requested
    if args.reset_state:
        from .state import ExportState

        state = ExportState(config.config_dir_path / "export_state.json")
        state.clear()
        print("Состояние экспорта сброшено. Все страницы будут экспортированы заново.\n")

    # List notebooks mode
    if args.list:
        from .auth import AuthManager
        from .graph_client import GraphClient
        from .onenote_api import OneNoteAPI

        auth = AuthManager(config)
        client = GraphClient(auth)
        api = OneNoteAPI(client)

        print("Блокноты OneNote:\n")
        notebooks = api.list_notebooks()
        if not notebooks:
            print("  (блокноты не найдены)")
            return
        for nb in notebooks:
            api.enumerate_notebook(nb)
            print(f"  {nb.display_name}")
            for section in nb.sections:
                print(f"    └── {section.display_name} ({len(section.pages)} стр.)")
            for sg in nb.section_groups:
                _print_section_group(sg, indent=4)
        return

    # Run export
    exporter = OneNoteExporter(config)
    exporter.export_all(notebook_filter=args.notebook)


def _print_section_group(group, indent=4):
    """Recursively print section group tree."""
    prefix = " " * indent
    print(f"{prefix}└── [{group.display_name}]")
    for section in group.sections:
        print(f"{prefix}    └── {section.display_name} ({len(section.pages)} стр.)")
    for sg in group.section_groups:
        _print_section_group(sg, indent=indent + 4)


if __name__ == "__main__":
    main()
