# Development

Проект состоит из проверенного PowerShell-движка и необязательной PySide6 GUI-оболочки. В GUI есть локальный пятиминутный монитор текущего маршрута; внешних сервисов, планировщиков и provider keys нет.

- `OpenCodeRouter.ps1`: argument validation, menu, shared named mutex, cache, presentation and exit codes.
- `Router.Core.psm1`: controller, HTTPS diagnostics, health classification, transactional selector operations. При импорте модуль принудительно задаёт UTF-8 для stdin/stdout PowerShell: без этого `pwsh`, запущенный через GUI `QProcess` без терминала, использует OEM code page и необратимо портит кириллицу/emoji в JSON.
- `OpenCodeRouter.pyw`: тонкая Windows GUI entrypoint с защитным перезапуском через `.venv\Scripts\pythonw.exe` из корня проекта, даже если VS Code вызвал глобальный `python.exe`.
- `app/core/`: настройки, локализация и координация GUI.
- `app/services/router_process.py`: неблокирующий запуск существующего CLI через `QProcess` и разбор JSON.
- `app/services/ui_scale_service.py`: чистые формулы автоматического DPI-масштаба и пользовательской поправки.
- `app/ui/`: главное окно, каркас виджетов, сигналы, явная сортировка таблицы, реестр SVG-иконок, системный трей и масштабируемая QSS-тема One Dark Pro.
- `Build_Tools/`: воспроизводимая PyInstaller onedir-сборка, fail-closed аудит DLL, post-build manifest, Inno Setup installer и portable deploy.
- `NamedPipeHttp.cs`: .NET HttpClient transport over local existing Mihomo pipe; dynamically compiled in memory by Add-Type. TCP transport is also supported for explicitly configured localhost controllers.

## Routing contract

The integration adds one process rule, a select group of concrete nodes and a localhost diagnostic listener. Existing rules retain their order; the process rule position determines priority. See docs/CLASH_SETUP.en.md for profile setup.

Controller transport is configured explicitly: a Windows named pipe, or an enabled localhost TCP API. Router does not enable a controller or restart the core. Controller mutations verify selector state after PUT.

For the legacy `controllerPipe: verge-mihomo`, Router reads `external-controller-pipe` from `secretSource` on every request. Clash Verge 2.5.5 uses an owner-specific pipe whose name also depends on core mode. Local `\\.\pipe\` prefixes are normalized; explicit custom pipes remain unchanged, and remote pipe paths are rejected. Missing/empty runtime pipe fields preserve compatibility with older Clash versions. No TCP fallback or controller configuration mutation is performed.

Health requests use new HTTP clients per node and one cancellation deadline. Parallel IP fallbacks stop when one IPv4 succeeds and all API requests finish. Redirects are not followed, TLS certificate validation stays enabled. Endpoints are credential-free probes; auth usability is not tested. Recognized geographical error text fails even inside JSON.

Auto scans concrete nodes serially, each node's requests in parallel. Normal auto filters failures, applies name preferences/latency, improvement threshold and healthy-route cooldown, then rechecks the final selection. `-DifferentIp` is a distinct cyclic mode: it sorts allowed nodes by the Russian location portion of each name (ignoring a leading flag or country code), starts after the current node, wraps only after the last node, and commits the first healthy result whose IPv4 differs from the baseline. When the failed baseline has no measurable IP, the first subsequent healthy result is accepted. Both modes restore the original selection through `finally` when no candidate can be committed. A controller failure may prevent physical restoration and is surfaced.

После успешного окончательного изменения selector функция `Disconnect-OpenCodeConnections` получает `/connections`, оставляет только записи `opencode.exe`, чья `chains` содержит `OpenCode-Location`, и закрывает каждую через `DELETE /connections/{id}`. Это вынуждает OpenCode переподключиться через новый outbound и не затрагивает другие процессы или подключения OpenCode из другой группы. Разрыв выполняется только для committed `use`/`auto`/`-DifferentIp`; временные `test` и `scan` его не вызывают.

Команда `scan` и кнопка «Все узлы» последовательно измеряют каждый разрешённый узел по русскому названию (без ведущего флага), начиная с первого по алфавиту независимо от порядка подписки и текущего маршрута. Результаты записываются в кэш; исходный selector всегда возвращается через `finally`. В отличие от `auto`, полный тест не выбирает лучший маршрут и не меняет текущий выбор после завершения.

`Test-RouterNodeExcluded` и `Get-AllowedRouterNodes` автоматически исключают Россию по флагу, названиям страны и отдельным кодам RU/RUS; `excludedNodes` добавляет запрещённые точные имена. Эти узлы отсутствуют в list/menu, не попадают в scan/auto и отклоняются для ручных `use`/`test`. Это фильтр имён подписки, не геолокация IP. Низкоуровневый `Set-RouterNode` сохраняет возможность транзакционно восстановить исходный selector, даже если исходный узел позднее оказался в исключениях. По умолчанию `excludedNodes` пуст.

## UI contract

При каждом запуске таблица сортируется по столбцу «Узел» по возрастанию русской
части названия. Заголовок сразу показывает этот порядок. Обновления списка
сохраняют выбранную пользователем сортировку; стартовая проверка по-прежнему
проверяет только текущий маршрут, без автоматического полного перебора.

Интерфейс использует централизованные семантические токены One Dark Pro из `app/core/app_config.py`: фон `#282C34`, панели `#21252B`/`#2C313C`, границы `#3E4451`, основной текст `#ABB2BF`, синий action/focus `#61AFEF`, зелёный success `#98C379`, красный danger `#E06C75` и оранжевый warning `#D19A66`. QSS-компоненты не должны добавлять произвольные hex-цвета; новые состояния сначала добавляются как токены. Обычный и приглушённый текст, основные действия и статусы проверяются на контраст не ниже WCAG AA 4.5:1; disabled-состояния остаются явно неактивными.

