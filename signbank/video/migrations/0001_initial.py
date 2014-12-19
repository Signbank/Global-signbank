# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Video'
        db.create_table('video_video', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('geometry', self.gf('django.db.models.fields.CharField')(default='320x240', max_length='20')),
            ('original', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('h264', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('ogg', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('video', ['Video'])

        # Adding model 'VideoSet'
        db.create_table('video_videoset', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('geometry', self.gf('django.db.models.fields.CharField')(default='320x240', max_length='20')),
        ))
        db.send_create_signal('video', ['VideoSet'])

        # Adding model 'VideoFile'
        db.create_table('video_videofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('mimetype', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('videoset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['video.VideoSet'])),
        ))
        db.send_create_signal('video', ['VideoFile'])


    def backwards(self, orm):
        
        # Deleting model 'Video'
        db.delete_table('video_video')

        # Deleting model 'VideoSet'
        db.delete_table('video_videoset')

        # Deleting model 'VideoFile'
        db.delete_table('video_videofile')


    models = {
        'video.video': {
            'Meta': {'object_name': 'Video'},
            'geometry': ('django.db.models.fields.CharField', [], {'default': "'320x240'", 'max_length': "'20'"}),
            'h264': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ogg': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'original': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'video.videofile': {
            'Meta': {'object_name': 'VideoFile'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'videoset': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['video.VideoSet']"})
        },
        'video.videoset': {
            'Meta': {'object_name': 'VideoSet'},
            'geometry': ('django.db.models.fields.CharField', [], {'default': "'320x240'", 'max_length': "'20'"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['video']
