# Data migration to migrate from django-tagging to custom tags

from django.db import migrations
from django.contrib.contenttypes.models import ContentType


def migrate_from_tagging(apps, schema_editor):
    """Migrate existing tags from django-tagging to custom tags app"""
    Tag = apps.get_model('tags', 'Tag')
    TaggedItem = apps.get_model('tags', 'TaggedItem')
    
    # Try to import django-tagging models
    try:
        from tagging.models import Tag as OldTag, TaggedItem as OldTaggedItem
    except ImportError:
        # django-tagging not installed, skip migration
        return
    
    # Get the Gloss content type from the old system
    try:
        from signbank.dictionary.models import Gloss
        gloss_ct = ContentType.objects.get_for_model(Gloss)
    except:
        return
    
    # Migrate all old tags
    old_tags = OldTag.objects.all()
    for old_tag in old_tags:
        # Create or get the new tag with the same name
        new_tag, _ = Tag.objects.get_or_create(name=old_tag.name)
        
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
