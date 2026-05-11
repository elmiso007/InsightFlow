INSERT INTO public.dados_gh 
(mes, empresa_func, razao_social, cnpj, matricula, nome, admissao, cargo, macro_cargo, gh_funcionario,
 desc_gh_funcionario, nome_gestor, cc, desc_cc, data_nascimento, email_corporativo, situacao, sexo, 
 diretoria_gh, login, data_gh, nivel_carreira)
SELECT 
    A.mes::TIMESTAMP,
    A.empresa_func::VARCHAR,
    A.razao_social::VARCHAR,
    A.cnpj::VARCHAR,
    A.matricula::INTEGER,
    A.nome::VARCHAR,
    A.admissao::TIMESTAMP,
    A.cargo::VARCHAR,
    A.macro_cargo::VARCHAR,
    A.gh_funcionario::VARCHAR,
    A.desc_gh_funcionario::VARCHAR,
    A.nome_gestor::VARCHAR,
    A.cc::VARCHAR,
    A.desc_cc::VARCHAR,
    A.data_nascimento::TIMESTAMP,
    A.email_corporativo::VARCHAR,
    A.situacao::VARCHAR,
    A.sexo::VARCHAR,
    A.diretoria_gh::VARCHAR,
    LOWER(SPLIT_PART(email_corporativo, '@', 1)) AS login,
    A.data_gh::TIMESTAMP,
    A.nivel_carreira::TEXT
FROM public.stg_dados_gh A
