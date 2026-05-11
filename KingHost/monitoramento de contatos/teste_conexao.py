import sys
from conecta_banco import get_sqlalchemy_engine, get_pyodbc_connection
import pandas as pd
from datetime import datetime

print("🔍 Testando conexão com o banco de dados...")

try:
    # Teste 1: SQLAlchemy Engine
    print("\n1️⃣ Testando SQLAlchemy engine...")
    engine = get_sqlalchemy_engine()
    print("✅ Engine criado com sucesso")
    
    # Teste 2: PyODBC Connection  
    print("\n2️⃣ Testando PyODBC connection...")
    conn = get_pyodbc_connection()
    print("✅ Conexão PyODBC criada com sucesso")
    
    # Teste 3: Query simples
    print("\n3️⃣ Testando query simples...")
    simple_query = "SELECT 1 as teste"
    df_test = pd.read_sql_query(simple_query, conn)
    print(f"✅ Query executada: {df_test.iloc[0]['teste']}")
    
    # Teste 4: Verificar se as tabelas existem
    print("\n4️⃣ Verificando tabelas...")
    tables_query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'kinghost_octadesk' 
    AND table_name IN ('chat', 'mensagens')
    LIMIT 5
    """
    df_tables = pd.read_sql_query(tables_query, conn)
    print(f"✅ Tabelas encontradas: {len(df_tables)} tabelas")
    for table in df_tables['table_name']:
        print(f"   - {table}")
    
    # Teste 5: Query com limite
    print("\n5️⃣ Testando query dos dados com LIMIT...")
    limited_query = """
    SELECT COUNT(*) as total
    FROM kinghost_octadesk.chat c 
    WHERE data_inicio_interacao >= CURRENT_DATE - INTERVAL '1 day'
    """
    df_count = pd.read_sql_query(limited_query, conn)
    print(f"✅ Registros último dia: {df_count.iloc[0]['total']}")
    
    print("\n🎉 TODOS OS TESTES PASSARAM! A conexão está funcionando.")
    
    conn.close()
    engine.dispose()
    
except Exception as e:
    print(f"\n❌ ERRO: {str(e)}")
    print(f"Tipo do erro: {type(e).__name__}")
    sys.exit(1)
