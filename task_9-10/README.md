# Практическое задание DevOps

В проект входят веб-приложение, конфигурации Docker/Prometheus/Alertmanager, systemd-служба и манифесты Kubernetes Deployment, Service и Ingress.

## Контракт приложения

- `POST /` и `POST /hello` возвращают `Hello, World!`, только если запрос содержит заголовок `Test: Hello`. В противном случае приложение возвращает HTTP 403.
- `GET /health` отправляет ping на `77.88.8.8` и при успехе возвращает HTTP 200 и текст `OK`. Если ping не проходит, возвращается HTTP 503.
- `GET /metrics` предоставляет метрики Prometheus.

## Docker Compose

Контейнеры мониторинга работают не от root. В Ubuntu перед запуском Compose скопируйте конфигурации в доступный для чтения каталог вне закрытого домашнего каталога:

```sh
sudo install -d -m 0755 /opt/devops-assignment/prometheus /opt/devops-assignment/alertmanager
sudo install -m 0644 prometheus/*.yml /opt/devops-assignment/prometheus/
sudo install -m 0644 alertmanager/*.yml /opt/devops-assignment/alertmanager/
```

Запустите сервисы и проверьте приложение:

```sh
docker compose up -d --build
docker compose ps
curl -i -X POST -H 'Test: Hello' http://127.0.0.1:8001/
curl -i http://127.0.0.1:8001/health
```

Приложение из Compose привязано к `127.0.0.1:8001`, поэтому существующее приложение systemd продолжает использовать порт 8000. Prometheus доступен на `127.0.0.1:9090`, Alertmanager — на `127.0.0.1:9093`. Prometheus собирает метрики приложения из Compose и формирует оповещение `WebAppDown`, если сбор метрик не удаётся в течение 30 секунд. Оповещение отображается в Alertmanager; внешний получатель уведомлений не настроен.

## systemd в Ubuntu Server

Создайте непривилегированную системную учётную запись, установите приложение в `/opt/devops-assignment` и установите Python-зависимости в виртуальное окружение `.venv`:

```sh
sudo adduser --system --group --home /opt/devops-assignment webapp
sudo install -d -o webapp -g webapp /opt/devops-assignment
sudo apt-get update && sudo apt-get install -y python3-venv iputils-ping
sudo -u webapp python3 -m venv /opt/devops-assignment/.venv
sudo -u webapp /opt/devops-assignment/.venv/bin/pip install -r /opt/devops-assignment/requirements.txt
sudo install -m 0644 systemd/devops-assignment.service /etc/systemd/system/devops-assignment.service
sudo systemctl daemon-reload
sudo systemctl enable --now devops-assignment.service
```

Перед выполнением команд скопируйте на VM код приложения, `requirements.txt` и systemd unit-файл.

## Kubernetes

В `k8s/app.yaml` указан образ `devops-assignment-web:1.0.0`. Он должен быть доступен на каждом узле. Также должен быть установлен контроллер Ingress. K3s устанавливает Traefik по умолчанию; для другого кластера установите и настройте контроллер Ingress, а затем укажите соответствующий `ingressClassName`. Сам ресурс Ingress не открывает сетевой порт: контроллер должен быть доступен через сеть VM. Манифест не использует `kubectl port-forward`.

```sh
kubectl apply -f k8s/app.yaml
kubectl get deploy,svc,ingress,pods -o wide
```

До применения манифеста соберите образ на каждом узле или опубликуйте его в реестре, доступном всем узлам.

## Развёртывание лабораторного кластера из трёх узлов

На текущих узлах K3s используется Ubuntu 22.04.5 LTS Desktop (графическая редакция), а не редакция Server. K3s и приложение уже работают; замена операционных систем потребует пересоздания кластера.

| Узел | Роль | Адрес Host-only / LAN |
| --- | --- | --- |
| `TASK9-K8S1` | Server / control plane | `192.168.56.103` / `192.168.0.115` (адрес LAN по DHCP) |
| `TASK9-K8S2` | Agent | `192.168.56.105` |
| `TASK9-K8S3` | Agent | `192.168.56.106` |
| `TASK9-ROUTER` | Шлюз NAT | `192.168.56.2` |
| `Task_8-10` | VM приложения и мониторинга Compose | `192.168.56.104` |

