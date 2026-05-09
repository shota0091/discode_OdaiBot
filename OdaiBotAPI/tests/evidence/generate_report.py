"""テストエビデンス HTML レポート生成スクリプト。"""
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import OrderedDict
from datetime import datetime

# ─────────────────────────────────────────────────────────────
# ファイル別ラベル定義
# ─────────────────────────────────────────────────────────────
FILE_LABELS = {
    "test_auth":          ("認証 API（ギルド）",      "POST /auth/login, /register, /invite, /invite/create; PUT|DELETE /users/{id}; GET /users"),
    "test_auth_global":   ("認証 API（グローバル）",  "POST /api/auth/login; GET /api/auth/guilds"),
    "test_auth_users":    ("ユーザー管理 API",        "POST /auth/reset-password, /users/{id}/ban, /unban, /unlock; GET|DELETE /bans; GET|DELETE /invites; GET /users/{id}/profile"),
    "test_deps":          ("共通依存関数",             "hash_password / verify_password / normalize_tags / get_guild_plan / require_pro_plan / require_dashboard_plan / check_odai_capacity"),
    "test_odai":          ("お題 API（基本）",         "GET /odai; POST /odai; PUT /odai/{id}; DELETE /odai/{id}"),
    "test_odai_extra":    ("お題 API（追加）",         "GET /odai/{id}/history; GET /odai/{id}/usage; GET /odai/{id}/image; POST /odai/import; PUT /odai/{id}（エッジケース）"),
    "test_plan_gates":    ("プランゲート統合テスト",   "require_pro_plan / require_dashboard_plan の実際の HTTP 挙動"),
    "test_plan_schedule": ("Free プランスケジュール",  "GET|PUT|DELETE /plan-schedule"),
    "test_schedules":     ("通常スケジュール API",     "GET /schedules; POST /schedules; PUT /schedules/{id}; DELETE /schedules/{id}"),
    "test_settings":      ("Guild 設定 API（基本）",   "GET|PUT /settings"),
    "test_settings_extra":("Guild 設定 API（追加）",   "GET /settings/name; GET /settings/channels"),
    "test_stripe":        ("Stripe 決済 API",          "GET /stripe/plan; POST /stripe/webhook; POST /stripe/checkout; POST /stripe/expand"),
    "test_summary":       ("ダッシュボードサマリー",   "GET /dashboard-summary"),
    "test_tags":          ("タグ API（基本）",          "GET /tags; POST /tags; PUT /tags/{id}; DELETE /tags/{id}"),
    "test_tags_extra":    ("タグ API（追加）",          "GET /tags/{id}/detail"),
    "test_test_post":     ("テスト投稿 API",            "POST /test-post"),
    "test_rate_limit":    ("レートリミッター",           "POST /auth/login（10回/分）、POST /auth/reset-password（5回/分）"),
}

N = "正常系"
A = "異常系"

