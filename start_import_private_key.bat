@echo off
call venv\Scripts\activate

python import_private_key\import_private_key.py

deactivate