Окончательная QSS-тема и экранный масштаб применяются до первого `show()`, чтобы системная палитра Qt не вспыхивала при запуске. Screen/DPI hooks подключаются уже после показа, когда доступен `windowHandle()`. Таблица использует контролируемую сортировку из `app/ui/table_sorting.py`: узлы сравниваются по русской части названия после флага/кода страны, IP и задержка — численно, API — в логическом порядке, дата — хронологически, отсутствующие значения всегда идут после заполненных. Все основные действия имеют подписанные SVG-иконки из `assets/icons/`; `assets/router.svg` является масштабируемым исходником марки, `assets/router.ico` — многослойной Windows-иконкой 16–256 px, воспроизводимой через `tools/export_app_icon.py`. Растровый `assets/app-icon-master.png` хранит исходную сгенерированную концепцию.

Таблица содержит только полезные столбцы `Узел`, `IP`, `API`, `Задержка`, `Проверен`. Текущий маршрут отмечается зелёной SVG-галочкой непосредственно в ячейке узла и подсказкой, поэтому отдельный служебный столбец не нужен. Строки с `API=FAIL` получают семантическую заливку `danger_surface` и явный контрастный `FAIL` цветом `danger_text`; цвет не является единственным индикатором состояния.

После первого показа окна создаётся `TrayController`. `QApplication` работает с `quitOnLastWindowClosed=False`: `closeEvent` сохраняет геометрию и скрывает окно, а `QSystemTrayIcon` остаётся видимым. «Показать», обычная активация и двойной клик восстанавливают окно. Единственная пользовательская команда завершения — «Выход» в меню лотка; она отказывается закрывать процесс, пока `ApplicationCore.is_busy`, чтобы не оборвать PowerShell `finally` при временной смене маршрута.

`MainWindow.route_monitor_timer` каждые 300000 мс запускает неблокирующий `status`, только если core свободен. Успешный фоновый результат обновляет карточку без toast. Неуспешная health-проверка запускает один `auto -DifferentIp`, то есть использует тот же русскоязычный циклический порядок, что кнопка «Другой IP». Ошибка controller/named pipe не запускает перебор, потому что без Clash переключение невозможно. `TrayController.notify()` централизует системные уведомления; клик по сообщению восстанавливает окно.

## Release pipeline

Версия читается из `VERSION` и синхронизируется с `pyproject.toml`, release notes, installer metadata и tray tooltip. Сборочный pipeline:

