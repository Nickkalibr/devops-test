# Задание 8 — CI/CD на GitHub и Jenkins

## 1. Требования

1. Используется Git-сервер; допускается применение общедоступного сервера.
2. Необходимо развернуть Jenkins.
3. `Job_1_Clone` — получать код из ветки `master` в workspace.
4. `Job_2_Delete` — удалять один-два файла.
5. `Job_3_Push` — отправлять результат обратно в Git.
6. Обеспечить автоматический запуск jobs.

## 2. Использованная инфраструктура

| Компонент | Значение |
|---|---|
| Git-хостинг | GitHub |
| Репозиторий | <https://github.com/Nickkalibr/devops-test> |
| Ветка | `master` |
| Jenkins | `http://127.0.0.1:8080` |
| Jenkins version | `2.580.2` |
| Git version в логе Jenkins | `2.34.1` |
| Jenkins credential ID | `github-devops-test` |
| Публичный доступ | Cloudflare Tunnel (`cloudflared`) |

Секреты и токены в README не включаются.

## 3. Схема

```text
GitHub push
    |
    v
GitHub Webhook -> Cloudflare Tunnel -> Jenkins
                                        |
                                        v
                                    Job_1_Clone
                                        |
                                archive artifacts
                                        |
                                        v
                                    Job_2_Delete
                                        |
                                archive artifacts
                                        |
                                        v
                                    Job_3_Push
                                        |
                                        v
                                    GitHub / master
```

## 4. Проверка репозитория

```bash
git ls-remote --heads https://github.com/Nickkalibr/devops-test.git
git clone --branch master https://github.com/Nickkalibr/devops-test.git
cd devops-test
git log --oneline --decorate -10
```

В проекте использовались каталоги `task_1-5`, `task_6-7`, позднее `task_8`, а также `.gitignore` и `webhook-test.txt`.

## 5. Cloudflare Tunnel и GitHub webhook

Jenkins слушал локальный адрес `http://localhost:8080`. Для временного внешнего доступа запускался:

```bash
cloudflared tunnel --url http://localhost:8080
```

Команда выводит публичный URL вида:

```text
https://<generated-name>.trycloudflare.com
```

Далее:

1. Процесс `cloudflared` необходимо оставить запущенным.
2. Необходимо скопировать актуальный URL.
3. В интерфейсе GitHub необходимо открыть **Settings → Webhooks → Add webhook**.
4. Необходимо указать адрес Jenkins webhook endpoint, соответствующий установленному GitHub plugin. Для GitHub plugin обычно используется путь `/github-webhook/`; необходимо проверить установленный plugin и его необходимо настроитьки.
5. В качестве события необходимо выбрать `push`.
6. После сохранения webhook необходимо проверить раздел **Recent Deliveries**.

**Важно:** Quick Tunnel временный. После перезапуска адрес может измениться, и webhook нужно обновить. Для постоянной эксплуатации лучше настроить именованный Cloudflare Tunnel.

В одном из логов Cloudflare был выдан адрес `https://maximize-unlimited-listed-adequate.trycloudflare.com`; это историческое значение, не следует считать его актуальным.

## 6. Jenkins Credentials

Для Job 3 в Jenkins использовалась запись Credentials с ID:

```text
github-devops-test
```

Создание и проверка записи выполняются в **Manage Jenkins → Credentials**. Необходимо использовать поддерживаемый GitHub способ аутентификации (например, username + Personal Access Token). Токен должен иметь минимально необходимые права на запись в репозиторий.

Не следует вставлять токен прямо в URL, shell script или Git-репозиторий. Токен необходимо передавать через Jenkins Credentials и соответствующий credential binding/plugin.

## 7. Job_1_Clone — checkout master

SCM необходимо настроитьки:

- Source Code Management: **Git**
- Repository URL: `https://github.com/Nickkalibr/devops-test.git`
- Branch Specifier: `*/master`
- Публичный репозиторий может читаться без credential.

Пример диагностического Execute shell шага (SCM checkout выполняет Jenkins до shell):

```bash
#!/bin/bash
set -e

echo "Starting repository clone..."
echo "Current directory:"
pwd

echo "Repository files:"
ls -la

echo "Clone completed successfully!"
```

В выполненном варианте workspace был:

```text
/var/lib/jenkins/workspace/Job_1_Clone
```

После успешной сборки необходимо настроить:

