INSERT INTO tray.stg_tickets_interactions 
SELECT
    NULLIF(TRIM(number), '')::INTEGER AS number,
    NULLIF(TRIM(interaction_id), '')::VARCHAR AS interaction_id,
    created_at AS created_at,
    NULLIF(TRIM(user_id), '')::VARCHAR AS user_id,
    NULLIF(TRIM(user_name), '')::VARCHAR AS user_name,
    NULLIF(TRIM(user_email), '')::VARCHAR AS user_email,
    NULLIF(TRIM(user_type), '')::VARCHAR AS user_type,
    NULLIF(TRIM(comments_content), '')::TEXT AS comments_content,
    NULLIF(TRIM(comments_type), '')::VARCHAR AS comments_type,
    CASE 
        WHEN comments_is_public::VARCHAR = 'true' THEN TRUE
        WHEN comments_is_public::VARCHAR = 'false' THEN FALSE
        ELSE NULL 
    END AS is_public_comment,
    NULLIF(TRIM(pc_channel_name), '')::VARCHAR AS channel_name,
    NULLIF(TRIM(pc_priority_name), '')::VARCHAR AS priority_name,
    NULLIF(TRIM(pc_group_assigned_name), '')::VARCHAR AS group_assigned_name,
    NULLIF(TRIM(pc_requester_name), '')::VARCHAR AS requester_name,
    NULLIF(TRIM(pc_organization_name), '')::VARCHAR AS organization_name,
    NULLIF(TRIM(pc_tags), '')::VARCHAR AS tags,
    NULLIF(TRIM(pc_status), '')::VARCHAR AS status,
    NULLIF(TRIM(pc_departamento), '')::VARCHAR AS department,
    NULLIF(TRIM(pc_type_name), '')::VARCHAR AS type_name,
    NULLIF(TRIM(pc_cc), '')::VARCHAR AS cc,
    NULLIF(TRIM(pc_form), '')::VARCHAR AS form_name,
    NOW() AS data_insercao,
    NOW() AS data_modificacao,
    'api_octadesk' AS source
FROM tray.payload_tickets_interactions;
