# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Guten.AI is a modular EPUB editor built with Python, GTK4, and libadwaita. It provides a modern interface for editing ebook files with real-time preview capabilities and AI-powered text correction features.

## Commands

### Running the Application
```bash
# Main entry point
python3 main.py

# Using the provided shell script (with virtual environment)
./run_gutenai.sh

# Legacy script (uses WebKit environment variable)
./run.sh
```

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m unittest discover tests/

# Individual component testing (as per README)
python -m components.sidebar_left
python -m components.editor_panel
python -m components.sidebar_right
```

## Architecture

### Core Components

1. **GutenCore** (`core/guten_core.py`) - Central EPUB management system
   - Single source of truth for EPUB state
   - Manages workspace directory (workdir) and OPF metadata
   - Uses ebooklib for packaging/importing
   - Maintains ElementTree for OPF manipulation
   - Does NOT handle link rewriting during file moves/renames

2. **GTK UI Layer** (`gtk_ui/`)
   - **MainWindow** (`main_window.py`) - Application coordinator using Adw.ApplicationWindow
   - **SidebarLeft** (`sidebar_left.py`) - EPUB structure navigation tree
   - **CentralEditor** (`central_editor.py`) - Multi-mode content editor (HTML/CSS/images)
   - **SidebarRight** (`sidebar_right.py`) - Real-time WebKit preview panel
   - **ActionManager** (`actions.py`) - Centralized action handling
   - **DialogManager** (`dialogs.py`) - Modal dialog management

### Key Design Principles

- **Single Core Pattern**: All UI components interact exclusively with GutenCore
- **Modular Architecture**: Independent, testable components
- **Signal-based Communication**: Uses GObject signals for component coordination
- **Workspace-based**: Operates on extracted EPUB directory structure
- **OPF as Source of Truth**: Maintains manifest/spine/metadata consistency

### File Structure Patterns

- `main.py` - Application entry point, sets up GTK4/Adw and launches GutenAIApplication
- `core/` - Business logic and EPUB management
- `gtk_ui/` - GTK4/libadwaita UI components
- `utils/` - Shared utilities (currently minimal)
- `tests/` - Unit tests (currently basic structure)

## Dependencies

- **Python 3.8+** (project uses Python 3.13)
- **PyGObject 3.42+** - GTK4 bindings
- **ebooklib 0.18+** - EPUB manipulation
- **GTK4 + libadwaita** - Modern GNOME UI toolkit
- **WebKit2** - HTML preview (optional, with WEBKIT_DISABLE_COMPOSITING_MODE=1)

## Development Notes

### Testing Strategy
- Each component designed for independent testing
- Current test suite is minimal (`tests/test_main.py` is a template)
- README suggests running individual components with `python -m` pattern

### UI Framework
- Uses GTK4 with libadwaita for modern GNOME styling
- Requires `gi.require_version('Gtk', '4.0')` and `gi.require_version('Adw', '1')`
- WebKit preview may need environment variable workaround

### Core Limitations
- Link rewriting not implemented (shows warnings via hooks)
- Basic invariants maintained: all files in manifest, documents optionally in spine
- Uses ElementTree for XML manipulation rather than specialized EPUB parsers

## AI Features

The project includes AI-powered text correction capabilities:
- Gemini-based text correction (`gtk_ui/gemini_corrector.py`)
- Correction modal interface (`gtk_ui/correction_modal.py`)
- Integration with the main editing workflow