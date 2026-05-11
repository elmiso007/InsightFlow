#!/usr/bin/env python3
"""
Contact Rate Quick Start
Script para configuração rápida da aplicação.
"""

import shutil
from pathlib import Path
import sys

def main():
    base_dir = Path(__file__).resolve().parent
    
    print("\n" + "="*70)
    print("🚀 CONTACT RATE - QUICK START SETUP")
    print("="*70 + "\n")
    
    # Verificar se requirements estão instalados
    print("📦 Verificando dependências...")
    try:
        import pandas
        import psycopg2
        print("   ✅ pandas instalado")
        print("   ✅ psycopg2 instalado")
    except ImportError:
        print("   ❌ Dependências não encontradas!")
        print("\n   Execute: pip install -r requirements.txt\n")
        sys.exit(1)
    
    # Verificar CSV
    print("\n📄 Verificando arquivos...")
    csv_file = base_dir / 'Contact Rate_ Suporte N1.csv'
    if csv_file.exists():
        print(f"   ✅ {csv_file.name} encontrado")
    else:
        print(f"   ❌ {csv_file.name} não encontrado!")
        sys.exit(1)
    
    # Verificar scripts SQL
    sql_files = ['INSERT.sql', 'UPDATE.sql']
    for sql_file in sql_files:
        path = base_dir / sql_file
        if path.exists():
            print(f"   ✅ {sql_file} encontrado")
        else:
            print(f"   ❌ {sql_file} não encontrado!")
            sys.exit(1)
    
    # Verificar/criar config
    print("\n⚙️  Configuração...")
    config_file = base_dir / 'config.ini'
    config_example = base_dir / 'config_example.ini'
    
    if not config_file.exists() and config_example.exists():
        print(f"   ⚠️  config.ini não encontrado")
        response = input("   Copiar config_example.ini para config.ini? (s/n): ").lower()
        if response == 's':
            shutil.copy(config_example, config_file)
            print(f"   ✅ Arquivo criado!")
            print(f"   ⚠️  EDITE config.ini com suas credenciais reais!")
        else:
            print(f"   ℹ️  Você precisa criar config.ini manualmente")
    elif config_file.exists():
        print(f"   ✅ config.ini encontrado")
    
    # Criar logs dir
    print("\n📁 Estrutura de diretórios...")
    logs_dir = base_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)
    print(f"   ✅ logs/ criado")
    
    # Validar CSV
    print("\n✓ Validando CSV...")
    response = input("  Executar validador de CSV? (s/n): ").lower()
    if response == 's':
        import subprocess
        result = subprocess.run(
            [sys.executable, str(base_dir / 'validate_csv.py')],
            capture_output=False
        )
        if result.returncode != 0:
            print("   ❌ Validação falhou!")
            sys.exit(1)
    
    # Resumo
    print("\n" + "="*70)
    print("✅ SETUP CONCLUÍDO COM SUCESSO!")
    print("="*70)
    
    print("\n📚 Próximos passos:")
    print("   1. Editar config.ini com suas credenciais")
    print("   2. Executar: python validate_csv.py")
    print("   3. Executar: python contact_rate.py")
    print("\n📖 Para mais informações, leia README.md\n")

if __name__ == '__main__':
    main()
