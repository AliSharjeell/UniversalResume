@echo off
setlocal
if exist "%~dp0resume.js" (
  bun "%~dp0resume.js" %*
) else if exist "%~dp0node_modules\resume-tui\bin\resume.js" (
  bun "%~dp0node_modules\resume-tui\bin\resume.js" %*
) else if exist "C:\AppsNew\UniversalResume\bin\resume.js" (
  bun "C:\AppsNew\UniversalResume\bin\resume.js" %*
) else (
  bun "%USERPROFILE%\.samethread-repo\bin\resume.js" %*
)
