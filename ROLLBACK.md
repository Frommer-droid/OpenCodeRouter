# Отключение интеграции и восстановление настроек

## Перед изменением профиля

Сохраните копию действующей конфигурации Clash Verge Rev и Global Script
в выбранную вами папку вне Git. Для настроек Router сохраните локальный
`OpenCodeRouter.config.json`. Храните резервную копию вместе с её датой и описанием.

## Отключение маршрута OpenCode

1. Завершите текущую проверку Router и выберите «Выход» в меню трея.
2. Отключите добавленное расширение профиля или удалите его изменения:
   правило `PROCESS-NAME,opencode.exe,OpenCode-Location`, диагностический listener
   `OpenCode-Test-Local` и группу `OpenCode-Location`.
3. Если эти имена были изменены, используйте свои значения. Перед удалением группы
   проверьте, что другие правила и listeners на неё не ссылаются.
4. Восстановите прежние значения общих настроек, если меняли их для интеграции.
   Не отключайте TUN, если он нужен другим приложениям.
5. Проверьте конфигурацию в Clash Verge Rev и примените её. Маршрут OpenCode
   будет определяться оставшимися правилами профиля.

Для полного возврата профиля восстановите собственную резервную копию через
Clash Verge Rev. Универсальный скрипт восстановления здесь не предоставляется:
расположение и состав профилей зависят от установки.

## Временная проверка узлов

`test` и `scan` восстанавливают выбранный до проверки узел. Это изменение selector,
а не восстановление файлов конфигурации. При недоступном API контроллера возврат
может быть невозможен; проверьте состояние группы после восстановления связи.

## English

Back up your Clash profile, Global Script and local Router config outside Git before
changing them. To disable the integration, finish pending tests and exit Router,
then disable the profile extension or remove the added process rule, diagnostic
listener and selector. Check for other references before removing a group.
Restore any shared settings you changed; keep TUN enabled if other applications need it.
Validate and apply the profile in Clash Verge Rev. To restore the entire profile,
use your own backup. The repository provides no installation-specific restore script.

Temporary `test` and `scan` commands restore the previous selector, not profile files.
An unavailable controller may prevent restoration; verify the group after reconnecting.