У маршрутизатора есть WAN-интерфейс NAT (`enp0s3`) и интерфейс внутренней сети Host-only (`enp0s8`). На нём включена пересылка IPv4, а трафик сети `192.168.56.0/24` маскарадуется при выходе через `enp0s3`. Правила сохраняются пакетом `iptables-persistent`. Установленный на маршрутизаторе `dnsmasq` пересылает DNS-запросы внутренней сети DNS-серверу VirtualBox NAT. VM приложения и все три узла Kubernetes используют `192.168.56.2` как шлюз по умолчанию. Их собственные NAT-интерфейсы оставлены для SSH-пробросов портов VirtualBox, но не используются как маршрут по умолчанию.

У каждого узла K3s есть NAT-интерфейс (`enp0s3`) и общий интерфейс Host-only (`enp0s8`). На `TASK9-K8S1` дополнительно настроен интерфейс моста к LAN (`enp0s9`) с адресом `192.168.0.115`, выданным DHCP. У этого интерфейса нет маршрута по умолчанию, IPv6 отключён; шлюзом по умолчанию остаётся `TASK9-ROUTER` (`192.168.56.2`). Постоянная служба `task9-lan-firewall.service` разрешает через мост TCP-подключения LAN только к портам 80/443 сети Pod Traefik, пропускает DHCP-ответы и блокирует прочий входящий и пересылаемый трафик через `enp0s9`. Unit-файл и скрипт находятся в `systemd/task9-lan-firewall.service` и `systemd/task9-lan-firewall.sh`. Поскольку гостевые NAT-интерфейсы используют одинаковый адрес на разных VM, Flannel явно привязан к интерфейсу Host-only. На каждом узле в `/etc/rancher/k3s/config.yaml` содержится:

```yaml
flannel-iface: enp0s8
```

Образ приложения `devops-assignment-web:1.0.0` импортирован в containerd K3s на каждом узле. Манифест создаёт три реплики — по одной на узел — и ресурс Ingress для Traefik. С хоста Windows или другого клиента физической сети `192.168.0.0/24` откройте `http://192.168.0.115/` или `https://192.168.0.115/`. Запрос попадает в Traefik через мост `enp0s9`; `kubectl port-forward` не используется. С хоста Windows также доступны адреса Host-only: `http://192.168.56.103/`, `http://192.168.56.105/` и `http://192.168.56.106/`. Адрес моста получен по DHCP и может измениться при обновлении аренды DHCP в LAN.

## Задание 10: безопасность рабочих нагрузок Kubernetes

В кластере установлены Cilium 1.20.5 в режиме CNI chaining вместе с Flannel, Istio 1.32.0 (профиль minimal) и OPA Gatekeeper 3.23.1. У Deployment `default/devops-assignment-web` три реплики с sidecar-контейнерами Istio. Конфигурации для повторного развёртывания находятся в `security/cilium-values.yaml`, `security/istio-install.yaml`, `security/gatekeeper-values.yaml`, `k8s/cilium-web-policy.yaml` и `k8s/istio-web-policy.yaml`.

Политика Istio `AuthorizationPolicy` `devops-assignment-web-allowlisted-http` разрешает только `POST /` или `POST /hello` с заголовком `Test: Hello`, а также `GET /health`. Запросы к другим путям или без требуемого заголовка отклоняются с кодом 403. Политика Cilium `CiliumNetworkPolicy` `devops-assignment-web-ingress` ограничивает доступ к порту приложения 8000 endpoint-ом Traefik, выбранным по Kubernetes-меткам. Отдельно разрешены kubelet probes на порты Istio 15020/15021 с адресов CNI-шлюзов трёх узлов. Исходный Pod Traefik был создан до установки Cilium и не имел Cilium endpoint, поэтому после включения CNI chaining его пересоздали. Новый Pod отображается как Cilium endpoint, и политика по меткам работает на всех трёх узлах. Внешний адрес Ingress — `192.168.0.115`; `port-forward` не используется.

Контейнер приложения и Pod работают с UID/GID 10001 и настройкой `runAsNonRoot`. Для контейнера заданы seccomp `RuntimeDefault`, файловая система root только для чтения, запрет повышения привилегий и сброс всех Linux capabilities, кроме `NET_RAW`, необходимой для проверки доступности через ping. Запросы и лимиты CPU, памяти и ephemeral-storage задаются в `k8s/app.yaml`. Для sidecar Istio также указаны запросы и лимиты CPU и памяти. Монтирование токена ServiceAccount включено, поскольку он нужен Istio для аутентификации в istiod.

