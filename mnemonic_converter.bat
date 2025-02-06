@echo off
call venv\Scripts\activate

python mnemonic_converter/mnemonic_converter.py

deactivate
