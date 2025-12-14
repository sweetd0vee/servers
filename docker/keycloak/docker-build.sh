#!/usr/bin/env bash

cd ../..

docker build -t arina/sber/keycloak:26.4.6 -f docker/keycloak/Dockerfile .

#docker push goolegs/trs/keycloak:local
#read -rsn1 -p"Press any key to continue";echo
