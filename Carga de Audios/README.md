# Pipeline de Carga de Áudios

Baixa gravações telefônicas do Yeastar PBX, transcreve com faster-whisper e persiste os resultados no banco PG17 para consumo pelo **Feedback Woz-Analista**.

---

## Visão geral

```
Yeastar PBX
    │
    │  REST API (search + download)
    ▼
pipeline.py  ──►  yeastar_client.py   (autenticação, busca, download)
    │
    ├──►  transcricao.py              (faster-whisper)
    │
    └──►  conecta_banco.py  ──►  PG17 · lw_octadesk.gravacoes_telefone
                                        │
                                        └──► Feedback Woz-Analista (leitura)
```

Esta pipeline é o **Pipeline A** da arquitetura de NPS telefônico:

| Pipeline | Responsabilidade |
|---|---|
| **A — Carga de Áudios** (este projeto) | Baixa áudios do Yeastar, transcreve e grava no PG17 |
| **B — Feedback Woz-Analista** | Lê transcrições do PG17 e gera análise de NPS com Gemini |

---

## Estrutura do projeto

```
Carga de Audios/
├── pipeline.py          # Orquestrador principal — entry point do agendamento
├── yeastar_client.py    # Cliente REST Yeastar (auth, busca, download)
├── transcricao.py       # Wrapper faster-whisper com carregamento lazy do modelo
├── conecta_banco.py     # Conexão e operações no PG17
├── config.py            # Configurações centralizadas (lê do .env)
├── requirements.txt     # Dependências Python
├── .env                 # Credenciais e parâmetros (NÃO versionar)
├── .env.example         # Template do .env
├── create_tables.sql    # DDL da tabela gravacoes_telefone
├── logs/                # Logs rotativos (criado automaticamente)
└── temp_audio/          # Áudios temporários, apagados após transcrição (criado automaticamente)
```

---

## Pré-requisitos

- Python 3.10+
- Acesso à rede interna da Locaweb (VPN ou rede corporativa) para o Yeastar
- Credenciais do banco PG17
- *(Opcional)* GPU NVIDIA para transcrição acelerada

---

## Instalação

```bash
# 1. Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar credenciais
copy .env.example .env
# Editar o .env com as credenciais reais
```

---

## Configuração

Edite o arquivo `.env` com os valores corretos:

### Yeastar PBX

| Variável | Descrição | Exemplo |
|---|---|---|
| `YEASTAR_URL` | URL base do portal Yeastar | `https://locaweb.ras.yeastar.com` |
| `YEASTAR_USER` | Usuário de acesso à API | `1014` |
| `YEASTAR_PASS` | Senha em texto plano (a pipeline faz o hash) | `MinhaSenh@` |

> A senha é automaticamente convertida para `Base64(MD5(senha))` antes de ser enviada ao Yeastar.

### Banco PG17

| Variável | Descrição |
|---|---|
| `DB17_HOST` | Host do PostgreSQL 17 |
| `DB17_PORT` | Porta (padrão: `5432`) |
| `DB17_NAME` | Nome do banco |
| `DB17_USER` | Usuário |
| `DB17_PASS` | Senha |
| `DB17_SCHEMA` | Schema da tabela (padrão: `lw_octadesk`) |

### Transcrição

| Variável | Descrição | Valores possíveis |
|---|---|---|
| `WHISPER_MODEL` | Tamanho do modelo Whisper | `tiny`, `base`, `small`, `medium`, `large-v2`, `large-v3` |
| `WHISPER_DEVICE` | Hardware de inferência | `cpu`, `cuda` |
| `WHISPER_LANGUAGE` | Idioma fixo (evita detecção automática) | `pt`, `en`, *(vazio = detecta automaticamente)* |

> **Recomendação:** `medium` + `cpu` é o melhor equilíbrio para servidores sem GPU. Em produção com GPU, use `large-v3` + `cuda`.

### Pipeline

| Variável | Descrição | Padrão |
|---|---|---|
| `PERIODO_HORAS` | Janela de busca no Yeastar a cada execução | `24` |
| `TEMP_DIR` | Diretório para áudios temporários | `temp_audio` |
| `LOG_LEVEL` | Nível de log no console | `INFO` |

---

## Banco de dados

### Criar a tabela

Execute o script DDL no banco PG17:

```bash
psql -h <DB17_HOST> -U <DB17_USER> -d <DB17_NAME> -f create_tables.sql
```

