"""
Validador de CSV - Verifica integridade do arquivo antes do processamento.

Uso: python validate_csv.py
"""

import pandas as pd
from pathlib import Path
import sys

def validate_csv(file_path: Path) -> bool:
    """
    Valida a estrutura e conteúdo do arquivo CSV.
    
    Args:
        file_path: Caminho para o arquivo CSV
        
    Returns:
        True se válido, False caso contrário
    """
    
    print(f"\n{'='*60}")
    print(f"Validando CSV: {file_path.name}")
    print(f"{'='*60}\n")
    
    # Verificação 1: Arquivo existe
    if not file_path.exists():
        print(f"❌ ERRO: Arquivo não encontrado: {file_path}")
        return False
    print(f"✅ Arquivo encontrado")
    
    # Verificação 2: Leitura básica
    try:
        df = pd.read_csv(file_path, encoding='utf-8')
        print(f"✅ Arquivo lido com sucesso")
    except Exception as e:
        print(f"❌ ERRO ao ler arquivo: {e}")
        return False
    
    # Verificação 3: Colunas esperadas
    expected_columns = ['AnoMes', 'Clientes', 'Contatos', 'Contact Rate (%)']
    if not all(col in df.columns for col in expected_columns):
        print(f"❌ ERRO: Colunas faltando ou incorretas")
        print(f"   Esperado: {expected_columns}")
        print(f"   Encontrado: {list(df.columns)}")
        return False
    print(f"✅ Colunas válidas: {list(df.columns)}")
    
    # Verificação 4: Linhas de dados
    if len(df) == 0:
        print(f"❌ ERRO: Arquivo vazio (sem dados)")
        return False
    print(f"✅ Total de linhas: {len(df)}")
    
    # Verificação 5: Sem valores nulos em colunas importantes
    for col in expected_columns:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            print(f"⚠️  AVISO: {null_count} valores nulos na coluna '{col}'")
    
    # Verificação 6: Amostra de dados
    print(f"\n📊 Primeiras linhas do arquivo:")
    print(df.head(3).to_string(index=False))
    
    # Verificação 7: Tipos de dados
    print(f"\n📋 Tipos de dados detectados:")
    for col in expected_columns:
        print(f"   {col}: {df[col].dtype}")
    
    # Verificação 8: Validação de formato
    print(f"\n🔍 Validação de formatos:")
    
    try:
        # Validar data
        dates = pd.to_datetime(df['AnoMes'], format="%Y/%m", errors='coerce')
        invalid_dates = dates.isnull().sum()
        if invalid_dates > 0:
            print(f"   ⚠️  {invalid_dates} datas inválidas (formato esperado: YYYY/MM)")
        else:
            print(f"   ✅ Datas válidas")
    except Exception as e:
        print(f"   ❌ Erro ao validar datas: {e}")
    
    # Validar números
    try:
        clientes = pd.to_numeric(df['Clientes'].astype(str).str.replace('.', ''), errors='coerce')
        invalid_num = clientes.isnull().sum()
        if invalid_num > 0:
            print(f"   ⚠️  {invalid_num} valores inválidos em 'Clientes'")
        else:
            print(f"   ✅ Coluna 'Clientes' válida")
    except Exception as e:
        print(f"   ❌ Erro ao validar 'Clientes': {e}")
    
    try:
        contatos = pd.to_numeric(df['Contatos'].astype(str).str.replace('.', ''), errors='coerce')
        invalid_num = contatos.isnull().sum()
        if invalid_num > 0:
            print(f"   ⚠️  {invalid_num} valores inválidos em 'Contatos'")
        else:
            print(f"   ✅ Coluna 'Contatos' válida")
    except Exception as e:
        print(f"   ❌ Erro ao validar 'Contatos': {e}")
    
    # Validar percentual
    try:
        rates = df['Contact Rate (%)'].astype(str)
        has_percent = rates.str.contains('%', regex=False).all()
        if not has_percent:
            print(f"   ⚠️  Nem todos valores contêm símbolo '%'")
        else:
            print(f"   ✅ Coluna 'Contact Rate (%)' válida")
    except Exception as e:
        print(f"   ❌ Erro ao validar 'Contact Rate (%)': {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ CSV VÁLIDO - Pronto para processamento")
    print(f"{'='*60}\n")
    
    return True

if __name__ == '__main__':
    csv_path = Path(__file__).resolve().parent / 'Contact Rate_ Suporte N1.csv'
    
    if validate_csv(csv_path):
        sys.exit(0)
    else:
        sys.exit(1)
