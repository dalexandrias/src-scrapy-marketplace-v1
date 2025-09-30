"""
Sistema de Monitoramento do Facebook Marketplace
Ponto de entrada principal para o sistema
"""

import sys
import os

# Adicionar o diretório atual ao path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
