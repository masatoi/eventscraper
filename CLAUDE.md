# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_hackernews.py
pytest tests/test_reuters_japan.py
pytest tests/test_validation.py

# Run tests with coverage
pytest --cov=src tests/

# Run tests with verbose output
pytest -v tests/
```

### Type Checking
```bash
# Run type checking on all source files
mypy src/ main.py example.py

# Strict type checking (with some warnings ignored)
mypy --strict src/ --ignore-missing-imports

# Check specific file
mypy src/models/data_models.py
```

### Code Quality
```bash
# Format code with Black (required after changes)
black src/ main.py example.py

# Sort imports with isort
isort src/ main.py example.py

# Lint with flake8
flake8 src/ main.py example.py
```

## Running the Application

### Basic Usage
```bash
# Scrape Hacker News (default 30 articles)
python main.py --sites hackernews

# Scrape Reuters Japan markets
python main.py --sites reuters_japan

# Scrape multiple sites
python main.py --sites hackernews reuters_japan

# Specify article limit
python main.py --sites hackernews --limit 10

# Export to different formats
python main.py --sites hackernews --format both

# List available sites
python main.py --list-sites

# Validate scrapers
python main.py --validate --sites hackernews
python main.py --validate  # validate all enabled sites

# Run example
python example.py
```

## Code Architecture

### Core Components

**Scraper Architecture**: The system uses an abstract base class pattern with `BaseScraper` (src/scraper/base.py:14) providing async HTTP session management and common functionality. Site-specific scrapers like `HackerNewsScraper` and `ReutersJapanScraper` inherit from this base.

**Available Scrapers**:
- `HackerNewsScraper`: Uses Firebase API to fetch top stories from Hacker News
- `ReutersJapanScraper`: Parses JavaScript-rendered content from Reuters Japan markets page, extracting article data from Fusion.globalContent JSON structure

**Data Models**: Unified data structures defined in `src/models/data_models.py` using Pydantic:
- `Article`: Unified article/post representation across all sites
- `ScrapingResult`: Container for scraping session results including metadata and error tracking
- `Author` and `Comment`: Supporting models for complete data representation

**Manager Pattern**: `ScraperManager` (src/scraper/manager.py:15) orchestrates parallel scraping across multiple sites, handles site registration, and manages concurrent execution with proper error handling.

**Configuration System**: YAML-based configuration (config/settings.yaml) with `Config` class (src/utils/config.py:11) supporting dot notation access, site-specific settings, and runtime config loading.

**Export System**: Flexible data export through `DataExporter` (src/utils/export.py:16) supporting JSON, CSV, and summary formats with proper datetime serialization.

**Validation System**: Comprehensive scraper validation framework through `ValidationResult` model and base scraper validation methods. Validates connectivity, data fetching, data structure integrity, and site-specific functionality.

### Key Design Patterns

- **Async Context Managers**: All scrapers use async context management for HTTP sessions
- **Parallel Execution**: Multiple sites scraped concurrently using `asyncio.gather()`
- **Error Isolation**: Each site's errors don't affect others; comprehensive error tracking
- **Type Safety**: Full type annotations throughout codebase; mypy compliance required

### Important Implementation Details

- **Path Management**: `sys.path.insert(0, str(Path(__file__).parent / "src"))` in main.py:15 for src module imports
- **HTTP Headers**: Custom User-Agent "EventScraper/1.0 (Educational Purpose)" in base.py:26
- **Logging**: Loguru-based logging with file rotation and structured format
- **Data Validation**: Pydantic models with HttpUrl validation and field validation
- **Scraper Validation**: Four-stage validation process (connectivity, data fetch, data structure, site-specific) with detailed error reporting and timing metrics

## Development Guidelines

- Always run `black` to format code after changes
- Add type annotations to all variables, parameters, and return types
- Run `mypy` after changes to ensure type consistency
- Run `pytest` after changes to verify functionality
- Use async/await patterns for all I/O operations
- Follow the existing error handling patterns with proper logging