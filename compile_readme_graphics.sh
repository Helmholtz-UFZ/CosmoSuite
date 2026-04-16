#!/usr/bin/env bash

drawio -x -f svg -e -b 10 -o "docs/diagrams/architecture.svg" "docs/diagrams/architecture.drawio"
drawio -x -f png -e -b 10 -o "docs/diagrams/architecture.png" "docs/diagrams/architecture.drawio"
