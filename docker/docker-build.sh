#!/usr/bin/env bash

cd ..

docker build -t arina/sber:master -f docker/Dockerfile .