- **Archive the artifacts** — архивировать файлы/каталоги проекта.
- **Build other projects** (или эквивалентную upstream/downstream необходимо настроитьку) — запускать `Job_2_Delete` только после успешного выполнения.

В консоли Job 1 были сообщения о checkout `origin/master`, `Clone completed successfully!`, архивировании артефактов и запуске Job 2.

## 8. Job_2_Delete — удалить два файла

Необходимо настроить **Copy artifacts from another project**:

- Project name: `Job_1_Clone`
- Build: последняя успешная сборка (или нужный номер сборки)
- Artifact filter: те файлы/каталоги, которые архивирует Job 1.

Пример shell-команд, соответствующих подтверждённому действию:

```bash
#!/bin/bash
set -e

echo "Files before deletion:"
find . -type f

rm -f task_8/delete-me-1.txt
rm -f task_8/delete-me-2.txt

echo "Files after deletion:"
find . -type f

test ! -f task_8/delete-me-1.txt
test ! -f task_8/delete-me-2.txt

echo "Both files successfully deleted!"
```

Затем необходимо заархивировать результат и настроить запуск `Job_3_Push` после успешного выполнения.

В логе до удаления были видны:

```text
./task_6-7/task_6-7.py
./task_6-7/requirements.txt
./task_1-5/task_1-5.py
./task_8/delete-me-1.txt
./task_8/delete-me-2.txt
```

После удаления остались три файла из `task_1-5` и `task_6-7`.

## 9. Job_3_Push — отправить изменения в Git

Необходимо настроить **Copy artifacts from another project**:

- Project name: `Job_2_Delete`
- необходимо выбрать артефакты успешной сборки.

Необходимо использовать credential ID `github-devops-test`. В логе Job 3 подтверждены fetch ветки `master`, синхронизация локальных изменений и push.

```

Для реального push необходимо обеспечить передачу credentials через Jenkins Credentials Binding / Git plugin. Пример выше не извлекает и не передаёт токен самостоятельно.

**Важная оговорка:** в показанном логе Job 3 было `No changes to commit`, затем `HEAD is up to date` и `Everything up-to-date`. Это успешный push/sync без нового коммита в той конкретной сборке. Необходимо проверить, что удаляемые Job 2 файлы действительно входят в отслеживаемую Git-историю, а Job 3 собирает изменённое рабочее дерево.

## 10. Автоматические триггеры

В логе Job 1 подтверждена причина запуска:

```text
Started by GitHub push by Nickkalibr
```

В downstream jobs отображался запуск от предыдущего проекта, например:

```text
Started by upstream project "Job_1_Clone" build number 11
```

Необходимо проверить следующие настройки:

- `Job_1_Clone`: GitHub hook trigger for GITScm polling (название зависит от установленного plugin).
- `Job_2_Delete`: запуск после успешного завершения `Job_1_Clone`.
- `Job_3_Push`: запуск после успешного завершения `Job_2_Delete`.

## 11. Проверка

В Jenkins необходимо проверить:

- `Job_1_Clone`: checkout из `origin/master`, успешное завершение и архивирование.
- `Job_2_Delete`: копирование артефактов; в выводе до/после два файла должны отсутствовать после удаления.
- `Job_3_Push`: Git fetch/push и статус `SUCCESS`.

Проверка репозитория вручную выполняется следующими командами:

```bash
git clone --branch master https://github.com/Nickkalibr/devops-test.git
cd devops-test
find . -type f
git log --oneline -10
```

## 12. Что подтверждено и что нужно уточнить

Подтверждено логами/скриншотами:

- Jenkins 2.580.2 доступен на `127.0.0.1:8080`.
- GitHub использовался как публичный Git-сервер.
- Job 1 получала код из `master`.
- GitHub push автоматически запускал Job 1.
- Job 2 копировала 3 артефакта и удаляла `task_8/delete-me-1.txt` и `task_8/delete-me-2.txt`.
- Job 3 получала артефакты Job 2 и выполняла Git fetch/rebase/push.
- Показанные сборки завершались `SUCCESS`.

Не сохранились в материалах:

- Полные исходные shell-скрипты всех трёх jobs.
- Полные XML-конфигурации Jenkins jobs.
- Окончательный webhook URL, secret и полный список выбранных событий.
- Содержимое GitHub token / Jenkins credential.

README содержит воспроизводимую логику и примеры команд; пример Job 3 следует следует адаптировать под фактическую схему копирования артефактов и Jenkins credentials.
