# Безопасное использование / Safe use

Храните API-ключи, controller secret, URL подписок и личные конфигурации локально,
вне Git. Не включайте их в скриншоты или распространяемые сборки. Открывайте локальный
controller API только на loopback и сохраняйте его аутентификацию, если она настроена.
Проверяйте изменения конфигурации перед применением и храните резервные копии вне Git.

Keep API keys, controller secrets, subscription URLs and personal configurations outside
Git. Exclude them from screenshots and distributed builds. Bind a local controller API
to loopback and preserve configured authentication. Review configuration changes before
applying them and keep backups outside Git.