### Esquema da tabela `gravacoes_telefone`

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | BIGSERIAL | PK autoincrementada |
| `call_id` | TEXT UNIQUE | ID da gravação no Yeastar — chave de idempotência |
| `arquivo_original` | TEXT | Nome do arquivo no PBX |
| `iniciada_em` | TIMESTAMPTZ | Início da chamada |
| `encerrada_em` | TIMESTAMPTZ | Fim da chamada |
| `duracao_segundos` | INTEGER | Duração em segundos |
| `ramal_agente` | TEXT | Ramal (extensão) do analista |
| `agente` | TEXT | Nome do analista |
| `transcricao_texto` | TEXT | Texto completo da transcrição |
| `transcricao_raw` | JSONB | Segmentos com timestamps e metadados do Whisper |
| `transcricao_idioma` | TEXT | Idioma detectado |
| `transcricao_modelo` | TEXT | Modelo Whisper utilizado |
| `nps_velocidade` | NUMERIC | Nota NPS — preenchida pelo Pipeline B |
| `nps_solucao` | NUMERIC | Nota NPS — preenchida pelo Pipeline B |
| `nps_relacionamento` | NUMERIC | Nota NPS — preenchida pelo Pipeline B |
| `classificacao_nps` | TEXT | Promotor / Neutro / Detrator — Pipeline B |
| `criado_em` | TIMESTAMPTZ | Data de inserção pelo Pipeline A |

---

## Uso

### Execução manual

```bash
# Processa as últimas 24 horas (padrão do .env)
python pipeline.py

# Sobrescreve a janela de tempo
python pipeline.py --horas 48

# Período fixo (reprocessamento ou backfill)
python pipeline.py --inicio 2026-07-01 --fim 2026-07-08
```

### Saída esperada

```
10:00:00 - INFO - ============================================================
10:00:00 - INFO - PIPELINE CARGA DE ÁUDIOS — INICIANDO
10:00:00 - INFO - ============================================================
10:00:00 - INFO - Período: 2026-07-07 10:00 → 2026-07-08 10:00
10:00:01 - INFO - Login Yeastar OK.
10:00:02 - INFO - 12 gravação(ões) encontrada(s) entre ...
10:00:02 - INFO - [1/12] Processando 20260708-100012-1234...
10:00:08 - INFO - ✓ 20260708-100012-1234 | 185s | 1842 chars
...
10:03:15 - INFO - CONCLUÍDO — OK: 10 | Puladas: 2 | Erros: 0 | Total: 12
```

---

## Agendamento (Windows Task Scheduler)

1. Abra o **Agendador de Tarefas** (`taskschd.msc`)
2. Crie uma nova tarefa básica:
   - **Gatilho:** Diariamente, às 06:00
   - **Ação:** Iniciar um programa
     - **Programa:** `C:\Users\emerson.ramos\Desktop\projetos\Carga de Audios\.venv\Scripts\python.exe`
     - **Argumentos:** `pipeline.py`
     - **Iniciar em:** `C:\Users\emerson.ramos\Desktop\projetos\Carga de Audios`
3. Em **Condições**, desmarque "Iniciar somente se o computador estiver alimentado por CA"

> **Dica:** Para execuções a cada hora, use o gatilho "Repetir a tarefa a cada 1 hora por 1 dia".

---

## Autenticação Yeastar

### Fluxo

```
pipeline.py
    │
    └─► YeastarClient.login()
            │
            ├─ POST /api/v1.0/login  { username, password: Base64(MD5(pass)) }
            │
            ├─ status == "Success"  ──► token salvo, pronto para usar
            │
            └─ status == "need_verify"  ──► POST /api/v1.0/tfaverify
                                               { trust_device: 1 }
                                               ──► token salvo
```

### Primeira execução com 2FA

Na primeira vez em um novo ambiente (máquina/IP), o Yeastar pode exigir verificação de dois fatores. Nesse caso:

1. Execute `python pipeline.py` — a pipeline iniciará a verificação 2FA
2. Você receberá um código por e-mail ou SMS no ramal `1014`
3. Edite `yeastar_client.py` em `_verificar_tfa()` e adicione o campo `code` com o valor recebido
4. Execute novamente — após isso, `trust_device=1` dispensa verificações futuras nesse ambiente

---

## Desempenho e modelos Whisper

| Modelo | Tamanho | RAM (CPU) | Qualidade | Velocidade (CPU) |
|---|---|---|---|---|
| `tiny` | 75 MB | ~1 GB | Baixa | Muito rápida |
| `base` | 145 MB | ~1 GB | Razoável | Rápida |
| `small` | 461 MB | ~2 GB | Boa | Moderada |
| `medium` | 1.4 GB | ~4 GB | **Muito boa** ← recomendado | ~2-4× tempo real |
| `large-v3` | 2.9 GB | ~8 GB | Excelente | ~6-8× tempo real (CPU) |

> "2× tempo real" significa que uma ligação de 5 minutos leva ~10 minutos para transcrever em CPU.

---

## Logs

Os logs são armazenados em `logs/pipeline.log` com rotação automática (10 MB por arquivo, 5 arquivos de backup).

Para acompanhar em tempo real:
```bash
# Windows PowerShell
Get-Content logs\pipeline.log -Wait -Tail 50
```

---

## Integração com Feedback Woz-Analista

O **Feedback Woz-Analista** (Pipeline B) lê desta tabela os registros onde `transcricao_texto IS NOT NULL`, identifica os analistas com NPS baixo por ramal e gera análise com Gemini.

A coluna `classificacao_nps` é preenchida pelo Pipeline B quando há dados de NPS associados à gravação (via protocolo ou período de atendimento).