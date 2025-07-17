@echo off
cd /d "%~dp0"
echo Updating repository to latest main branch...
echo This will discard any local changes!
echo.
pause
echo.
echo Fetching latest changes from remote...
git fetch origin
echo.
echo Resetting to origin/main (this will discard local changes)...
git reset --hard origin/main
echo.
echo Repository updated successfully!
pause 
