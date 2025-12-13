#!/usr/bin/env bash

cd ../..

docker build -t arina/sber/dashboard:master -f docker/app/Dockerfile .