1. `Build_Tools/build_release.py` проверяет точный `.venv` interpreter, полностью заменяет `PATH` доверенным минимумом и запускает `OpenCodeRouter.spec`.
2. `.spec` включает только публичные runtime-файлы и `OpenCodeRouter.config.example.json`; локальный `OpenCodeRouter.config.json`, `settings.json`, `logs/`, `cache/` и `private/` не входят.
3. `Build_Tools/audit_build.py` читает `COLLECT-00.toc`, останавливается при foreign binary origin и сверяет SHA-256 полного `concrt140/msvcp140*/vcruntime140*` комплекта с текущим PySide6. Результат сохраняется в `BUILD_AUDIT.json`.
4. `Build_Tools/post_build.py` требует успешный audit, переносит onedir в корневую `OpenCodeRouter/`, создаёт `RUNTIME_MANIFEST.json` и сохраняет work/dist. `OPENCODE_ROUTER_BUILD_ROOT` задаёт временный корень, по умолчанию это `../temp-dev/<проект>/release`. Полный аудит остаётся там, а распространяемый отчёт не содержит локальных путей. EXE содержит Windows version resource из `VERSION`.
5. `Build_Tools/build_installer.py` создаёт установщик на рабочем столе или в `--output-dir`. На целевом компьютере выбирается `D:\Apps\OpenCodeRouter` при наличии D, иначе `C:\Apps\OpenCodeRouter`. Язык мастера — русский. Для нестандартного расположения Inno Setup задайте `INNO_SETUP_ISCC`. Скрипт сам не запускает установленное приложение.
6. `Build_Tools/deploy_portable.py --destination-parent <папка>` обновляет файлы поставки в подпапке `OpenCodeRouter` явно выбранного назначения, сохраняя пользовательские настройки, логи и кеши. Архив не создаётся.

Перед запуском `post_build.py` всегда сохраняйте результат аудита `COLLECT-00.toc`. После post-build обязателен неинтерактивный frozen smoke с захватом stdout/stderr.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests OpenCodeRouter.pyw
$env:QT_QPA_PLATFORM='offscreen'; .\.venv\Scripts\python.exe .\OpenCodeRouter.pyw --smoke-test
pwsh -NoProfile -File .\tests\Router.Tests.ps1
pwsh -NoProfile -File .\OpenCodeRouter.ps1 status
```

GUI использует только проектную `.venv`. Обычный запуск выполняется через `.venv\Scripts\pythonw.exe`; VS Code workspace и Debug также закреплены за проектной `.venv` в `.vscode/settings.json` и `.vscode/launch.json`. `settings.json` и `logs/gui.log` являются локальными runtime-файлами и исключены из Git. Во время выполняющейся команды окно можно скрыть в лоток, но нельзя завершить приложение: это сохраняет PowerShell `finally`, отвечающий за восстановление исходного selector.

Selector recovery tests mock the controller and use synthetic nodes. Live routing checks require an explicitly configured integration; temporary tests must restore selection.

## Sources

Reference documentation: [Qt for Python](https://doc.qt.io/qtforpython-6/), [setuptools package discovery](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html), [Mihomo listeners](https://github.com/metacubex/meta-docs/blob/main/docs/config/inbound/listeners/index.md), [REST API](https://github.com/metacubex/meta-docs/blob/main/docs/api/index.md), [.NET ConnectCallback](https://github.com/dotnet/runtime/blob/main/src/libraries/System.Net.Http/src/System/Net/Http/SocketsHttpHandler/SocketsHttpHandler.cs).



## Документация для посетителей GitHub

- `README.md` — краткое описание и запуск на русском.
- `README.en.md` — английская версия с той же последовательностью запуска.
- `docs/USAGE.md` — подробное руководство, выделенное из прежнего README.


При изменении запуска, требований или релиза синхронизировать обе версии README.

## Минимальная интеграция Clash

`examples/clash-verge/opencode.fragment.yaml` описывает минимальные дополнения к рабочему профилю. Инструкции: `docs/CLASH_SETUP.md` и `docs/CLASH_SETUP.en.md`. Это документационный фрагмент с placeholder-именами узлов, не самостоятельная подписка и не автоматический установщик. Конфигурации с учётными данными в репозиторий не включаются.

Если подписка предоставляет пользовательские направления со ⭐/🚀, добавляйте
в `OpenCode-Location` именно эти имена из основной VPN-группы. Направление может
быть вложенной fallback-группой: не раскрывайте её рекурсивно до внутренних
серверов (`DE-15`, `BRIDGE-US-3` и подобных). Постоянную правку выполняйте
в Global Script, поскольку Clash заново генерирует runtime YAML при применении профиля.


## Local build preferences

Optional machine-specific build preferences belong in ignored `private/build-settings.json`.
Supported keys are `portableParent` (portable deployment parent) and `iscc` (Inno Setup
compiler executable). The installer selects `D:\Apps\OpenCodeRouter` when D exists on
the target computer, otherwise `C:\Apps\OpenCodeRouter`; legacy `installDir` is ignored.
Without local preferences, portable deployment requires `--destination-parent`.
The `INNO_SETUP_ISCC` environment variable overrides the local compiler setting; an explicit
`--destination-parent` overrides the local portable destination. Do not commit this local file.
