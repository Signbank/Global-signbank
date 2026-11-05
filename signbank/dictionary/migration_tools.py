def sql_for_app_removal(app_label: str, tables_names: list[str]) -> None:
    """Creates raw SQL statements for the removal of external apps"""
    drop_tables = "\n".join(
        [f"DROP TABLE IF EXISTS {table_name};" for table_name in tables_names]
    )
    delete_froms = f"""
        DELETE FROM auth_group_permissions WHERE permission_id IN (
            SELECT id FROM auth_permission WHERE content_type_id IN (
                SELECT id FROM django_content_type WHERE app_label = '{app_label}'
            )
        );
        DELETE FROM auth_permission WHERE content_type_id IN (
            SELECT id FROM django_content_type WHERE app_label = '{app_label}'
        );
        DELETE FROM django_admin_log WHERE content_type_id IN (
            SELECT id FROM django_content_type WHERE app_label = '{app_label}'
        );
        DELETE FROM django_content_type WHERE app_label = '{app_label}';
        DELETE FROM django_migrations WHERE app = '{app_label}';
    """
    return f"{drop_tables}\n{delete_froms}"