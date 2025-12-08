#!/bin/bash


export COMPOSE_PROJECT_NAME=servers

docker-compose -f docker-compose.yaml --env-file .env.docker down