# ─────────────────────────────────────────────────────────────
# テストケース説明定義 (想定ケース, 想定結果, 種別)
# ─────────────────────────────────────────────────────────────
DESCRIPTIONS = {
    # ── test_auth ──────────────────────────────────────────────
    "TestLogin::test_success":                               ("正しいユーザー名・パスワードでログイン",              "200 OK：JWT トークン・ロール返却",          N),
    "TestLogin::test_wrong_password_returns_401":            ("誤ったパスワードでログイン",                         "401 Unauthorized",                          A),
    "TestLogin::test_user_not_found_returns_401":            ("存在しないユーザーでログイン",                        "401 Unauthorized",                          A),
    "TestRegister::test_success":                            ("有効な招待トークンで新規登録",                        "200 OK：api_token 返却",                    N),
    "TestRegister::test_short_password_returns_400":         ("8 文字未満のパスワードで登録",                        "400 Bad Request",                           A),
    "TestRegister::test_invalid_token_returns_404":          ("無効な招待トークンで登録",                            "404 Not Found",                             A),
    "TestRegister::test_duplicate_username_returns_409":     ("既存ユーザー名で登録",                               "409 Conflict",                              A),
    "TestCreateInvite::test_success":                        ("管理者が招待リンクを作成",                            "200 OK：invite_token 返却",                 N),
    "TestCreateInvite::test_invalid_role_returns_400":       ("無効なロール指定で招待作成",                          "400 Bad Request",                           A),
    "TestCreateInvite::test_duplicate_username_returns_409": ("既存ユーザー名で招待作成",                           "409 Conflict",                              A),
    "TestListUsers::test_success":                           ("管理者がユーザー一覧取得",                            "200 OK：ユーザーリスト返却",                N),
    "TestCreateUser::test_success_first_user":               ("最初のユーザーを管理者として作成",                    "200 OK：api_token 返却",                    N),
    "TestCreateUser::test_short_password_returns_400":       ("8 文字未満のパスワードでユーザー作成",               "400 Bad Request",                           A),
    "TestCreateUser::test_duplicate_username_returns_409":   ("既存ユーザー名でユーザー作成",                       "409 Conflict",                              A),
    "TestUpdateUser::test_success":                          ("管理者がユーザー情報を更新",                          "200 OK",                                    N),
    "TestUpdateUser::test_not_found_returns_404":            ("存在しないユーザーを更新",                            "404 Not Found",                             A),
    "TestUpdateUser::test_no_update_fields_returns_400":     ("更新フィールド未指定で更新リクエスト",                "400 Bad Request",                           A),
    "TestDeleteUser::test_success":                          ("管理者がユーザーを削除",                              "200 OK",                                    N),
    "TestDeleteUser::test_self_delete_returns_400":          ("自分自身を削除しようとする",                          "400 Bad Request",                           A),
    "TestDeleteUser::test_not_found_returns_404":            ("存在しないユーザーを削除",                            "404 Not Found",                             A),

    # ── test_auth_global ───────────────────────────────────────
    "TestGlobalLogin::test_success":                         ("グローバルエンドポイントで正しい認証情報でログイン",   "200 OK：JWT トークン・所属ギルド返却",      N),
    "TestGlobalLogin::test_wrong_password_returns_401":      ("グローバルログインで誤ったパスワード",                "401 Unauthorized",                          A),
    "TestGlobalLogin::test_user_not_found_returns_401":      ("グローバルログインで存在しないユーザー",              "401 Unauthorized",                          A),
    "TestGlobalLogin::test_no_guilds_returns_403":           ("どのギルドにも所属しないユーザーでログイン",          "403 Forbidden",                             A),
    "TestGlobalLogin::test_display_name_in_response":        ("display_name が設定されているユーザーでログイン",    "200 OK：display_name フィールド含む",       N),
    "TestListGuilds::test_success":                          ("有効なトークンでギルド一覧取得",                      "200 OK：ギルドリスト返却",                  N),
    "TestListGuilds::test_no_token_returns_401":             ("トークンなしでギルド一覧取得",                        "401 Unauthorized",                          A),
    "TestListGuilds::test_invalid_token_returns_401":        ("無効なトークンでギルド一覧取得",                      "401 Unauthorized",                          A),
    "TestListGuilds::test_multiple_guilds":                  ("複数ギルドに所属するユーザーのギルド一覧",            "200 OK：複数ギルド返却",                    N),

    # ── test_auth_users ────────────────────────────────────────
    "TestResetPassword::test_success":                       ("有効なリセットトークンで新しいパスワードを設定",      "200 OK",                                    N),
    "TestResetPassword::test_invalid_token_returns_404":     ("無効なリセットトークンでパスワードリセット",          "404 Not Found",                             A),
    "TestResetPassword::test_user_not_found_returns_404":    ("トークンに紐づくユーザーが存在しない",               "404 Not Found",                             A),
    "TestResetPassword::test_short_password_returns_400":    ("8 文字未満の新しいパスワードで設定",                 "400 Bad Request",                           A),
    "TestGetInviteInfo::test_success":                       ("有効な招待トークンで招待情報を取得",                  "200 OK：username / guild_name 返却",        N),
    "TestGetInviteInfo::test_invalid_token_returns_404":     ("無効な招待トークンで招待情報取得",                   "404 Not Found",                             A),
    "TestListBans::test_success":                            ("管理者が BAN リストを取得",                           "200 OK：BAN ユーザーリスト返却",            N),
    "TestListBans::test_empty_list":                         ("BAN されているユーザーが 0 名の場合",                 "200 OK：空リスト返却",                      N),
    "TestListBans::test_unauthenticated_returns_401":        ("未認証で BAN リスト取得",                             "401 Unauthorized",                          A),
    "TestListBans::test_non_admin_returns_403":              ("一般ユーザーが BAN リスト取得",                       "403 Forbidden",                             A),
    "TestRemoveBan::test_success":                           ("管理者が BAN を解除",                                 "200 OK",                                    N),
    "TestRemoveBan::test_not_found_returns_404":             ("存在しない BAN エントリを解除",                       "404 Not Found",                             A),
    "TestRemoveBan::test_non_admin_returns_403":             ("一般ユーザーが BAN 解除",                             "403 Forbidden",                             A),
    "TestListInvites::test_success":                         ("管理者が招待リスト取得",                              "200 OK：招待リスト返却",                    N),
    "TestListInvites::test_empty_list":                      ("招待が 0 件の場合",                                   "200 OK：空リスト返却",                      N),
    "TestListInvites::test_non_admin_returns_403":           ("一般ユーザーが招待リスト取得",                        "403 Forbidden",                             A),
    "TestRevokeInvite::test_success":                        ("管理者が招待を失効させる",                            "200 OK",                                    N),
    "TestRevokeInvite::test_not_found_returns_404":          ("存在しない招待を失効",                                "404 Not Found",                             A),
    "TestRevokeInvite::test_non_admin_returns_403":          ("一般ユーザーが招待失効",                              "403 Forbidden",                             A),
    "TestUnlockUser::test_success":                          ("管理者がロックされたユーザーを解錠",                  "200 OK",                                    N),
    "TestUnlockUser::test_not_found_returns_404":            ("存在しないユーザーを解錠",                            "404 Not Found",                             A),
    "TestUnlockUser::test_non_admin_returns_403":            ("一般ユーザーが解錠リクエスト",                        "403 Forbidden",                             A),
    "TestBanUser::test_success":                             ("管理者が対象ユーザーを BAN",                          "200 OK",                                    N),
    "TestBanUser::test_self_ban_returns_400":                ("管理者が自分自身を BAN",                              "400 Bad Request",                           A),
    "TestBanUser::test_user_not_found_returns_404":          ("存在しないユーザーを BAN",                            "404 Not Found",                             A),
    "TestBanUser::test_non_admin_returns_403":               ("一般ユーザーが BAN リクエスト",                       "403 Forbidden",                             A),
    "TestUnbanUser::test_success":                           ("管理者が BAN ユーザーを解除",                         "200 OK",                                    N),
    "TestUnbanUser::test_user_not_found_returns_404":        ("存在しないユーザーの BAN 解除",                       "404 Not Found",                             A),
    "TestUnbanUser::test_non_admin_returns_403":             ("一般ユーザーが BAN 解除リクエスト",                   "403 Forbidden",                             A),
    "TestGetUserProfile::test_admin_can_view_any_profile":   ("管理者が他ユーザーのプロフィールを取得",             "200 OK：プロフィール返却",                  N),
    "TestGetUserProfile::test_user_can_view_own_profile":    ("一般ユーザーが自分のプロフィールを取得",             "200 OK：プロフィール返却",                  N),
    "TestGetUserProfile::test_user_cannot_view_others_profile": ("一般ユーザーが他ユーザーのプロフィールを取得",    "403 Forbidden",                             A),
    "TestGetUserProfile::test_not_found_returns_404":        ("存在しないユーザーのプロフィールを取得",              "404 Not Found",                             A),
    "TestGetUserProfile::test_profile_includes_odai_and_tags": ("プロフィールにお題・タグ一覧が含まれること",        "200 OK：odai / tags フィールド含む",        N),
    "TestListUsersNonAdmin::test_non_admin_sees_only_own_data": ("一般ユーザーがユーザー一覧を取得",                "200 OK：自分のデータのみ返却",              N),
    "TestUpdateUserExtra::test_non_admin_cannot_update_other_user": ("一般ユーザーが他ユーザーを更新",              "403 Forbidden",                             A),
    "TestUpdateUserExtra::test_wrong_current_password_returns_401": ("誤った現パスワードでパスワード変更",           "401 Unauthorized",                          A),
    "TestUpdateUserExtra::test_missing_current_password_returns_400": ("現パスワード未指定でパスワード変更",         "400 Bad Request",                           A),
    "TestUpdateUserExtra::test_admin_can_change_role":       ("管理者が一般ユーザーのロールを変更",                  "200 OK",                                    N),

    # ── test_deps ──────────────────────────────────────────────
    "TestHashPassword::test_returns_salt_and_digest":        ("パスワードをハッシュ化しソルト+ダイジェスト形式で返却", "ソルト:ダイジェスト 形式の文字列",         N),
    "TestHashPassword::test_same_password_different_salts":  ("同じパスワードを 2 回ハッシュ化",                    "毎回異なるハッシュ値（ランダムソルト）",    N),
    "TestHashPassword::test_different_passwords_different_hashes": ("異なるパスワードをハッシュ化",                 "異なるハッシュ値",                          N),
    "TestVerifyPassword::test_correct_password":             ("正しいパスワードで検証",                              "True 返却",                                 N),
    "TestVerifyPassword::test_wrong_password":               ("誤ったパスワードで検証",                              "False 返却",                                A),
    "TestVerifyPassword::test_malformed_hash_returns_false": ("不正フォーマットのハッシュで検証",                    "False 返却（例外なし）",                    A),
    "TestVerifyPassword::test_empty_password":               ("空文字のパスワードで検証",                            "False 返却",                                A),
    "TestNormalizeTags::test_none_returns_empty_list":       ("None を渡す",                                         "空リスト返却",                              N),
    "TestNormalizeTags::test_comma_separated_string":        ("カンマ区切り文字列を渡す",                            "分割されたタグリスト返却",                  N),
    "TestNormalizeTags::test_string_with_spaces":            ("スペース入りタグ文字列を渡す",                        "トリム済みタグリスト返却",                  N),
    "TestNormalizeTags::test_list_input":                    ("リストを渡す",                                         "そのままリスト返却",                        N),
    "TestNormalizeTags::test_list_with_empty_strings":       ("空文字を含むリストを渡す",                            "空文字除去済みリスト返却",                  N),
    "TestNormalizeTags::test_empty_string":                  ("空文字列を渡す",                                       "空リスト返却",                              N),
    "TestNormalizeTags::test_single_tag":                    ("単一タグ文字列を渡す",                                 "要素 1 件のリスト返却",                     N),
    "TestGetGuildPlan::test_returns_plan_when_record_exists": ("プランレコードが存在する場合",                       "DB のプランレコード返却",                   N),
    "TestGetGuildPlan::test_falls_back_to_free_when_no_record": ("ギルドのプランレコードがない場合",                 "free プランのデフォルト値返却",             N),
    "TestGetGuildPlan::test_falls_back_to_empty_dict_when_plans_table_empty": ("plans テーブルが空の場合",           "空辞書にフォールバック",                    N),
    "TestRequireDashboardPlan::test_free_plan_raises_403":   ("free プランで dashboard_plan 要求",                   "403 Forbidden（HTTPException）",            A),
    "TestRequireDashboardPlan::test_light_plan_passes":      ("light プランで dashboard_plan 要求",                  "通過（例外なし）",                          N),
    "TestRequireDashboardPlan::test_pro_plan_passes":        ("pro プランで dashboard_plan 要求",                    "通過（例外なし）",                          N),
    "TestRequireProPlan::test_free_raises_403":              ("free プランで pro_plan 要求",                          "403 Forbidden（HTTPException）",            A),
    "TestRequireProPlan::test_light_raises_403":             ("light プランで pro_plan 要求",                         "403 Forbidden（HTTPException）",            A),
    "TestRequireProPlan::test_pro_passes":                   ("pro プランで pro_plan 要求",                           "通過（例外なし）",                          N),
    "TestRequireProPlan::test_enterprise_passes":            ("enterprise プランで pro_plan 要求",                   "通過（例外なし）",                          N),
    "TestCheckOdaiCapacity::test_null_capacity_is_unlimited": ("custom_odai_capacity=None の場合",                   "上限なし（通過）",                          N),
    "TestCheckOdaiCapacity::test_zero_capacity_raises_403":  ("容量 0 のギルドで登録",                               "403 Forbidden",                             A),
    "TestCheckOdaiCapacity::test_under_capacity_passes":     ("現在件数が上限未満",                                   "通過（例外なし）",                          N),
    "TestCheckOdaiCapacity::test_at_capacity_raises_403":    ("現在件数が上限と同数",                                 "403 Forbidden",                             A),
    "TestCheckOdaiCapacity::test_bulk_import_exceeding_capacity_raises_403": ("一括インポートで上限超過",             "403 Forbidden",                             A),

    # ── test_odai ──────────────────────────────────────────────
    "TestListOdai::test_success":                            ("お題一覧を取得",                                       "200 OK：お題リスト返却",                    N),
    "TestListOdai::test_filter_by_tag":                      ("タグ指定でお題一覧をフィルタ",                         "200 OK：タグ絞り込み結果返却",              N),
    "TestListOdai::test_filter_by_favorite":                 ("お気に入り指定でお題一覧をフィルタ",                   "200 OK：お気に入り絞り込み結果返却",        N),
    "TestListOdai::test_unauthenticated_returns_401":        ("未認証でお題一覧取得",                                  "401 Unauthorized",                          A),
    "TestUploadOdai::test_success":                          ("有効な画像ファイルをアップロード",                      "201 Created：お題データ返却",               N),
    "TestUploadOdai::test_invalid_content_type_returns_400": ("画像以外のファイルをアップロード",                     "400 Bad Request",                           A),
    "TestUploadOdai::test_file_too_large_returns_400":       ("上限サイズを超えるファイルをアップロード",              "400 Bad Request",                           A),
    "TestUploadOdai::test_duplicate_returns_409":            ("同名ファイルを再アップロード",                          "409 Conflict",                              A),
    "TestUpdateOdai::test_success":                          ("お題のメモ・タグ等を更新",                              "200 OK：更新後のお題データ返却",            N),
    "TestUpdateOdai::test_not_found_returns_404":            ("存在しないお題を更新",                                  "404 Not Found",                             A),
    "TestDeleteOdai::test_success":                          ("お題を削除",                                           "200 OK",                                    N),
    "TestDeleteOdai::test_not_found_returns_404":            ("存在しないお題を削除",                                  "404 Not Found",                             A),

    # ── test_odai_extra ────────────────────────────────────────
    "TestGetOdaiHistory::test_success":                      ("お題の操作履歴を取得",                                  "200 OK：履歴リスト・ページング情報返却",    N),
    "TestGetOdaiHistory::test_not_found_returns_404":        ("存在しないお題の履歴を取得",                            "404 Not Found",                             A),
    "TestGetOdaiHistory::test_pagination_params":            ("page=2, per_page=10 で履歴取得",                        "200 OK：指定ページ・件数で返却",            N),
    "TestGetOdaiHistory::test_per_page_clamped_to_50":       ("per_page=100 で履歴取得",                              "200 OK：per_page は 50 にクランプ",         N),
    "TestGetOdaiHistory::test_unauthenticated_returns_401":  ("未認証で履歴取得",                                      "401 Unauthorized",                          A),
    "TestGetOdaiUsage::test_success":                        ("お題の使用状況（チャンネル・日時）を取得",              "200 OK：使用履歴リスト返却",                N),
    "TestGetOdaiUsage::test_channel_id_is_string":           ("DB から整数型の channel_id が返る場合",                "レスポンスの channel_id が文字列型",        N),
    "TestGetOdaiUsage::test_not_found_returns_404":          ("存在しないお題の使用状況取得",                          "404 Not Found",                             A),
    "TestGetOdaiUsage::test_empty_usage":                    ("使用履歴が 0 件のお題",                                 "200 OK：空リスト返却",                      N),
    "TestGetOdaiUsage::test_unauthenticated_returns_401":    ("未認証で使用状況取得",                                  "401 Unauthorized",                          A),
    "TestGetOdaiImage::test_not_found_odai_returns_404":     ("存在しないお題の画像を取得",                            "404 Not Found",                             A),
    "TestGetOdaiImage::test_no_storage_path_returns_404":    ("storage_path が NULL のお題の画像取得",                "404 Not Found",                             A),
    "TestGetOdaiImage::test_file_not_on_disk_returns_404":   ("DB に storage_path あるがファイルが存在しない",         "404 Not Found",                             A),
    "TestGetOdaiImage::test_success_jpeg":                   ("JPEG ファイルの画像取得",                              "200 OK：Content-Type: image/jpeg",          N),
    "TestGetOdaiImage::test_success_png":                    ("PNG ファイルの画像取得",                               "200 OK：Content-Type: image/png",           N),
    "TestGetOdaiImage::test_success_webp":                   ("WebP ファイルの画像取得",                              "200 OK：Content-Type: image/webp",          N),
    "TestGetOdaiImage::test_unauthenticated_returns_401":    ("未認証で画像取得",                                      "401 Unauthorized",                          A),
    "TestImportOdai::test_success_single_file":              ("単一ファイルの一括インポート",                          "201 Created：success=true のレスポンス",    N),
    "TestImportOdai::test_duplicate_file_fails_gracefully":  ("既存ファイル名を一括インポート",                        "201 Created：success=false で継続（全体は失敗しない）", A),
    "TestImportOdai::test_partial_success_multiple_files":   ("複数ファイルのうち一部が重複",                          "201 Created：成功分は true、失敗分は false", N),
    "TestImportOdai::test_unauthenticated_returns_401":      ("未認証で一括インポート",                                "401 Unauthorized",                          A),
    "TestUpdateOdaiEdgeCases::test_filename_rename_conflict_returns_409": ("別お題と同名にリネーム",                   "409 Conflict",                              A),
    "TestUpdateOdaiEdgeCases::test_empty_filename_returns_400": ("空白のみのファイル名にリネーム",                     "400 Bad Request",                           A),
    "TestUpdateOdaiEdgeCases::test_memo_update":             ("お題のメモを更新",                                      "200 OK：更新後のお題データ返却",            N),
    "TestUpdateOdaiEdgeCases::test_soft_delete":             ("deleted=true でソフトデリート",                         "200 OK：deleted_at が設定される",           N),
    "TestUpdateOdaiEdgeCases::test_restore_odai":            ("deleted=false でソフトデリートを復元",                  "200 OK：deleted_at が NULL にリセット",     N),
    "TestUpdateOdaiEdgeCases::test_tags_update":             ("タグリストを新しいタグに更新",                          "200 OK：タグが更新される",                  N),
    "TestUpdateOdaiEdgeCases::test_filename_successful_rename": ("衝突しないファイル名にリネーム",                     "200 OK：新しいファイル名で返却",            N),

    # ── test_plan_gates ────────────────────────────────────────
    "TestDashboardPlanGate::test_free_plan_login_returns_403": ("free プランのギルドでダッシュボードログイン",         "403 Forbidden",                             A),
    "TestDashboardPlanGate::test_light_plan_login_succeeds": ("light プランのギルドでダッシュボードログイン",          "200 OK",                                    N),
    "TestDashboardPlanGate::test_pro_plan_login_succeeds":   ("pro プランのギルドでダッシュボードログイン",            "200 OK",                                    N),
    "TestProPlanGate::test_odai_list_free_returns_403":      ("free プランでお題一覧取得",                             "403 Forbidden",                             A),
    "TestProPlanGate::test_odai_list_light_returns_403":     ("light プランでお題一覧取得",                            "403 Forbidden",                             A),
    "TestProPlanGate::test_odai_list_pro_passes":            ("pro プランでお題一覧取得",                              "200 OK",                                    N),
    "TestProPlanGate::test_tags_list_free_returns_403":      ("free プランでタグ一覧取得",                             "403 Forbidden",                             A),
    "TestProPlanGate::test_tags_list_light_returns_403":     ("light プランでタグ一覧取得",                            "403 Forbidden",                             A),
    "TestProPlanGate::test_tags_list_pro_passes":            ("pro プランでタグ一覧取得",                              "200 OK",                                    N),
    "TestProPlanGate::test_schedules_list_free_returns_403": ("free プランでスケジュール一覧取得",                     "403 Forbidden",                             A),
    "TestProPlanGate::test_schedules_list_light_returns_403": ("light プランでスケジュール一覧取得",                   "403 Forbidden",                             A),
    "TestProPlanGate::test_schedules_list_pro_passes":       ("pro プランでスケジュール一覧取得",                      "200 OK",                                    N),
    "TestProPlanGate::test_settings_put_free_returns_403":   ("free プランで設定更新",                                 "403 Forbidden",                             A),
    "TestProPlanGate::test_settings_put_light_returns_403":  ("light プランで設定更新",                                "403 Forbidden",                             A),
    "TestProPlanGate::test_settings_put_pro_passes":         ("pro プランで設定更新",                                  "200 OK",                                    N),
    "TestProPlanGate::test_settings_get_light_passes":       ("light プランで設定取得（GET はゲートなし）",             "200 OK",                                    N),
    "TestProPlanGate::test_summary_free_passes_auth_but_plan_not_gated": ("free プランでサマリー取得（プランゲートなし）", "200 OK",                                N),

    # ── test_plan_schedule ─────────────────────────────────────
    "TestGetPlanSchedule::test_returns_schedule_when_exists": ("スケジュールが存在する場合に取得",                     "200 OK：スケジュール返却",                  N),
    "TestGetPlanSchedule::test_returns_null_when_no_schedule": ("スケジュールが未設定の場合に取得",                    "200 OK：data=null 返却",                    N),
    "TestGetPlanSchedule::test_unauthenticated_returns_401": ("未認証でプランスケジュール取得",                        "401 Unauthorized",                          A),
    "TestSetPlanSchedule::test_creates_schedule_when_none_exists": ("スケジュール未設定時に新規作成",                  "200 OK：新規スケジュール返却",              N),
    "TestSetPlanSchedule::test_updates_existing_schedule":   ("既存スケジュールを更新",                                "200 OK：更新後のスケジュール返却",          N),
    "TestSetPlanSchedule::test_non_pro_cannot_create_second_schedule": ("非 pro プランで 2 件目のスケジュール作成",    "403 Forbidden",                             A),
    "TestSetPlanSchedule::test_free_plan_can_create_first_schedule": ("free プランで 1 件目のスケジュール作成",        "200 OK",                                    N),
    "TestSetPlanSchedule::test_unauthenticated_returns_401": ("未認証でスケジュール設定",                              "401 Unauthorized",                          A),
    "TestDeletePlanSchedule::test_success":                  ("プランスケジュールを削除",                              "200 OK",                                    N),
    "TestDeletePlanSchedule::test_not_found_returns_404":    ("存在しないプランスケジュールを削除",                    "404 Not Found",                             A),
    "TestDeletePlanSchedule::test_wrong_guild_returns_404":  ("別ギルドのスケジュールを削除",                          "404 Not Found",                             A),
    "TestDeletePlanSchedule::test_unauthenticated_returns_401": ("未認証でスケジュール削除",                           "401 Unauthorized",                          A),

    # ── test_schedules ─────────────────────────────────────────
    "TestListSchedules::test_success":                       ("スケジュール一覧を取得",                                "200 OK：スケジュールリスト返却",            N),
    "TestListSchedules::test_unauthenticated_returns_401":   ("未認証でスケジュール一覧取得",                          "401 Unauthorized",                          A),
    "TestCreateSchedule::test_success":                      ("有効なデータでスケジュールを作成",                      "201 Created：作成済みスケジュール返却",     N),
    "TestCreateSchedule::test_invalid_time_format_returns_400": ("無効な時刻フォーマットでスケジュール作成",           "400 Bad Request",                           A),
    "TestCreateSchedule::test_invalid_tag_mode_returns_400": ("無効な tag_mode でスケジュール作成",                   "400 Bad Request",                           A),
    "TestCreateSchedule::test_allow_mode_without_tags_returns_400": ("allow モードでタグ未指定",                       "400 Bad Request",                           A),
    "TestCreateSchedule::test_allow_mode_with_tags_succeeds": ("allow モードでタグを指定",                             "201 Created",                               N),
    "TestUpdateSchedule::test_success":                      ("スケジュールを更新",                                    "200 OK：更新後のスケジュール返却",          N),
    "TestUpdateSchedule::test_not_found_returns_404":        ("存在しないスケジュールを更新",                          "404 Not Found",                             A),
    "TestDeleteSchedule::test_success":                      ("スケジュールを削除",                                    "200 OK",                                    N),
    "TestDeleteSchedule::test_not_found_returns_404":        ("存在しないスケジュールを削除",                          "404 Not Found",                             A),

    # ── test_settings ──────────────────────────────────────────
    "TestGetSettings::test_success":                         ("Guild 設定を取得",                                     "200 OK：設定データ返却",                    N),
    "TestGetSettings::test_returns_defaults_when_no_row":    ("設定レコードが未作成の場合",                            "200 OK：デフォルト値返却",                  N),
    "TestGetSettings::test_use_default_odai_false":          ("use_default_odai=false の設定取得",                    "200 OK：false が返却",                      N),
    "TestGetSettings::test_unauthenticated_returns_401":     ("未認証で設定取得",                                      "401 Unauthorized",                          A),
    "TestUpdateSettings::test_update_existing":              ("既存設定を更新",                                        "200 OK：更新後の設定返却",                  N),
    "TestUpdateSettings::test_insert_when_not_exists":       ("設定が未存在の場合に UPDATE",                          "200 OK（INSERT OR UPDATE）",                N),
    "TestUpdateSettings::test_update_use_default_odai":      ("use_default_odai フラグを更新",                        "200 OK",                                    N),
    "TestUpdateSettings::test_non_admin_returns_403":        ("一般ユーザーが設定更新",                                "403 Forbidden",                             A),

    # ── test_settings_extra ────────────────────────────────────
    "TestGetGuildName::test_success":                        ("登録済みギルドの名前を取得",                            "200 OK：guild_name 返却",                   N),
    "TestGetGuildName::test_not_registered_returns_null":    ("未登録ギルドの名前取得",                                "200 OK：guild_name=null 返却",              N),
    "TestGetGuildName::test_no_auth_required":               ("認証なしでギルド名取得（公開エンドポイント）",           "200 OK（認証不要）",                        N),
    "TestGetChannels::test_success":                         ("チャンネル一覧を取得",                                  "200 OK：チャンネルリスト返却",              N),
    "TestGetChannels::test_empty_returns_empty_list":        ("チャンネルが 0 件の場合",                              "200 OK：空リスト返却",                      N),
    "TestGetChannels::test_channel_id_is_string":            ("DB から整数型の channel_id が返る場合",                "レスポンスの channel_id が文字列型",        N),
    "TestGetChannels::test_unauthenticated_returns_401":     ("未認証でチャンネル一覧取得",                            "401 Unauthorized",                          A),

    # ── test_stripe ────────────────────────────────────────────
    "TestGetGuildPlanEndpoint::test_returns_plan_when_record_exists": ("プランレコードが存在する場合",                 "200 OK：プラン情報返却",                    N),
    "TestGetGuildPlanEndpoint::test_returns_free_defaults_when_no_record": ("プランレコードがない場合",               "200 OK：free プランのデフォルト返却",       N),
    "TestGetGuildPlanEndpoint::test_current_period_end_is_returned": ("current_period_end が設定されている場合",       "200 OK：current_period_end フィールド含む", N),
    "TestStripeWebhook::test_invalid_signature_returns_400": ("不正な Stripe 署名でウェブフック",                     "400 Bad Request",                           A),
    "TestStripeWebhook::test_checkout_completed_subscription_upserts_guild_plan": ("checkout.session.completed（新規サブスク）", "200 OK：guild_plans テーブルが upsert される", N),
    "TestStripeWebhook::test_checkout_completed_expand_increments_capacity": ("checkout.session.completed（容量拡張）", "200 OK：custom_odai_capacity が加算される", N),
    "TestStripeWebhook::test_subscription_updated_updates_status": ("customer.subscription.updated イベント",          "200 OK：status が更新される",               N),
    "TestStripeWebhook::test_subscription_deleted_sets_canceled": ("customer.subscription.deleted イベント",           "200 OK：status が canceled に設定",         N),
    "TestStripeWebhook::test_unknown_event_type_returns_200": ("未知のイベントタイプ",                                  "200 OK（無視して正常終了）",                N),
    "TestStripeWebhook::test_checkout_completed_missing_guild_id_is_noop": ("メタデータに guild_id がない場合",         "200 OK（ノーオペレーション）",              N),
    "TestCreateCheckout::test_no_bot_secret_returns_401":    ("Bot シークレットなしでチェックアウト作成",               "401 Unauthorized",                          A),
    "TestCreateCheckout::test_wrong_bot_secret_returns_401": ("誤った Bot シークレットでチェックアウト作成",            "401 Unauthorized",                          A),
    "TestCreateCheckout::test_plan_not_found_returns_400":   ("存在しないプランでチェックアウト作成",                   "400 Bad Request",                           A),
    "TestCreateCheckout::test_plan_without_price_id_returns_400": ("price_id 未設定のプランでチェックアウト",          "400 Bad Request",                           A),
    "TestCreateCheckout::test_success_returns_checkout_url": ("有効なプランでチェックアウト作成",                       "200 OK：Stripe チェックアウト URL 返却",    N),
    "TestCreateExpand::test_no_bot_secret_returns_401":      ("Bot シークレットなしで容量拡張",                         "401 Unauthorized",                          A),
    "TestCreateExpand::test_guild_not_found_returns_404":    ("存在しないギルドで容量拡張",                             "404 Not Found",                             A),
    "TestCreateExpand::test_cannot_expand_returns_403":      ("容量拡張が許可されていないプランで拡張",                 "403 Forbidden",                             A),
    "TestCreateExpand::test_exceeds_max_capacity_returns_400": ("最大容量を超える拡張",                                "400 Bad Request",                           A),
    "TestCreateExpand::test_success_returns_checkout_url":   ("有効な容量拡張リクエスト",                              "200 OK：Stripe チェックアウト URL 返却",    N),

    # ── test_summary ───────────────────────────────────────────
    "TestDashboardSummary::test_success_with_last_post":     ("最終投稿あり状態でサマリー取得",                        "200 OK：last_post フィールド含む",          N),
    "TestDashboardSummary::test_success_without_last_post":  ("最終投稿なし状態でサマリー取得",                        "200 OK：last_post=null",                    N),
    "TestDashboardSummary::test_unauthenticated_returns_401": ("未認証でサマリー取得",                                 "401 Unauthorized",                          A),

    # ── test_tags ──────────────────────────────────────────────
    "TestListTags::test_success":                            ("タグ一覧を取得",                                        "200 OK：タグリスト返却",                    N),
    "TestListTags::test_search_passes_query_param":          ("検索クエリ指定でタグ一覧取得",                          "200 OK：クエリが DB に渡される",            N),
    "TestListTags::test_unauthenticated_returns_401":        ("未認証でタグ一覧取得",                                  "401 Unauthorized",                          A),
    "TestCreateTag::test_success":                           ("新しいタグを作成",                                      "201 Created：作成済みタグ返却",             N),
    "TestCreateTag::test_duplicate_name_returns_409":        ("既存のタグ名で作成",                                    "409 Conflict",                              A),
    "TestUpdateTag::test_success":                           ("タグ情報を更新",                                        "200 OK：更新後のタグ返却",                  N),
    "TestUpdateTag::test_not_found_returns_404":             ("存在しないタグを更新",                                  "404 Not Found",                             A),
    "TestUpdateTag::test_name_conflict_returns_409":         ("別タグと同名に変更",                                    "409 Conflict",                              A),
    "TestUpdateTag::test_no_fields_returns_400":             ("更新フィールド未指定",                                  "400 Bad Request",                           A),
    "TestDeleteTag::test_success":                           ("タグを削除",                                           "200 OK",                                    N),
    "TestDeleteTag::test_not_found_returns_404":             ("存在しないタグを削除",                                  "404 Not Found",                             A),

    # ── test_tags_extra ────────────────────────────────────────
    "TestGetTagDetail::test_success":                        ("タグ詳細（お題・スケジュール埋め込み）を取得",           "200 OK：name / odai / schedules 返却",      N),
    "TestGetTagDetail::test_not_found_returns_404":          ("存在しないタグの詳細取得",                              "404 Not Found",                             A),
    "TestGetTagDetail::test_includes_odai_list":             ("タグ詳細にお題一覧が含まれること",                      "200 OK：odai フィールドにリスト",           N),
    "TestGetTagDetail::test_includes_schedules_with_enabled_as_bool": ("schedules の enabled が bool 型か確認",        "enabled=true（int→bool 変換）",             N),
    "TestGetTagDetail::test_unauthenticated_returns_401":    ("未認証でタグ詳細取得",                                  "401 Unauthorized",                          A),

    # ── test_test_post ─────────────────────────────────────────
    "TestTestPost::test_success":                            ("候補お題が存在する場合にテスト投稿",                     "200 OK：選択されたお題返却",                N),
    "TestTestPost::test_no_candidate_returns_404":           ("候補お題が 0 件の場合にテスト投稿",                     "404 Not Found",                             A),
    "TestTestPost::test_with_tag_mode_and_list":             ("tag_mode と tag_list を指定してテスト投稿",              "200 OK：指定タグ条件で候補選択",            N),
    "TestTestPost::test_default_tag_mode_is_all":            ("tag_mode 未指定でテスト投稿",                           "200 OK：デフォルト tag_mode='all' が適用", N),
    "TestTestPost::test_unauthenticated_returns_401":        ("未認証でテスト投稿",                                    "401 Unauthorized",                          A),

    # ── test_rate_limit ────────────────────────────────────────
    "TestLoginRateLimit::test_rate_limit_returns_429":          ("ログインを 10 回連続で試行（上限到達後）",            "429 Too Many Requests：リトライ時間付きメッセージ", A),
    "TestResetPasswordRateLimit::test_rate_limit_returns_429":  ("パスワードリセットを 5 回連続で試行（上限到達後）",  "429 Too Many Requests：リトライ時間付きメッセージ", A),

    # ── test_odai（追加分） ────────────────────────────────────
    "TestDeleteOdai::test_non_admin_returns_403":            ("一般ユーザーがお題を削除",                              "403 Forbidden",                             A),

    # ── test_odai_extra（追加分） ──────────────────────────────
    "TestImportOdai::test_no_files_returns_422":             ("ファイルを 1 件も送らずにインポートリクエスト",          "422 Unprocessable Entity（必須フィールド欠落）", A),
}

