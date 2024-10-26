#!/bin/bash
set -euo pipefail
for file in fiat/*.html token/*.html; do
    echo converting "$file" to "${file%\.html}.pdf"
    uv tool run weasyprint "$file" "${file%\.html}.pdf"
done
