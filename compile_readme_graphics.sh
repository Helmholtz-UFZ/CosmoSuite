#!/usr/bin/env bash

drawio -x -f svg -e -b 10 -o "docs/diagrams/architecture.svg" "docs/diagrams/architecture.drawio"
drawio -x -f png -e -b 10 -o "docs/diagrams/architecture.png" "docs/diagrams/architecture.drawio"

# drawio sometimes produces PNGs missing the IEND chunk — append one if absent
if ! tail -c 8 "docs/diagrams/architecture.png" | grep -q "IEND"; then
    printf '\x00\x00\x00\x00IEND\xae\x42\x60\x82' >> "docs/diagrams/architecture.png"
    echo "Warning: appended missing IEND chunk to architecture.png"
fi