# ─────────────────────────────────────────────────────────────
# JUnit XML を解析
# ─────────────────────────────────────────────────────────────
xml_path = Path(__file__).parent / "junit_report.xml"
tree = ET.parse(xml_path)
root = tree.getroot()

suite_elem = root.find("testsuite")
suite = suite_elem if suite_elem is not None else root

total    = int(suite.get("tests",    0))
failures = int(suite.get("failures", 0))
errors   = int(suite.get("errors",   0))
timestamp = suite.get("timestamp", "")
elapsed   = float(suite.get("time", 0))

file_tests = OrderedDict()
for tc in suite.findall("testcase"):
    classname = tc.get("classname", "")
    parts = classname.rsplit(".", 1)
    module = parts[0].split(".")[-1] if len(parts) == 2 else classname
    cls    = parts[1]                if len(parts) == 2 else ""
    name   = tc.get("name", "")
    failed = tc.find("failure") is not None or tc.find("error") is not None
    key    = f"{cls}::{name}"
    desc   = DESCRIPTIONS.get(key, ("", "", ""))
    file_tests.setdefault(module, []).append({
        "cls": cls, "name": name, "failed": failed,
        "scenario": desc[0], "expected": desc[1], "kind": desc[2],
    })

# ─────────────────────────────────────────────────────────────
# 集計
# ─────────────────────────────────────────────────────────────
passed    = total - failures - errors
now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

