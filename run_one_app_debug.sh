#!/bin/bash
# Скрипт запускает контейнеры с компонентами, необходимыми для работы платформы,
# кроме сервисов самой платформы.

#-f docker/compose/docker-compose.grafana.yml \

docker compose --env-file docker/compose/.cont_one_app.env \
-f docker/compose/docker-compose.redis.yml \
-f docker/compose/docker-compose.rabbitmq.yml \
-f docker/compose/docker-compose.ldap.one_app.yml \
-f docker/compose/docker-compose.postgresql.data_in_container.yml \
-f docker/compose/docker-compose.grafana.yml \
-f docker/compose/docker-compose.ports.yml \
up
