-- v2.0 プラン構造更新
-- Free: 独自お題10件・Dashboard有効
-- Light: 独自お題100件
-- Pro: 独自お題1000件・タグ機能

UPDATE plans SET
  custom_odai_base = 10,
  custom_odai_max  = 10,
  has_dashboard    = 1
WHERE name = 'free';

UPDATE plans SET
  custom_odai_base = 100,
  custom_odai_max  = NULL
WHERE name = 'light';

UPDATE plans SET
  custom_odai_base = 1000,
  custom_odai_max  = NULL
WHERE name = 'pro';

-- 既存のFreeプランguildの容量を0→10に更新
UPDATE guild_plans gp
JOIN plans p ON gp.plan_id = p.id
SET gp.custom_odai_capacity = 10
WHERE p.name = 'free' AND gp.custom_odai_capacity = 0;
