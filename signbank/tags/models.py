from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


class TagManager(models.Manager):
    """Custom manager for Tag model"""
    
    def add_tag(self, obj, tag_name):
        """Add a tag to an object. Creates tag if it doesn't exist."""
        if not tag_name or not tag_name.strip():
            return None
        
        # Remove quotes if present (from old tagging system)
        tag_name = tag_name.strip().strip('"\'')
        
        tag, _ = self.get_or_create(name=tag_name)
        content_type = ContentType.objects.get_for_model(obj)
        TaggedItem.objects.get_or_create(
            tag=tag,
            content_type=content_type,
            object_id=obj.id
        )
        return tag
    
    def get_for_object(self, obj):
        """Get all tags for an object"""
        content_type = ContentType.objects.get_for_model(obj)
        tagged_items = TaggedItem.objects.filter(
            content_type=content_type,
            object_id=obj.id
        ).select_related('tag')
        return [ti.tag for ti in tagged_items]


class Tag(models.Model):
    """Custom Tag model to replace django-tagging"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    
    objects = TagManager()
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'
    
    def __str__(self):
        return self.name


class TaggedItem(models.Model):
    """Custom TaggedItem model linking tags to objects"""
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='items')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    
    # Generic foreign key
    content_object = GenericForeignKey('content_type', 'object_id')
    
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('tag', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['tag']),
        ]
        verbose_name = 'Tagged Item'
        verbose_name_plural = 'Tagged Items'
    
    def __str__(self):
        return f'{self.content_object} tagged with "{self.tag}"'
