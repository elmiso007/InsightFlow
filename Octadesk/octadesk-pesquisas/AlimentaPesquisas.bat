@echo off
setlocal EnableExtensions

for /f "usebackq eol=# tokens=1* delims==" %%A in ("%~dp0.env") do (
  if not "%%A"=="" (
    set "%%A=%%B"
  )
)

python "%~dp0api.py"