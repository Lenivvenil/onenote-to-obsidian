"""CLI entry point: python -m onenote_to_obsidian"""

from __future__ import annotations

import argparse
import logging

logger = logging.getLogger(__name__)

import sys

from .config import DEFAULT_CONFIG_DIR, DEFAULT_VAULT_PATH, Config
from .exporter import OneNoteExporter
from .graph_client import GraphAPIError
from .onenote_api import SectionGroup


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export OneNote notebooks to Obsidian Markdown",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python -m onenote_to_obsidian                  Export all notebooks
  python -m onenote_to_obsidian --list           List available notebooks
  python -m onenote_to_obsidian --notebook Asaka Export a specific notebook
  python -m onenote_to_obsidian --reset-state    Reset state (re-export everything)
  python -m onenote_to_obsidian --setup          Configure custom client_id

Configuration is created automatically on first run.
No Azure AD app registration required — uses a public
Microsoft Office client_id by default.
""",
    )
    parser.add_argument(
        "--vault",
        type=str,
        default=DEFAULT_VAULT_PATH,
        help="Path to Obsidian vault (default: %(default)s)",
    )
    parser.add_argument(
        "--notebook",
        type=str,
        help="Export only the specified notebook (by name)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Configure custom client_id (only if default doesn't work)",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Reset export state (all pages will be re-exported)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available notebooks and exit",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output (DEBUG-level logging)",
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
        print("Setup complete. Run without --setup to start exporting.")
        return

    # Reset state if requested
    if args.reset_state:
        from .state import ExportState

        state = ExportState(config.config_dir_path / "export_state.json")
        state.clear()
        print("Export state cleared. All pages will be re-exported.\n")

    try:
        # List notebooks mode
        if args.list:
            from .auth import AuthManager
            from .graph_client import GraphClient
            from .onenote_api import OneNoteAPI

            auth = AuthManager(config)
            client = GraphClient(auth)
            api = OneNoteAPI(client)

            print("OneNote Notebooks:\n")
            notebooks = api.list_notebooks()
            if not notebooks:
                print("  (no notebooks found)")
                return
            for nb in notebooks:
                api.enumerate_notebook(nb)
                print(f"  {nb.display_name}")
                for section in nb.sections:
                    print(f"    └── {section.display_name} ({len(section.pages)} pages)")
                for sg in nb.section_groups:
                    _print_section_group(sg, indent=4)
            return

        # Run export
        exporter = OneNoteExporter(config)
        exporter.export_all(notebook_filter=args.notebook)
    except KeyboardInterrupt:
        print("\nExport cancelled.")
        sys.exit(130)
    except GraphAPIError as e:
        logger.debug("GraphAPIError: %s", e, exc_info=True)
        print(f"\nAPI error: {e}")
        print("Run with --verbose for details.")
        sys.exit(1)
    except OSError as e:
        logger.debug("OSError: %s", e, exc_info=True)
        print(f"\nFile system error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.debug("Unexpected error: %s", e, exc_info=True)
        print(f"\nUnexpected error: {e}")
        print("Run with --verbose for details.")
        sys.exit(1)


def _print_section_group(group: SectionGroup, indent: int = 4) -> None:
    """Recursively print section group tree."""
    prefix = " " * indent
    print(f"{prefix}└── [{group.display_name}]")
    for section in group.sections:
        print(f"{prefix}    └── {section.display_name} ({len(section.pages)} pages)")
    for sg in group.section_groups:
        _print_section_group(sg, indent=indent + 4)


if __name__ == "__main__":
    main()
