if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "====================================================="
Write-Host "DANG CAI DAT MOI TRUONG CHO BAI LAB (QUYEN ADMIN)"
Write-Host "====================================================="

Write-Host "[1/3] Dang cai dat Python 3.12 vao thu muc he thong (Program Files)..."
winget install --id Python.Python.3.12 --exact --machine --silent --accept-package-agreements --accept-source-agreements

Write-Host "[2/3] Dang cai dat cac thu vien AI (PyTorch, Pandas, ChromaDB...)..."
& "C:\Program Files\Python312\python.exe" -m pip install -e "C:\Users\doduc\K4-L3A-Day10-Data-Pipeline-Data-Observability"

Write-Host "[3/3] Kiem tra lai moi truong..."
& "C:\Program Files\Python312\python.exe" -c "import chromadb, great_expectations, sentence_transformers; print('Moi truong san sang!')"

Write-Host "====================================================="
Write-Host "CAI DAT HOAN TAT! Ban co the tat cua so nay."
Read-Host "Nhan Enter de thoat..."
