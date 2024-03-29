# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-11-25 12:50
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0053_auto_20221031_1424'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='definition',
            name='role',
        ),
        migrations.RenameField(
            model_name='definition',
            old_name='role_fk',
            new_name='role',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='handedness',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='handedness_fk',
            new_name='handedness',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='domhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='domhndsh_fk',
            new_name='domhndsh',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='subhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='subhndsh_fk',
            new_name='subhndsh',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='final_domhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='final_domhndsh_fk',
            new_name='final_domhndsh',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='final_subhndsh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='final_subhndsh_fk',
            new_name='final_subhndsh',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='locprim',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='locprim_fk',
            new_name='locprim',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='final_loc',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='final_loc_fk',
            new_name='final_loc',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='locsecond',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='locsecond_fk',
            new_name='locsecond',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='initial_secondary_loc',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='initial_secondary_loc_fk',
            new_name='initial_secondary_loc',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='final_secondary_loc',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='final_secondary_loc_fk',
            new_name='final_secondary_loc',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='domSF',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='domSF_fk',
            new_name='domSF',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='domFlex',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='domFlex_fk',
            new_name='domFlex',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='relatArtic',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='relatArtic_fk',
            new_name='relatArtic',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='absOriPalm',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='absOriPalm_fk',
            new_name='absOriPalm',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='absOriFing',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='absOriFing_fk',
            new_name='absOriFing',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='relOriMov',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='relOriMov_fk',
            new_name='relOriMov',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='relOriLoc',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='relOriLoc_fk',
            new_name='relOriLoc',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='oriCh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='oriCh_fk',
            new_name='oriCh',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='handCh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='handCh_fk',
            new_name='handCh',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='movSh',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='movSh_fk',
            new_name='movSh',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='movDir',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='movDir_fk',
            new_name='movDir',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='movMan',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='movMan_fk',
            new_name='movMan',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='contType',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='contType_fk',
            new_name='contType',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='locPrimLH',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='locPrimLH_fk',
            new_name='locPrimLH',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='iconType',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='iconType_fk',
            new_name='iconType',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='namEnt',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='namEnt_fk',
            new_name='namEnt',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='semField',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='semField_fk',
            new_name='semField',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='wordClass',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='wordClass_fk',
            new_name='wordClass',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='wordClass2',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='wordClass2_fk',
            new_name='wordClass2',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='derivHist',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='derivHist_fk',
            new_name='derivHist',
        ),

        migrations.RemoveField(
            model_name='gloss',
            name='valence',
        ),
        migrations.RenameField(
            model_name='gloss',
            old_name='valence_fk',
            new_name='valence',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsNumSel',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsNumSel_fk',
            new_name='hsNumSel',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsFingSel',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsFingSel_fk',
            new_name='hsFingSel',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsFingSel2',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsFingSel2_fk',
            new_name='hsFingSel2',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsFingConf',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsFingConf_fk',
            new_name='hsFingConf',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsFingConf2',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsFingConf2_fk',
            new_name='hsFingConf2',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsAperture',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsAperture_fk',
            new_name='hsAperture',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsThumb',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsThumb_fk',
            new_name='hsThumb',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsSpread',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsSpread_fk',
            new_name='hsSpread',
        ),

        migrations.RemoveField(
            model_name='handshape',
            name='hsFingUnsel',
        ),
        migrations.RenameField(
            model_name='handshape',
            old_name='hsFingUnsel_fk',
            new_name='hsFingUnsel',
        ),

        migrations.RemoveField(
            model_name='morpheme',
            name='mrpType',
        ),
        migrations.RenameField(
            model_name='morpheme',
            old_name='mrpType_fk',
            new_name='mrpType',
        ),

        migrations.RemoveField(
            model_name='othermedia',
            name='type',
        ),
        migrations.RenameField(
            model_name='othermedia',
            old_name='type_fk',
            new_name='type',
        ),

    ]