total_normal = sum(1 for ts in file_tests.values() for t in ts if t["kind"] == N)
total_abnormal = sum(1 for ts in file_tests.values() for t in ts if t["kind"] == A)

# ─────────────────────────────────────────────────────────────
# HTML ビルダー
# ─────────────────────────────────────────────────────────────
def make_toc(file_tests):
    items = ""
    for fkey in file_tests:
        label = FILE_LABELS.get(fkey, (fkey, ""))[0]
        items += f'<li><a href="#{fkey}">{fkey} <small>— {label}</small></a></li>\n'
    return f"<ul>{items}</ul>"


def make_file_summary(file_tests):
    rows = ""
    for fkey, tests in file_tests.items():
        label, ep = FILE_LABELS.get(fkey, (fkey, ""))
        cnt  = len(tests)
        ok   = sum(1 for t in tests if not t["failed"])
        ng   = cnt - ok
        norm = sum(1 for t in tests if t["kind"] == N)
        abno = sum(1 for t in tests if t["kind"] == A)
        ng_cell = f'<span style="color:#e74c3c;font-weight:bold">{ng}</span>' if ng else "0"
        rows += (
            f"<tr>"
            f"<td><a href='#{fkey}'><code>{fkey}</code></a></td>"
            f"<td>{label}</td>"
            f"<td style='font-size:0.82em'>{ep}</td>"
            f"<td style='text-align:center'>{cnt}</td>"
            f"<td style='text-align:center;color:#27ae60;font-weight:bold'>{ok}</td>"
            f"<td style='text-align:center'>{ng_cell}</td>"
            f"<td style='text-align:center'><span class='badge-normal'>{norm}</span></td>"
            f"<td style='text-align:center'><span class='badge-abnormal'>{abno}</span></td>"
            f"</tr>\n"
        )
    return rows


