# OneNote → Obsidian Exporter

## Что это

Python-инструмент для экспорта блокнотов OneNote в Obsidian-совместимый Markdown через Microsoft Graph API. Экспортирует текст, изображения и файловые вложения с сохранением структуры блокнот/секция/страница.

## Структура проекта

```
onenote_to_obsidian/
├── __main__.py              # CLI entry point (python -m onenote_to_obsidian)
├── config.py                # Конфигурация (дефолтный client_id Microsoft Office, без Azure AD)
├── auth.py                  # OAuth2 device code flow через MSAL, кэш токенов, fallback client_id
├── graph_client.py          # HTTP-клиент для Graph API (retry 429/5xx/401, pagination)
├── onenote_api.py           # OneNote endpoints: notebooks, sections, section groups, pages
├── html_converter.py        # OneNote HTML → Markdown (markdownify + BeautifulSoup)
├── resource_downloader.py   # Скачивание картинок/вложений
├── exporter.py              # Главный оркестратор экспорта
├── state.py                 # Состояние экспорта (resume по lastModifiedDateTime)
├── utils.py                 # sanitize_filename, deduplicate_path
└── requirements.txt         # msal, requests, beautifulsoup4, markdownify
```

## Как запускать

```bash
cd ~/Projects
source onenote_to_obsidian/.venv/bin/activate

# Экспорт всех блокнотов (при первом запуске конфиг создаётся автоматически)
python -m onenote_to_obsidian

# Список блокнотов
python -m onenote_to_obsidian --list

# Экспорт конкретного блокнота
python -m onenote_to_obsidian --notebook "Asaka"

# Повторный полный экспорт
python -m onenote_to_obsidian --reset-state

# Настройка кастомного client_id (если дефолтный не работает)
python -m onenote_to_obsidian --setup

# Подробный лог
python -m onenote_to_obsidian -v
```

Регистрация приложения в Azure AD **НЕ требуется**. По умолчанию используется
публичный client_id Microsoft Office (`d3590ed6-52b3-4102-aeff-aad2292ab01c`).
Если он не работает, `--setup` позволяет переключиться на другой (например,
Microsoft Teams: `1fec8e78-bce4-4aaf-ab1b-5451cc387264`).

## Зависимости

Виртуальное окружение: `.venv/` (Python 3.14). Зависимости из `requirements.txt`:
- `msal` — OAuth2 авторизация Microsoft
- `requests` — HTTP-клиент
- `beautifulsoup4` — парсинг HTML
- `markdownify` — HTML→Markdown конвертация

Установка: `source .venv/bin/activate && pip install -r requirements.txt`

## Конфигурация

Хранится в `~/.onenote_exporter/`:
- `config.json` — client_id, vault_path, scopes
- `token_cache.json` — кэш OAuth2 токенов (chmod 600)
- `export_state.json` — какие страницы уже экспортированы

Vault по умолчанию: `/Users/ivankuzmin/Library/Mobile Documents/iCloud~md~obsidian/Documents/NBUClaude`

## Архитектура и ключевые решения

- **Авторизация**: OAuth2 device code flow, authority `https://login.microsoftonline.com/consumers` (личный Microsoft-аккаунт). Дефолтный client_id: Microsoft Office (`d3590ed6-...`), fallback: Microsoft Teams (`1fec8e78-...`). MSAL SerializableTokenCache для persist-а токенов.
- **Graph API**: Retry на 429 (Retry-After), 5xx (exponential backoff), 401 (token refresh). Автопагинация через `@odata.nextLink`.
- **HTML→Markdown**: Кастомный подкласс `markdownify.MarkdownConverter` с переопределёнными `convert_img`, `convert_object`, `convert_p`, `convert_li`, `convert_iframe`. Сигнатуры используют `**kwargs` для совместимости с markdownify >= 1.2.
- **Ресурсы**: Картинки и вложения скачиваются в `attachments/` внутри секции, ссылаются из Markdown как `![alt](attachments/file.png)`.
- **Resume**: Состояние экспорта по page_id + lastModifiedDateTime. Неизменённые страницы пропускаются.
- **Section groups**: Рекурсивный обход вложенных групп секций.

## Результат экспорта

```
Vault/
├── Notebook Name/
│   ├── Section Name/
│   │   ├── attachments/
│   │   │   ├── 0-resourceid.png
│   │   │   └── document.pdf
│   │   ├── Page Title.md
│   │   └── Another Page.md
│   └── Another Section/
│       └── ...
└── Another Notebook/
    └── ...
```

Каждый `.md` содержит YAML frontmatter:
```yaml
---
created: 2023-01-15T10:30:00Z
modified: 2024-06-20T14:22:00Z
source: onenote
onenote_id: "page-guid"
---
```

## Что конвертируется из OneNote HTML

| OneNote HTML | Markdown |
|---|---|
| `<img src="graph.../resources/{id}/$value">` | `![alt](attachments/id.png)` |
| `<object data-attachment="file.pdf">` | `[file.pdf](attachments/file.pdf)` |
| `<p data-tag="to-do">` | `- [ ] текст` |
| `<p data-tag="to-do:completed">` | `- [x] текст` |
| `<iframe data-original-src="...">` | `[Embedded content](url)` |
| `position:absolute` CSS | Удаляется |
| `<b>`, `<i>`, `<h1>`-`<h6>`, `<table>`, `<a>` | Стандартный Markdown |

## Рекомендации по доработке

- При добавлении новых конвертеров тегов — переопределяй метод `convert_<tagname>` в `OneNoteMarkdownConverter` с сигнатурой `(self, el, text, **kwargs)`.
- Тесты конвертера можно запускать передачей sample HTML через `preprocess_onenote_html()` → `convert_page_html()`.
- При изменении Graph API endpoints — править `onenote_api.py`, не `graph_client.py`.
- Не трогать `token_cache.json` вручную — им управляет MSAL.
