#!/usr/bin/env bash

cd ../..

docker build -t arina/sber/postgres:16.9-bookworm -f docker/postgres/Dockerfile .

#docker push goolegs/trs/keycloak:local
#read -rsn1 -p"Press any key to continue";echo