def kind_badge(kind):
    if kind == N:
        return '<span class="badge-normal">正常系</span>'
    if kind == A:
        return '<span class="badge-abnormal">異常系</span>'
    return ""


def make_detail_sections(file_tests):
    html = ""
    for fkey, tests in file_tests.items():
        label, ep = FILE_LABELS.get(fkey, (fkey, ""))
        cnt  = len(tests)
        ok   = sum(1 for t in tests if not t["failed"])
        norm = sum(1 for t in tests if t["kind"] == N)
        abno = sum(1 for t in tests if t["kind"] == A)
        html += f"""
<section id="{fkey}">
  <h2>{fkey} <small style="font-weight:normal;color:#555">— {label}</small></h2>
  <p style="color:#555;font-size:0.9em">{ep}</p>
  <p>
    <strong>テスト数：</strong>{cnt} &nbsp;|&nbsp;
    <strong style="color:#27ae60">成功：{ok}</strong> &nbsp;|&nbsp;
    <strong style="color:#e74c3c">失敗：{cnt-ok}</strong> &nbsp;|&nbsp;
    <span class="badge-normal">正常系：{norm}</span> &nbsp;
    <span class="badge-abnormal">異常系：{abno}</span>
  </p>
  <table>
    <thead>
      <tr>
        <th>テストクラス</th>
        <th>テスト名</th>
        <th>種別</th>
        <th>想定ケース</th>
        <th>想定結果</th>
        <th>結果</th>
      </tr>
    </thead>
    <tbody>
"""
        for t in tests:
            result_badge = '<span class="badge-fail">FAIL</span>' if t["failed"] else '<span class="badge-pass">PASS</span>'
            html += (
                f"      <tr>"
                f"<td><code>{t['cls']}</code></td>"
                f"<td><code>{t['name']}</code></td>"
                f"<td style='text-align:center'>{kind_badge(t['kind'])}</td>"
                f"<td>{t['scenario']}</td>"
                f"<td>{t['expected']}</td>"
                f"<td style='text-align:center'>{result_badge}</td>"
                f"</tr>\n"
            )
        html += "    </tbody>\n  </table>\n</section>\n"
    return html


