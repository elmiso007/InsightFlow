INSERT INTO public.c_gh (
    mes, emp_mat, nome_sobrenome, nome, cargo, situacao, gestor,
    centro_de_custo, desc_cc, admissao, empresa, matricula, equipe,
    lider_bdo, funcao, carga_horaria, rotacao, data_nascimento, upgrade
)
SELECT 
    mes, emp_mat, nome_sobrenome, nome, cargo, situacao, gestor,
    centro_de_custo, desc_cc, admissao, empresa, matricula, equipe,
    lider_bdo, funcao, carga_horaria, rotacao, data_nascimento, upgrade
FROM public.stg_c_gh
WHERE NOT EXISTS (
    SELECT 1
    FROM public.c_gh
    WHERE c_gh.mes = stg_c_gh.mes
);