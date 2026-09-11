# Data migration to migrate from django-tagging to custom tags

from django.db import migrations
from django.contrib.contenttypes.models import ContentType


def migrate_from_tagging(apps, schema_editor):
    """Migrate existing tags from django-tagging to custom tags app"""
    Tag = apps.get_model('tags', 'Tag')
    TaggedItem = apps.get_model('tags', 'TaggedItem')
    
    # Define temporary models that map to the old tagging tables
    # This works even if django-tagging is not in INSTALLED_APPS
    from django.db import models, connection
    
    class OldTag(models.Model):
        name = models.CharField(max_length=50, unique=True)
        
        class Meta:
            app_label = 'tagging'
            db_table = 'tagging_tag'
    
    class OldTaggedItem(models.Model):
        tag = models.ForeignKey(OldTag, on_delete=models.CASCADE)
        content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
        object_id = models.PositiveIntegerField()
        created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
        
        class Meta:
            app_label = 'tagging'
            db_table = 'tagging_taggeditem'
    
    # Get the Gloss content type
    try:
        from signbank.dictionary.models import Gloss
        gloss_ct = ContentType.objects.get_for_model(Gloss)
    except Exception as e:
        print(f"[tags migration] ERROR: Could not import Gloss model or get content type: {e}. Aborting migration.")
        raise
    
    try:
        # Try to query old tags - if table doesn't exist, migration is skipped
        old_tags = OldTag.objects.all()
        old_tags_count = old_tags.count()
        print(f"[tags migration] Found {old_tags_count} old tags to migrate")
        
        if old_tags_count == 0:
            print("[tags migration] No old tags found. Migration complete.")
            return
        
        migrated_count = 0
        tagged_items_count = 0
        
        for old_tag in old_tags:
            # Create or get the new tag with the same name
            new_tag, created = Tag.objects.get_or_create(name=old_tag.name)
            if created:
                migrated_count += 1
            
            # Get all tagged items for this old tag
            old_items = OldTaggedItem.objects.filter(tag=old_tag)
            
            for old_item in old_items:
                # Only migrate Gloss tags
                try:
                    ct = old_item.content_type
                    if ct.app_label == 'dictionary' and ct.model == 'gloss':
                        # Create the new TaggedItem
                        TaggedItem.objects.get_or_create(
                            tag=new_tag,
                            content_type=gloss_ct,
                            object_id=old_item.object_id,
                            defaults={'created': old_item.created}
                        )
                        tagged_items_count += 1
                except Exception as item_error:
                    print(f"[tags migration] Warning: Could not migrate tag '{old_tag.name}' for object {old_item.object_id}: {item_error}")
        
        print(f"[tags migration] COMPLETED: {migrated_count} new tags created with {tagged_items_count} tagged items")
    except Exception as e:
        print(f"[tags migration] ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise


def reverse_migrate(apps, schema_editor):
    """Reverse migration - just clear custom tags (optional)"""
    # You may want to keep the tags or delete them
    # This just clears them to reverse the migration
    Tag = apps.get_model('tags', 'Tag')
    TaggedItem = apps.get_model('tags', 'TaggedItem')
    TaggedItem.objects.all().delete()
    Tag.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tags', '0001_initial'),
        ('dictionary', '0097_alter_gloss_absorifing_alter_gloss_absoripalm_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_from_tagging, reverse_migrate),
    ]
