import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime,timedelta
import psycopg2
import numpy as np

# Set up PostgreSQL connection
server = '10.30.138.28'
database = 'report_requesttracker'
uid = 'a_report'
pwd = 'Eequ8ohc'
engine_conn_string = f"postgresql://{uid}:{pwd}@{server}/{database}"
engine = create_engine(engine_conn_string)
connection = engine.connect()

try:

    df = pd.read_excel(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\octadesk-conversas\Total de conversas.xlsx')

    def serializar_dataframe(df):
        mapeamento_colunas = {
            "ID":"protocolo",
            "Status conversa":"status",
            "Nome do solicitante":"nome_solicitante",
            "E-mail do solicitante":"email_solicitante",
            "Telefone do solicitante":"telefone_solicitante",
            "Organização do solicitante":"organizacao",
            "Data e hora de entrada":"data_inicio",
            "Data e hora de encerramento":"data_final",
            "Tempo de espera":"tempoemespera",
            "Duração da conversa":"duracao",
            "Responsável da conversa":"responsavel",
            "Participantes da conversa":"analista",
            "Grupo responsável da conversa":"grupo_responsavel",
            "Total de interações":"interacoes",
            "Origem da conversa":"origem_conversa",
            "Pesquisa de satisfação":"status_pesquisa",
            "Comentário da pesquisa":"comentario_pesquisa",
            "Ticket da conversa":"ticket",
            "Fluxos / Bots":"fluxo_bots",
            "Tags":"tags",
            "Tempo de espera após atribuição":"tempo_espera_apos_atribuicao",
            "octabsp":"octabsp",
            "id-conversa":"id_conversa",
            "numero-conversa":"numero_conversa",
            "primeira-mensagem-cliente":"primeira_mensagem_cliente",
            "tamanho-empresa":"tamanho_empresa",
            "customField.v2-cnpj":"customfield_v2_cnpj",
            "customField.v2-motivo-financeiro":"customfield_v2_motivo_financeiro",
            "customField.v2-faturaematraso":"customfield_v2_faturaematraso",
            "CNPJ":"cnpj",
            "motivo-financeiro":"motivo_financeiro",
            "360dialog":"dialog360",
            "octadesk":"octadesk",
            "socialminer":"socialminer",
            "nomedaempresa":"nomedaempresa",
            "undefined":"undefined",
            "motivo-de-contato":"motivo_de_contato",
            "nome-empresa":"nome_empresa",
            "email-agente":"email_agente",
            "descrição-atendimento":"descricao_atendimento",
            "customField.nome_contato":"customfield_nome_contato",
            "customField.n":"customfield",
            "sitedaempresa":"sitedaempresa",
            "SYSTEN_INFORMATION_AUTHORIZATION":"system_information_authorization",
            "SYSTEN_INFORMATION_SUBDOMAIN":"system_information_subdomain",
            "SYSTEN_INFORMATION_NOW":"system_information_now",
            "divulgacaooctanapratica":"divulgacaooctanapratica",
            "customField.CNPJ":"customfieldcnpj",
            "Melhorhorariooctanapratica":"melhorhorariooctanapratica",
            "utm-source":"utm_source",
            "utm-medium":"utm_medium",
            "utm-campaign":"utm_campaign",
            "utm-term":"utm_term",
            "utm-content":"utm_content",
            "hubspotutk":"hubspotutk",
            "Subdomínio Octadesk":"subdominio_octadesk",
            "Cluster":"cluster",
            "Código do Plano":"codigo_plano",
            "MRR":"mrr",
            "Data de criação do ambiente":"data_criacao_ambiente",
            "Data de contratação":"data_contratacao",
            "Perfil do usuário":"perfil_do_usuario",
            "canal-que-preferem-receber-comunicacoes":"canal_que_preferem_receber_comunicacoes",
            "Temadeinteresse-octanapratica":"temadeinteresse_octanapratica"
        }

        # Renomear colunas
        df = df.rename(columns=mapeamento_colunas)

        # Garantir que todas as colunas estejam presentes
        todas_colunas = list(mapeamento_colunas.values()) + ['participante']
        for col in todas_colunas:
            if col not in df.columns:
                df[col] = None

        # Reordenar colunas
        df = df[todas_colunas]

        return df

    df_serializado = serializar_dataframe(df)

    print(df_serializado.head())

    df_serializado['data_inicio'] = pd.to_datetime(df_serializado['data_inicio'], format='%d/%m/%Y %H:%M')
    df_serializado['data_inicio'] = df_serializado['data_inicio'].dt.strftime('%Y-%m-%d %H:%M:%S')
    df_serializado['data_final'] = pd.to_datetime(df_serializado['data_final'], format='%d/%m/%Y %H:%M', errors='coerce')
    df_serializado['data_final'] = df_serializado['data_final'].dt.strftime('%Y-%m-%d %H:%M:%S')

    df_serializado['tempoemespera'] = df_serializado['tempoemespera'].replace('-', np.nan)
    df_serializado['telefone_solicitante'] = df_serializado['telefone_solicitante'].replace('-', np.nan)
    df_serializado['organizacao'] = df_serializado['organizacao'].replace('-', np.nan)
    df_serializado['duracao'] = df_serializado['duracao'].replace('-', np.nan)
    df_serializado['responsavel'] = df_serializado['responsavel'].replace('-', np.nan)
    df_serializado['analista'] = df_serializado['analista'].replace('-', np.nan)
    df_serializado['grupo_responsavel'] = df_serializado['grupo_responsavel'].replace('-', np.nan)
    df_serializado['tags'] = df_serializado['tags'].replace('-', np.nan)
    df_serializado['comentario_pesquisa'] = df_serializado['comentario_pesquisa'].replace('-', np.nan)
    df_serializado['ticket'] = df_serializado['ticket'].replace('-', np.nan)
    df_serializado['fluxo_bots'] = df_serializado['fluxo_bots'].replace('-', np.nan)
    df_serializado['tempo_espera_apos_atribuicao'] = df_serializado['tempo_espera_apos_atribuicao'].replace('-', np.nan)


    df_serializado.to_sql('stg_conversas', con=engine,if_exists='replace', index=False, schema='octadesk')

    total_linhas_inseridas = 0

    with open(r'C:\Users\lucas.abner\Desktop\Rotinas Python\Octadesk\octadesk-conversas\INSERT.sql', 'r', encoding='utf-8') as file:
        query_insercao = text(file.read())

    result = connection.execute(query_insercao)
    linhas_inseridas = result.rowcount
    total_linhas_inseridas += linhas_inseridas  # Contagem de linhas inseridas
    connection.commit()
    print(f"{total_linhas_inseridas} linhas inseridas na tabela octadesk.s_conversas.")


except Exception as e:
    print("Ocorreu um erro:", e)

connection.close()
engine.dispose