Gatekeeper 3.23.1 проверяет эти же ограничения при admission с помощью `K8sWebContainerSecurity` и constraint `devops-assignment-web-security`. Constraint применяется к Pod в namespace `default` с меткой `app=devops-assignment-web`. Он проверяет UID/GID Pod, режим non-root, seccomp `RuntimeDefault`, UID/GID контейнера web, файловую систему только для чтения, настройку privilege escalation, сброшенные capabilities, а также CPU/memory requests и limits. Единственная дополнительная разрешённая capability — `NET_RAW` для ping. Параметр Helm Gatekeeper `controllerManager.disableGenerateOperation: false` необходим для регистрации контроллером CRD, используемых ConstraintTemplate.

Примените шаблон, дождитесь регистрации CRD, а затем примените constraint:

```sh
kubectl apply -f k8s/gatekeeper-template.yaml
kubectl wait --for=condition=Established crd/k8swebcontainersecurity.constraints.gatekeeper.sh --timeout=120s
kubectl apply -f k8s/gatekeeper-constraint.yaml
```

Проверка admission прошла успешно: тестовый Pod с меткой приложения, но без настроек безопасности, был отклонён с сообщениями Gatekeeper; Pod с требуемыми настройками прошёл server-side dry-run.

При проверках из физической LAN запросы к `http://192.168.0.115/` дали следующие результаты: 8 из 8 запросов POST с `Test: Hello` вернули 200; 4 из 4 POST-запросов без этого заголовка вернули 403; 4 из 4 запросов к `/health` вернули 200 и `OK`; 3 из 3 внешних запросов к `/metrics` вернули 403. Все три реплики приложения были в состоянии `2/2 Running`, три агента Cilium и контроллеры Istio и Gatekeeper работали, все три узла Kubernetes имели статус Ready. Исходный Pod Traefik был создан до установки Cilium и не управлялся Cilium; после установки он был пересоздан, что восстановило стабильное применение политики по выбранным меткам.

## Сверка с требованиями

| Пункт | Статус | Примечания |
| --- | --- | --- |
| a. Веб-приложение на Python и endpoints | Выполнено | Проверено: `Test: Hello` возвращает 200, отсутствующий или неверный заголовок — 403, `/health` — `200 OK`. |
| b. systemd-служба под отдельным пользователем | Выполнено | Служба работает как `webapp` на существующей VM `Task_8-10`. На этой VM установлена Ubuntu 22.10; отличие версии принято пользователем. |
| c. Dockerfile и образ | Выполнено | Образ собран и доступен Compose и всем узлам K3s. |
| d. Compose, Prometheus, Alertmanager | Выполнено | Все три контейнера работают; Prometheus собирает метрики и отправляет оповещение `WebAppDown` в Alertmanager. |
| e. Маршрутизатор с двумя интерфейсами и NAT | Выполнено | Внутренний адрес маршрутизатора — `192.168.56.2`; пересылка и masquerade сохраняются после перезагрузки. |
| f. Выход VM приложения через маршрутизатор | Выполнено | `Task_8-10` и узлы K3s используют `192.168.56.2` как IPv4-шлюз по умолчанию. |
| g. Кластер Kubernetes из трёх узлов | Работает; редакция ОС отличается | Все узлы Ready, у приложения 3 из 3 реплик. На узлах Ubuntu Desktop вместо запрошенной Server. Для server/control plane выделен 1 vCPU; в требованиях K3s указывается минимум 2 ядра. |
| h. Ingress без `kubectl port-forward` | Выполнено в физической LAN | Ingress доступен по `http://192.168.0.115/` и HTTPS через мост K8S1. Межсетевой экран ограничивает этот интерфейс HTTP/HTTPS-трафиком. |
| Задание 10a. Установка Istio, Cilium и Gatekeeper | Выполнено | Контроллеры Istio 1.32.0, Cilium 1.20.5 и Gatekeeper 3.23.1 работают; ConstraintTemplate и constraint приложения активны. |
| Задание 10b. Ограничение доступа с помощью Istio и Cilium | Выполнено | Cilium разрешает endpoint Traefik и проверки узлов; Istio разрешает только заданные POST-запросы с заголовком и health check. Повторные проверки из LAN прошли. |
| Задание 10c. Ограничения ресурсов, ФС и пользователя | Выполнено | Запросы и лимиты ресурсов, UID/GID 10001, non-root, read-only root filesystem, seccomp RuntimeDefault, запрет повышения привилегий и сброс capabilities настроены в Pod и контролируются Gatekeeper. |
