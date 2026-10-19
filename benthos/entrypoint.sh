#!/bin/sh

# 47-96-0-0-5-20-1
./benthos -c ./workflows/47-96-0-0-5-20-1/temp.yaml &
./benthos -c ./workflows/47-96-0-0-5-20-1/water.yaml &
./benthos -c ./workflows/47-96-0-0-5-20-1/feedback.yaml &

# 25-56-0-0-8-162-1 (alfalfa)
./benthos -c ./workflows/25-56-0-0-8-162-1/water.yaml &
./benthos -c ./workflows/25-56-0-0-8-162-1/feedback.yaml &

tail -f /dev/null