# ─────────────────────────────────────────────────────────────
# HTML 出力
# ─────────────────────────────────────────────────────────────
html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OdaiBotAPI UT エビデンス レポート</title>
<style>
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; margin: 0; padding: 0; background: #f5f7fa; color: #333; }}
  header {{ background: #2c3e50; color: white; padding: 24px 40px; }}
  header h1 {{ margin: 0 0 6px; font-size: 1.6em; }}
  header p {{ margin: 0; opacity: 0.8; font-size: 0.9em; }}
  .container {{ max-width: 1300px; margin: 0 auto; padding: 24px 40px; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-bottom: 28px; }}
  .card {{ background: white; border-radius: 8px; padding: 18px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  .card .val {{ font-size: 2.2em; font-weight: bold; }}
  .card.pass   .val {{ color: #27ae60; }}
  .card.fail   .val {{ color: #e74c3c; }}
  .card.total  .val {{ color: #2c3e50; }}
  .card.time   .val {{ color: #8e44ad; }}
  .card.normal .val {{ color: #2980b9; }}
  .card.abnorm .val {{ color: #e67e22; }}
  .card label {{ display: block; color: #777; font-size: 0.82em; margin-top: 4px; }}
  section {{ background: white; border-radius: 8px; padding: 24px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
  h2 {{ color: #2c3e50; margin-top: 0; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; font-size: 1.15em; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.875em; }}
  th {{ background: #2c3e50; color: white; padding: 10px 12px; text-align: left; white-space: nowrap; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid #ecf0f1; vertical-align: top; }}
  tr:hover td {{ background: #f0f4f8; }}
  code {{ background: #eef; padding: 1px 5px; border-radius: 3px; font-size: 0.88em; }}
  .badge-pass    {{ background:#27ae60; color:white; padding:2px 10px; border-radius:12px; font-size:0.82em; font-weight:bold; }}
  .badge-fail    {{ background:#e74c3c; color:white; padding:2px 10px; border-radius:12px; font-size:0.82em; font-weight:bold; }}
  .badge-normal  {{ background:#2980b9; color:white; padding:2px 10px; border-radius:12px; font-size:0.82em; font-weight:bold; display:inline-block; }}
  .badge-abnormal{{ background:#e67e22; color:white; padding:2px 10px; border-radius:12px; font-size:0.82em; font-weight:bold; display:inline-block; }}
  nav ul {{ list-style: none; padding: 0; column-count: 2; column-gap: 16px; }}
  nav li {{ margin: 4px 0; }}
  nav a {{ color: #2980b9; text-decoration: none; }}
  nav a:hover {{ text-decoration: underline; }}
  small {{ font-size: 0.82em; }}
</style>
</head>
<body>
<header>
  <h1>OdaiBotAPI ユニットテスト エビデンス レポート</h1>
  <p>生成日時: {now_str} &nbsp;|&nbsp; テスト実行タイムスタンプ: {timestamp}</p>
</header>
<div class="container">

<div class="summary-grid">
  <div class="card total"><div class="val">{total}</div><label>総テスト数</label></div>
  <div class="card pass"><div class="val">{passed}</div><label>成功</label></div>
  <div class="card fail"><div class="val">{failures + errors}</div><label>失敗</label></div>
  <div class="card time"><div class="val">{elapsed:.1f}s</div><label>実行時間</label></div>
  <div class="card normal"><div class="val">{total_normal}</div><label>正常系</label></div>
  <div class="card abnorm"><div class="val">{total_abnormal}</div><label>異常系</label></div>
</div>

<section>
  <h2>目次</h2>
  <nav>{make_toc(file_tests)}</nav>
</section>

<section>
  <h2>ファイル別サマリー</h2>
  <table>
    <thead>
      <tr>
        <th>ファイル名</th>
        <th>対象機能</th>
        <th>対象エンドポイント</th>
        <th>件数</th>
        <th>成功</th>
        <th>失敗</th>
        <th>正常系</th>
        <th>異常系</th>
      </tr>
    </thead>
    <tbody>
{make_file_summary(file_tests)}    </tbody>
  </table>
</section>

<h2 style="margin-top:32px">テストケース詳細</h2>
{make_detail_sections(file_tests)}

</div>
</body>
</html>
"""

out_path = Path(__file__).parent / "test_report.html"
out_path.write_text(html_content, encoding="utf-8")
print(f"Report generated: {out_path}")
print(f"  total={total}  passed={passed}  failed={failures+errors}")
print(f"  normal={total_normal}  abnormal={total_abnormal}")
