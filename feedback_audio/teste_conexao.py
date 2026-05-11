"""
Script de Teste de Conexão - Sistema de Análise NPS
====================================================

Valida se todas as configurações e conexões estão funcionando corretamente.
"""

import sys
from pathlib import Path

def test_imports():
    """Testa se todos os módulos podem ser importados"""
    print("\n🔍 Testando imports...")
    try:
        from config import config
        print("  ✅ config.py")
        from conecta_banco import get_sqlalchemy_engine, get_psycopg2_connection
        print("  ✅ conecta_banco.py")
        import pandas as pd
        print("  ✅ pandas")
        import google.generativeai as genai
        print("  ✅ google.generativeai")
        from dotenv import load_dotenv
        print("  ✅ python-dotenv")
        return True, config
    except ImportError as e:
        print(f"  ❌ Erro de importação: {e}")
        return False, None

def test_config_validation(config):
    """Valida se as configurações essenciais estão presentes"""
    print("\n⚙️  Validando configurações...")
    if config.validate():
        print("  ✅ Configurações válidas!")
        return True
    else:
        print("  ❌ Configurações inválidas!")
        return False

def test_database_connection(config):
    """Testa conexão com o banco de dados"""
    print("\n🗄️  Testando conexão com banco de dados...")
    try:
        from conecta_banco import get_psycopg2_connection
        conn = get_psycopg2_connection()
        print(f"  ✅ Conectado ao {config.DB_HOST}:{config.DB_PORT}")
        
        # Testa uma query simples
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"  ✅ PostgreSQL: {version.split(',')[0]}")
        
        # Verifica schema
        cursor.execute(f"SELECT schema_name FROM information_schema.schemata WHERE schema_name = '{config.DB_SCHEMA}'")
        schema = cursor.fetchone()
        if schema:
            print(f"  ✅ Schema '{config.DB_SCHEMA}' existe")
        else:
            print(f"  ⚠️  Schema '{config.DB_SCHEMA}' não encontrado")
        
        # Verifica tabelas essenciais
        cursor.execute(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{config.DB_SCHEMA}'
            AND table_name IN ('rawdata_analise_nps_analistas', 'analise_nps_analistas', 'vw_report_diario')
        """)
        tables = cursor.fetchall()
        
        expected_tables = ['rawdata_analise_nps_analistas', 'analise_nps_analistas', 'vw_report_diario']
        found_tables = [t[0] for t in tables]
        
        for table in expected_tables:
            if table in found_tables:
                print(f"  ✅ Tabela '{table}' existe")
            else:
                print(f"  ⚠️  Tabela '{table}' não encontrada")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Erro de conexão: {e}")
        return False

def test_gemini_api(config):
    """Testa conexão com API do Gemini"""
    print("\n🤖 Testando API Google Gemini...")
    try:
        import google.generativeai as genai
        
        if not config.GEMINI_API_KEY:
            print("  ❌ GEMINI_API_KEY não configurada")
            return False
        
        genai.configure(api_key=config.GEMINI_API_KEY)
        print(f"  ✅ API Key configurada (***{config.GEMINI_API_KEY[-8:]})")
        print(f"  ✅ Modelo: {config.GEMINI_MODEL}")
        
        # Teste simples
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        response = model.generate_content("Hello, responda apenas 'OK'")
        
        if response.text:
            print(f"  ✅ API funcionando! Resposta: {response.text[:50]}")
            return True
        else:
            print("  ⚠️  API respondeu, mas sem texto")
            return False
            
    except Exception as e:
        print(f"  ❌ Erro na API Gemini: {e}")
        return False

def test_file_permissions():
    """Testa permissões de escrita nos diretórios"""
    print("\n📁 Testando permissões de arquivos...")
    
    # Diretório de logs
    logs_dir = Path(__file__).parent / "logs"
    try:
        logs_dir.mkdir(exist_ok=True)
        test_file = logs_dir / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        print(f"  ✅ Permissão de escrita em logs/")
    except Exception as e:
        print(f"  ❌ Sem permissão em logs/: {e}")
        return False
    
    # Diretório raiz (para arquivos de saída)
    try:
        test_file = Path(__file__).parent / "test_write.tmp"
        test_file.write_text("test")
        test_file.unlink()
        print(f"  ✅ Permissão de escrita no diretório raiz")
    except Exception as e:
        print(f"  ❌ Sem permissão no diretório raiz: {e}")
        return False
    
    return True

def main():
    """Executa todos os testes"""
    print("="*70)
    print("🧪 TESTE DE CONFIGURAÇÃO - Sistema de Análise NPS")
    print("="*70)
    
    results = []
    
    # 1. Imports
    success, config = test_imports()
    results.append(("Imports", success))
    
    if not success:
        print("\n❌ Falha nos imports. Instale as dependências:")
        print("   pip install -r requirements.txt")
        return False
    
    # 2. Validação de config
    success = test_config_validation(config)
    results.append(("Configurações", success))
    
    if not success:
        print("\n❌ Configure o arquivo .env corretamente")
        return False
    
    # 3. Banco de dados
    success = test_database_connection(config)
    results.append(("Banco de Dados", success))
    
    # 4. API Gemini
    success = test_gemini_api(config)
    results.append(("API Gemini", success))
    
    # 5. Permissões
    success = test_file_permissions()
    results.append(("Permissões de Arquivo", success))
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO DOS TESTES")
    print("="*70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        print(f"  {test_name:.<50} {status}")
        if not passed:
            all_passed = False
    
    print("="*70)
    
    if all_passed:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("\n✅ Sistema pronto para uso!")
        print("\n💡 Para executar: python verifica_nps.py")
        return True
    else:
        print("\n⚠️  ALGUNS TESTES FALHARAM!")
        print("\n📖 Consulte o GUIA_INSTALACAO.md para mais detalhes")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
