# Проверка проекта / Verification

Этот документ описывает воспроизводимые проверки. Личные адреса, подписки,
снимки соединений и рабочие конфигурации не входят в репозиторий.

## Автоматические проверки

Из корня проекта с подготовленной `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check app tests tools OpenCodeRouter.pyw
pwsh -NoProfile -File .\tests\Router.Tests.ps1
```

Тесты GUI используют offscreen-режим и подставные данные. Router.Tests.ps1
проверяет классификацию ответов, восстановление selector и выбор узлов с mock-контроллером.

## Интеграционные проверки

Проверяйте конфигурационные примеры на искусственном профиле без рабочих учётных данных.

Живые проверки требуют собственной настроенной интеграции Clash. Они могут
временно переключать маршрут, поэтому выполняются отдельно от unit-тестов.
Не публикуйте конфиги и реальные адреса вместе с результатами.

## Что эти проверки не доказывают

- Доступность провайдеров из другой сети и успешный запрос с API-ключом.
- Правильность произвольной подписки Clash.
- Работу установщика после изменений в сборке без нового frozen smoke-test.

## English

Run the automated commands above from the repository root using its `.venv`.
GUI tests use offscreen rendering and fake data. PowerShell tests mock controller operations.
Configuration examples should be checked against synthetic profiles without credentials.
Live routing and installer verification are separate checks; never attach credentials or personal IP addresses.
