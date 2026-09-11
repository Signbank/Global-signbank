# Data migration to migrate from django-tagging to custom tags

import logging
from django.db import migrations
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)


def migrate_from_tagging(apps, schema_editor):
    """Migrate existing tags from django-tagging to custom tags app"""
    Tag = apps.get_model('tags', 'Tag')
    TaggedItem = apps.get_model('tags', 'TaggedItem')
    
    # Try to import django-tagging models if package is still installed
    try:
        from tagging.models import Tag as OldTag, TaggedItem as OldTaggedItem
    except (ImportError, ModuleNotFoundError, RuntimeError) as e:
        logger.info(f"django-tagging not installed or not available: {e}. Skipping migration.")
        return
    
    # Get the Gloss content type
    try:
        from signbank.dictionary.models import Gloss
        gloss_ct = ContentType.objects.get_for_model(Gloss)
    except Exception as e:
        logger.error(f"Could not import Gloss model or get content type: {e}. Aborting migration.")
        raise
    
    try:
        # Migrate all old tags
        old_tags = OldTag.objects.all()
        migrated_count = 0
        tagged_items_count = 0
        
        logger.info(f"Starting migration of {old_tags.count()} old tags")
        
        for old_tag in old_tags:
            # Create or get the new tag with the same name
            new_tag, _ = Tag.objects.get_or_create(name=old_tag.name)
            migrated_count += 1
            
            # Get all tagged items for this old tag
            old_items = OldTaggedItem.objects.filter(tag=old_tag)
            
            for old_item in old_items:
                # Only migrate Gloss tags (object_id and content_type_id match Gloss)
                if old_item.content_type.app_label == 'dictionary' and old_item.content_type.model == 'gloss':
                    # Create the new TaggedItem
                    TaggedItem.objects.get_or_create(
                        tag=new_tag,
                        content_type=gloss_ct,
                        object_id=old_item.object_id,
                        defaults={'created': old_item.created}
                    )
                    tagged_items_count += 1
        
        logger.info(f"Migration completed: {migrated_count} tags migrated with {tagged_items_count} tagged items")
    except Exception as e:
        logger.error(f"Error during tag migration: {e}", exc_info=True)
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
