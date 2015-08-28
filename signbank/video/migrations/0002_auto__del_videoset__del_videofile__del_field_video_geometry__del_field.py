# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'VideoSet'
        db.delete_table('video_videoset')

        # Deleting model 'VideoFile'
        db.delete_table('video_videofile')

        # Deleting field 'Video.geometry'
        db.delete_column('video_video', 'geometry')

        # Deleting field 'Video.original'
        db.delete_column('video_video', 'original')

        # Deleting field 'Video.h264'
        db.delete_column('video_video', 'h264')

        # Deleting field 'Video.ogg'
        db.delete_column('video_video', 'ogg')

        # Adding field 'Video.videofile'
        db.add_column('video_video', 'videofile',
                      self.gf('django.db.models.fields.files.FileField')(default='', max_length=100),
                      keep_default=False)


    def backwards(self, orm):
        # Adding model 'VideoSet'
        db.create_table('video_videoset', (
            ('geometry', self.gf('django.db.models.fields.CharField')(default='320x240', max_length='20')),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('video', ['VideoSet'])

        # Adding model 'VideoFile'
        db.create_table('video_videofile', (
            ('mimetype', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('videoset', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['video.VideoSet'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
        ))
        db.send_create_signal('video', ['VideoFile'])

        # Adding field 'Video.geometry'
        db.add_column('video_video', 'geometry',
                      self.gf('django.db.models.fields.CharField')(default='320x240', max_length='20'),
                      keep_default=False)

        # Adding field 'Video.original'
        db.add_column('video_video', 'original',
                      self.gf('django.db.models.fields.files.FileField')(default='', max_length=100),
                      keep_default=False)

        # Adding field 'Video.h264'
        db.add_column('video_video', 'h264',
                      self.gf('django.db.models.fields.files.FileField')(default='', max_length=100),
                      keep_default=False)

        # Adding field 'Video.ogg'
        db.add_column('video_video', 'ogg',
                      self.gf('django.db.models.fields.files.FileField')(default='', max_length=100),
                      keep_default=False)

        # Deleting field 'Video.videofile'
        db.delete_column('video_video', 'videofile')


    models = {
        'video.video': {
            'Meta': {'object_name': 'Video'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'videofile': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['video']