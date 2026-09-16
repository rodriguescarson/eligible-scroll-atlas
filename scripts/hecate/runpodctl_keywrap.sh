#!/usr/bin/env bash
# Scripts launched over ssh lack the container env, so runpodctl finds no API key. Read it from PID 1 at call time.
export RUNPOD_API_KEY="$(tr '\0' '\n' < /proc/1/environ | sed -n 's/^RUNPOD_API_KEY=//p')"
exec /usr/bin/runpodctl "$@"
