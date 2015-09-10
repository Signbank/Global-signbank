# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Translation'
        db.create_table(u'dictionary_translation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('gloss', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dictionary.Gloss'])),
            ('translation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dictionary.Keyword'])),
            ('index', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'dictionary', ['Translation'])

        # Adding model 'Keyword'
        db.create_table(u'dictionary_keyword', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
        ))
        db.send_create_signal(u'dictionary', ['Keyword'])

        # Adding model 'Definition'
        db.create_table(u'dictionary_definition', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('gloss', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dictionary.Gloss'])),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('count', self.gf('django.db.models.fields.IntegerField')()),
            ('published', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'dictionary', ['Definition'])

        # Adding model 'Language'
        db.create_table(u'dictionary_language', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'dictionary', ['Language'])

        # Adding model 'Dialect'
        db.create_table(u'dictionary_dialect', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('language', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dictionary.Language'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('description', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'dictionary', ['Dialect'])

        # Adding model 'RelationToForeignSign'
        db.create_table(u'dictionary_relationtoforeignsign', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('gloss', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['dictionary.Gloss'])),
            ('loan', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('other_lang', self.gf('django.db.models.fields.CharField')(max_length=20)),
            ('other_lang_gloss', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'dictionary', ['RelationToForeignSign'])

        # Adding model 'FieldChoice'
        db.create_table(u'dictionary_fieldchoice', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('field', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('english_name', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('machine_value', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'dictionary', ['FieldChoice'])

        # Adding model 'Gloss'
        db.create_table(u'dictionary_gloss', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('idgloss', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('annotation_idgloss', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('annotation_idgloss_en', self.gf('django.db.models.fields.CharField')(max_length=30, blank=True)),
            ('bsltf', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('asltf', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('aslgloss', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('asloantf', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('bslgloss', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('bslloantf', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('useInstr', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('rmrks', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('blend', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('blendtf', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('compound', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('comptf', self.gf('django.db.models.fields.NullBooleanField')(null=True, blank=True)),
            ('handedness', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('domhndsh', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('subhndsh', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('final_domhndsh', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('final_subhndsh', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('locprim', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('final_loc', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('locVirtObj', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('locsecond', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('initial_secondary_loc', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('final_secondary_loc', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('initial_palm_orientation', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('final_palm_orientation', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('initial_relative_orientation', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('final_relative_orientation', self.gf('django.db.models.fields.CharField')(max_length=20, null=True, blank=True)),
            ('inWeb', self.gf('django.db.models.fields.NullBooleanField')(default=False, null=True, blank=True)),
            ('isNew', self.gf('django.db.models.fields.NullBooleanField')(default=False, null=True, blank=True)),
            ('inittext', self.gf('django.db.models.fields.CharField')(max_length='50', blank=True)),
            ('morph', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('sedefinetf', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('segloss', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('sense', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('sn', self.gf('django.db.models.fields.IntegerField')(unique=True, null=True, blank=True)),
            ('StemSN', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('relatArtic', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('absOriPalm', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('absOriFing', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('relOriMov', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('relOriLoc', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('oriCh', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('handCh', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('repeat', self.gf('django.db.models.fields.NullBooleanField')(default=False, null=True, blank=True)),
            ('altern', self.gf('django.db.models.fields.NullBooleanField')(default=False, null=True, blank=True)),
            ('movSh', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('movDir', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('movMan', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('contType', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('phonOth', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('mouthG', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('mouthing', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('phonetVar', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('iconImg', self.gf('django.db.models.fields.CharField')(max_length=50, blank=True)),
            ('namEnt', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('semField', self.gf('django.db.models.fields.CharField')(max_length=5, null=True, blank=True)),
            ('tokNo', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoSgnr', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoA', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoV', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoR', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoGe', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoGr', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoO', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoSgnrA', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoSgnrV', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoSgnrR', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoSgnrGe', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoSgnrGr', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('tokNoSgnrO', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('creationDate', self.gf('django.db.models.fields.DateField')(default=datetime.datetime(2015, 1, 1, 0, 0))),
            ('creator', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True)),
        ))
        db.send_create_signal(u'dictionary', ['Gloss'])

        # Adding M2M table for field language on 'Gloss'
        m2m_table_name = db.shorten_name(u'dictionary_gloss_language')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('gloss', models.ForeignKey(orm[u'dictionary.gloss'], null=False)),
            ('language', models.ForeignKey(orm[u'dictionary.language'], null=False))
        ))
        db.create_unique(m2m_table_name, ['gloss_id', 'language_id'])

        # Adding M2M table for field dialect on 'Gloss'
        m2m_table_name = db.shorten_name(u'dictionary_gloss_dialect')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('gloss', models.ForeignKey(orm[u'dictionary.gloss'], null=False)),
            ('dialect', models.ForeignKey(orm[u'dictionary.dialect'], null=False))
        ))
        db.create_unique(m2m_table_name, ['gloss_id', 'dialect_id'])

        # Adding model 'Relation'
        db.create_table(u'dictionary_relation', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relation_sources', to=orm['dictionary.Gloss'])),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(related_name='relation_targets', to=orm['dictionary.Gloss'])),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=20)),
        ))
        db.send_create_signal(u'dictionary', ['Relation'])

        # Adding model 'MorphologyDefinition'
        db.create_table(u'dictionary_morphologydefinition', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('parent_gloss', self.gf('django.db.models.fields.related.ForeignKey')(related_name='parent_glosses', to=orm['dictionary.Gloss'])),
            ('role', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('morpheme', self.gf('django.db.models.fields.related.ForeignKey')(related_name='morphemes', to=orm['dictionary.Gloss'])),
        ))
        db.send_create_signal(u'dictionary', ['MorphologyDefinition'])

        # Adding model 'UserProfile'
        db.create_table(u'dictionary_userprofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(related_name='user_profile_user', unique=True, to=orm['auth.User'])),
            ('last_used_language', self.gf('django.db.models.fields.CharField')(default='en', max_length=2)),
        ))
        db.send_create_signal(u'dictionary', ['UserProfile'])


    def backwards(self, orm):
        # Deleting model 'Translation'
        db.delete_table(u'dictionary_translation')

        # Deleting model 'Keyword'
        db.delete_table(u'dictionary_keyword')

        # Deleting model 'Definition'
        db.delete_table(u'dictionary_definition')

        # Deleting model 'Language'
        db.delete_table(u'dictionary_language')

        # Deleting model 'Dialect'
        db.delete_table(u'dictionary_dialect')

        # Deleting model 'RelationToForeignSign'
        db.delete_table(u'dictionary_relationtoforeignsign')

        # Deleting model 'FieldChoice'
        db.delete_table(u'dictionary_fieldchoice')

        # Deleting model 'Gloss'
        db.delete_table(u'dictionary_gloss')

        # Removing M2M table for field language on 'Gloss'
        db.delete_table(db.shorten_name(u'dictionary_gloss_language'))

        # Removing M2M table for field dialect on 'Gloss'
        db.delete_table(db.shorten_name(u'dictionary_gloss_dialect'))

        # Deleting model 'Relation'
        db.delete_table(u'dictionary_relation')

        # Deleting model 'MorphologyDefinition'
        db.delete_table(u'dictionary_morphologydefinition')

        # Deleting model 'UserProfile'
        db.delete_table(u'dictionary_userprofile')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'dictionary.definition': {
            'Meta': {'ordering': "['gloss', 'role', 'count']", 'object_name': 'Definition'},
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Gloss']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'published': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        u'dictionary.dialect': {
            'Meta': {'ordering': "['language', 'name']", 'object_name': 'Dialect'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Language']"}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'dictionary.fieldchoice': {
            'Meta': {'ordering': "['field', 'machine_value']", 'object_name': 'FieldChoice'},
            'english_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'field': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'machine_value': ('django.db.models.fields.IntegerField', [], {})
        },
        u'dictionary.gloss': {
            'Meta': {'ordering': "['idgloss']", 'object_name': 'Gloss'},
            'StemSN': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'absOriFing': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'absOriPalm': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'altern': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'annotation_idgloss': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'annotation_idgloss_en': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'aslgloss': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'asloantf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'asltf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'blend': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'blendtf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'bslgloss': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'bslloantf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'bsltf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'compound': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'comptf': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'contType': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'creationDate': ('django.db.models.fields.DateField', [], {'default': 'datetime.datetime(2015, 1, 1, 0, 0)'}),
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'dialect': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['dictionary.Dialect']", 'symmetrical': 'False'}),
            'domhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'final_domhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'final_loc': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'final_palm_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'final_relative_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'final_secondary_loc': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'final_subhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'handCh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'handedness': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'iconImg': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'idgloss': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'inWeb': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'initial_palm_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'initial_relative_orientation': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'initial_secondary_loc': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'inittext': ('django.db.models.fields.CharField', [], {'max_length': "'50'", 'blank': 'True'}),
            'isNew': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'language': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['dictionary.Language']", 'symmetrical': 'False'}),
            'locVirtObj': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'locprim': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'locsecond': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'morph': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'mouthG': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'mouthing': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'movDir': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'movMan': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'movSh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'namEnt': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'oriCh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'phonOth': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'phonetVar': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'relOriLoc': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'relOriMov': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'relatArtic': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'repeat': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'rmrks': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'sedefinetf': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'segloss': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'semField': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'sense': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sn': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'subhndsh': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'tokNo': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoA': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoGe': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoGr': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoO': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoR': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoSgnr': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoSgnrA': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoSgnrGe': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoSgnrGr': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoSgnrO': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoSgnrR': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoSgnrV': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'tokNoV': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'useInstr': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'})
        },
        u'dictionary.keyword': {
            'Meta': {'ordering': "['text']", 'object_name': 'Keyword'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'dictionary.language': {
            'Meta': {'ordering': "['name']", 'object_name': 'Language'},
            'description': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'dictionary.morphologydefinition': {
            'Meta': {'object_name': 'MorphologyDefinition'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'morpheme': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'morphemes'", 'to': u"orm['dictionary.Gloss']"}),
            'parent_gloss': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'parent_glosses'", 'to': u"orm['dictionary.Gloss']"}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '5'})
        },
        u'dictionary.relation': {
            'Meta': {'ordering': "['source']", 'object_name': 'Relation'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relation_sources'", 'to': u"orm['dictionary.Gloss']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'relation_targets'", 'to': u"orm['dictionary.Gloss']"})
        },
        u'dictionary.relationtoforeignsign': {
            'Meta': {'ordering': "['gloss', 'loan', 'other_lang', 'other_lang_gloss']", 'object_name': 'RelationToForeignSign'},
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Gloss']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'loan': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'other_lang': ('django.db.models.fields.CharField', [], {'max_length': '20'}),
            'other_lang_gloss': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'dictionary.translation': {
            'Meta': {'ordering': "['gloss', 'index']", 'object_name': 'Translation'},
            'gloss': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Gloss']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'translation': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dictionary.Keyword']"})
        },
        u'dictionary.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_used_language': ('django.db.models.fields.CharField', [], {'default': "'en'", 'max_length': '2'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'user_profile_user'", 'unique': 'True', 'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['dictionary']