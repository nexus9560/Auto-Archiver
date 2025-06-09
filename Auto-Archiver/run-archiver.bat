@echo off
REM Usage: run_archiver.bat <URL>
setlocal

REM Activate the virtual environment
call AA-ENV\Scripts\activate.bat

REM Run the Python script with the provided URL
python Auto_Archiver.py %1

REM Deactivate the virtual environment (optional)
deactivate

endlocal