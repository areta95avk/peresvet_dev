#!/bin/bash
# Скрипт запускает контейнеры с сервисами платформы. Протокол - HTTPS.
# Предназначен для запуска на сервере, доступном из интернета, 
# так как сертификаты генерируются с помощью Let's Encrypt.
# 
# в первом аргументе можно задать имя сервера, в качестве которого по умолчанию
# принимается имя текущего сервера

#-f docker/compose/docker-compose.grafana.yml \

srv=$HOSTNAME
if [ -n "$1" ]
then
    srv=$1
fi

sed -i "s/NGINX_HOST=.*/NGINX_HOST=$srv/" docker/compose/.cont_one_app.env
docker compose --env-file docker/compose/.cont_one_app.env \
-f docker/compose/docker-compose.redis.yml \
-f docker/compose/docker-compose.rabbitmq.yml \
-f docker/compose/docker-compose.ldap.one_app.yml \
-f docker/compose/docker-compose.postgresql.data_in_container.yml \
-f docker/compose/docker-compose.one_app.yml \
-f docker/compose/docker-compose.grafana.yml \
-f docker/compose/docker-compose.nginx.one_app_ssl_letsencrypt.yml \
up
