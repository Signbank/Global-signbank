class AuditRouter:
    """
    A router to control all database operations on models in easyaudit
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == "easyaudit":
            return "audit"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == "easyaudit":
            return "audit"
        return None

    def allow_migrate(self, db, app_label, **hints):
        if app_label == "easyaudit":
            return db == "audit"
        return None
