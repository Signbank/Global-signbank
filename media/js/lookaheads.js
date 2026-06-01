
var busy_editing = false;

// bloodhounds for field choices

var handedness_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Handedness'+'/%QUERY'
    });

handedness_bloodhound.initialize();

function handednesstypeahead(target) {

     $(target).typeahead(null, {
          name: 'handedness',
          displayKey: 'name',
          source: handedness_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var domhndsh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape'+'/%QUERY'
    });

domhndsh_bloodhound.initialize();

function domhndshtypeahead(target) {

     $(target).typeahead(null, {
          name: 'domhndsh',
          displayKey: 'name',
          source: domhndsh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var subhndsh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/handshape'+'/%QUERY'
    });

subhndsh_bloodhound.initialize();

function subhndshtypeahead(target) {

     $(target).typeahead(null, {
          name: 'subhndsh',
          displayKey: 'name',
          source: subhndsh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var handCh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/HandshapeChange'+'/%QUERY'
    });

handCh_bloodhound.initialize();

function handChtypeahead(target) {

     $(target).typeahead(null, {
          name: 'handCh',
          displayKey: 'name',
          source: handCh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var relatArtic_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/RelatArtic'+'/%QUERY'
    });

relatArtic_bloodhound.initialize();

function relatArtictypeahead(target) {

     $(target).typeahead(null, {
          name: 'relatArtic',
          displayKey: 'name',
          source: relatArtic_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var locprim_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Location'+'/%QUERY'
    });

locprim_bloodhound.initialize();

function locprimtypeahead(target) {

     $(target).typeahead(null, {
          name: 'locprim',
          displayKey: 'name',
          source: locprim_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var contType_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/ContactType'+'/%QUERY'
    });

contType_bloodhound.initialize();

function contTypetypeahead(target) {

     $(target).typeahead(null, {
          name: 'contType',
          displayKey: 'name',
          source: contType_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var movSh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/MovementShape'+'/%QUERY'
    });

movSh_bloodhound.initialize();

function movShtypeahead(target) {

     $(target).typeahead(null, {
          name: 'movSh',
          displayKey: 'name',
          source: movSh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var movDir_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/MovementDir'+'/%QUERY'
    });

movDir_bloodhound.initialize();

function movDirtypeahead(target) {

     $(target).typeahead(null, {
          name: 'movDir',
          displayKey: 'name',
          source: movDir_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var relOriMov_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/RelOriMov'+'/%QUERY'
    });

relOriMov_bloodhound.initialize();

function relOriMovtypeahead(target) {

     $(target).typeahead(null, {
          name: 'relOriMov',
          displayKey: 'name',
          source: relOriMov_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var relOriLoc_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/RelOriLoc'+'/%QUERY'
    });

relOriLoc_bloodhound.initialize();

function relOriLoctypeahead(target) {

     $(target).typeahead(null, {
          name: 'relOriLoc',
          displayKey: 'name',
          source: relOriLoc_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
var oriCh_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/OriChange'+'/%QUERY'
    });

oriCh_bloodhound.initialize();

function oriChtypeahead(target) {

     $(target).typeahead(null, {
          name: 'oriCh',
          displayKey: 'name',
          source: oriCh_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
var namEnt_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/NamedEntity'+'/%QUERY'
    });

namEnt_bloodhound.initialize();

function namEnttypeahead(target) {

     $(target).typeahead(null, {
          name: 'namEnt',
          displayKey: 'name',
          source: namEnt_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
var valence_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/Valence'+'/%QUERY'
    });

valence_bloodhound.initialize();

function valencetypeahead(target) {

     $(target).typeahead(null, {
          name: 'valence',
          displayKey: 'name',
          source: valence_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}

var wordClass_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/fieldchoice/WordClass'+'/%QUERY'
    });

wordClass_bloodhound.initialize();

function wordClasstypeahead(target) {

     $(target).typeahead(null, {
          name: 'wordClass',
          displayKey: 'name',
          source: wordClass_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
}
// last of the field choice bloodhounds

var selected_semField = selected_semField;

var semField_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/semField'+'/%QUERY'
    });

semField_bloodhound.initialize();

function semFieldtypeahead(target) {

     $(target).typeahead(null, {
          name: 'semField',
          displayKey: 'name',
          source: semField_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

function renderSelectedSemField() {
    var container = $('#semField_value');
    container.empty();
    var values_input = $('#semField_hidden_input_values');
    values_input.empty();
    var placeholder_lookahead = $('#semField_multiselect');
    selected_semField.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="semField" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp;&nbsp;&times;</span>').click(function() {
            selected_semField = selected_semField.filter(i => i !== item);
            renderSelectedSemField();
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
    var new_placeholder = selected_semField.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
    placeholder_lookahead.css("color", "red");
}

var selected_derivHist = selected_derivHist;

var derivHist_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/derivHist'+'/%QUERY'
    });

derivHist_bloodhound.initialize();

function derivHisttypeahead(target) {

     $(target).typeahead(null, {
          name: 'derivHist',
          displayKey: 'name',
          source: derivHist_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

function renderSelectedDerivHist() {
    var container = $('#derivHist_value');
    container.empty();
    var values_input = $('#derivHist_hidden_input_values');
    values_input.empty();
    var placeholder_lookahead = $('#derivHist_multiselect');
    selected_derivHist.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="derivHist" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp;&nbsp;&times;</span>').click(function() {
            selected_derivHist = selected_derivHist.filter(i => i !== item);
            renderSelectedDerivHist();
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
    var new_placeholder = selected_derivHist.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
}

var selected_dialect = selected_dialect;

var dialect_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/dialect/'+gloss_dataset_id+'/%QUERY'
    });

dialect_bloodhound.initialize();

function dialecttypeahead(target) {

     $(target).typeahead(null, {
          name: 'dialect',
          displayKey: 'name',
          source: dialect_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(fc) {
                  return("<p><strong>" + fc.name +  "</strong></p>");
              }
          }
      });
};

function renderSelectedDialect() {
    var container = $('#dialect_value');
    container.empty();
    var values_input = $('#dialect_hidden_input_values');
    values_input.empty();
    var placeholder_lookahead = $('#dialect_multiselect');
    selected_dialect.forEach(function(item) {
        var tag = $('<button class="actionButton"></button>').text(item.name);
        var input_value = $('<input type="hidden" name="dialect" value="'+item.machine_value+'">');
        var removeBtn = $('<span class="remove">&nbsp;&nbsp;&times;</span>').click(function() {
            selected_dialect = selected_dialect.filter(i => i !== item);
            renderSelectedDialect();
        });
        tag.append(removeBtn);
        container.append(tag);
        values_input.append(input_value);
    });
    var new_placeholder = selected_dialect.map(item => item.name).join(", ");
    placeholder_lookahead.attr("placeholder", new_placeholder);
    placeholder_lookahead.css("color", "red");
}

var lemma_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/lemma/'+gloss_dataset_id+'/'+gloss_default_language_code+'/%QUERY'
    });

lemma_bloodhound.initialize();

function lemmatypeahead(target) {

     $(target).typeahead(null, {
          name: 'lemmatarget',
          displayKey: 'lemma',
          limit: 10,
          source: lemma_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(lemma) {
                  return("<p><strong>" + lemma.lemma + "</strong></p>");
              }
          }
      });
};

var gloss_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/gloss/'+gloss_dataset_id+'/%QUERY'
    });

gloss_bloodhound.initialize();

function glosstypeahead(target) {

     $(target).typeahead(null, {
          name: 'glosstarget',
          displayKey: 'annotation_idgloss',
          source: gloss_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  return("<p><strong>" + gloss.annotation_idgloss +  "</strong></p>");
              }
          }
      });
};

var morph_bloodhound = new Bloodhound({
      datumTokenizer: function(d) { return d.tokens; },
      queryTokenizer: Bloodhound.tokenizers.whitespace,
      remote: url+'/dictionary/ajax/morph/%QUERY'
    });

morph_bloodhound.initialize();

function morphtypeahead(target) {

     $(target).typeahead(null, {
          name: 'morphtarget',
          displayKey: 'annotation_idgloss',
          source: morph_bloodhound.ttAdapter(),
          templates: {
              suggestion: function(gloss) {
                  return("<p><strong>" + gloss.annotation_idgloss + "</strong></p>");
              }
          }
      });
};

$("#show_set_lemma_form").on('click', function() {
    $('#lemma_forms_row').show();
    $("#set_lemma_form").show();
    $('#lemma_buttons').hide();
    $('#add_lemma_form').hide();
});

$("#show_create_lemma_form").on('click', function() {
    $('#lemma_forms_row').show();
    $('#add_lemma_form').show();
    $('#lemma_buttons').hide();
    $("#set_lemma_form").hide();
});

$(".lemma-form-dismiss").on('click', function() {
    var this_form = $(this).parent().attr('id');
    if (this_form === 'set_lemma_form') {
        $('#lemma_forms_row').hide();
    } else {
        $('#add_lemma_form').hide();
    }
    $('#lemma_buttons').show();
});

function disable_edit_morphology() {
    $('#add_morphologydefinition_form').hide();
    $('#add_morphemedefinition_form').hide();
    $('#add_blenddefinition_form').hide();
    $('.morphology_delete_edit_only').each(function() {
        $(this).hide();
    });
    $('.button-morphology-to-appear-in-edit-mode').hide();
    $('.empty_row_morphology').each(function() {
        $(this).hide();
    });
}

$(".morphology-edit-dismiss").on('click', function() {
    $('#add_morphologydefinition_form').hide();
    $('#add_morphemedefinition_form').hide();
    $('#add_blenddefinition_form').hide();
    $('.morphology_delete_edit_only').each(function() {
        $(this).hide();
    });
    $(this).hide();
    $('#enable_edit_morphology').show();
    $('.empty_row_morphology').each(function() {
        $(this).hide();
    });
});

$("#enable_edit_morphology").on('click', function() {
    $('#add_morphologydefinition_form').show();
    $('#add_morphemedefinition_form').show();
    $('#add_blenddefinition_form').show();
    $('.morphology_delete_edit_only').each(function() {
        $(this).show();
    });
    $('.empty_row_morphology').each(function() {
        $(this).show();
    });
    $('.button-morphology-to-appear-in-edit-mode').show();
    $(this).hide();
});

function disable_edit_relations() {
    $('#add_relation_form').hide();
    $('.relation_delete_edit_only').each(function() {
        $(this).hide();
    });
    $('.button-relations-to-appear-in-edit-mode').hide();
}

$(".relation-edit-dismiss").on('click', function() {
    $('#add_relation_form').hide();
    $('.relation_delete_edit_only').each(function() {
        $(this).hide();
    });
    $(this).hide();
    $('#enable_edit_relations').show();
});

$("#enable_edit_relations").on('click', function() {
    $('#add_relation_form').show();
    $('.relation_delete_edit_only').each(function() {
        $(this).show();
    });
    $('.button-relations-to-appear-in-edit-mode').show();
    $(this).hide();
});

function ajaxifyTagForm() {
    // ajax form submission for tag addition and deletion
    $('.tagdelete').click(function() {
        var action = $(this).attr('href');
        var tagid = $(this).attr('id');
        var tagelement = $(this).parents('.tagli');

        $.post(action,
              {tag: tagid, 'delete': "True" },
               function(data) {
                    if (data === 'deleted') {
                        // remove the tag from the page
                       tagelement.remove();
                    }
               });

        return false;
    });

    $('#tagaddform').submit(function(){

        var newtag = $('#tagaddform select').val();

        if (newtag != "") {
            $.post($(this).attr('action'), $(this).serialize(),
                    function(data) {
                       // response is a new tag list
                       $('#tags').replaceWith(data);
                       ajaxifyTagForm();
                   });
        } else {
            alert("Please select a tag value.");
        }

        return false;
    });
}

function disable_lookaheads(category) {
     // this makes use of specific element identifiers for the lookahead fields
     $('.form-control').each(function() {
         var this_id = $(this).attr('id');
         if (!this_id) {return;}
         var data_category = $(this).attr('data-category');
         if (!data_category) {return;}
         if (data_category != category) {return;}
         if (this_id.endsWith("_lookahead")) {
             $(this).attr('disabled', true);
             return;
         }
         if (this_id.endsWith("_value")) {
             $(this).attr('disabled', true);
         }
         if (this_id.endsWith("_text")) {
             $(this).attr('disabled', true);
         }
         if (this_id.endsWith("_multiselect")) {
             $(this).attr('disabled', true);
         }
     });
}

function enable_lookaheads(category) {
     // this makes use of specific element identifiers for the lookahead fields
     $('.form-control').each(function() {
         var this_id = $(this).attr('id');
         if (!this_id) {return;}
         var data_category = $(this).attr('data-category');
         if (!data_category) {return;}
         if (data_category != category) {return;}
         if (this_id.endsWith("_lookahead")) {
             $(this).removeAttr('disabled');
             return;
         }
         if (this_id.endsWith("_value")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.endsWith("_text")) {
             $(this).removeAttr('disabled');
         }
         if (this_id.endsWith("_multiselect")) {
             $(this).removeAttr('disabled');
         }
     });
}

function enable_edit_panel(category) {
    if (category === 'semantics') {
        $('.editsemanticsform').show();
        $('#semField_value').trigger('editSemField');
        $('#derivHist_value').trigger('editDerivHistField');
    }
    if (category === 'general') {
        $('.read_only').hide();
        $('.edit_only').show();
        $('.editdialectform').show();
        $('.editform').show();  // appears in gloss tags and affiliations
        $('#dialect_value').trigger('editDialectField');
        $('#lemma_buttons_group').show();
    }
    $('.empty_row_'+category).show();
    $('#enable_edit_'+category).addClass('edit_enabled');
    $('#enable_edit_'+category).hide();
    $('.button-'+category+'-to-appear-in-edit-mode').show();
    enable_lookaheads(category);
}

function disable_edit_panel(category) {
    if (category === 'semantics') {
        $('.editsemanticsform').hide();
    }
    if (category === 'general') {
        $('.editdialectform').hide();
        $('#lemma_buttons_group').hide();
        $('#lemma_forms_row').hide();
        $('.editform').hide();  // appears in gloss tags and affiliations
        $('.read_only').show();
        $('.edit_only').hide();
    }
    $('.empty_row_'+category).hide();
    $('.button-'+category+'-to-appear-in-edit-mode').hide();
    $('#enable_edit_'+category).removeClass('edit_enabled');
    $('#enable_edit_'+category).show();
    disable_lookaheads(category);
    busy_editing = false;
}

function toggle_edit_general() {
    if ($('#enable_edit_general').hasClass('edit_enabled'))
    {
        disable_edit_panel('general');
    } else {
        enable_edit_panel('general');
    }
}

function toggle_edit_phonology() {
    if ($('#enable_edit_phonology').hasClass('edit_enabled'))
    {
        disable_edit_panel('phonology');
    } else {
        enable_edit_panel('phonology');
    }
}

function toggle_edit_semantics() {
    if ($('#enable_edit_semantics').hasClass('edit_enabled'))
    {
        disable_edit_panel('semantics');
    } else {
        enable_edit_panel('semantics');
    }
}

function get_width_of_selection(text) {
    let $span = $('<span>')
        .text(text)
        .css({
            position: 'absolute',
            visibility: 'hidden',
            whiteSpace: 'nowrap',
        })
        .appendTo('body');
    let width = $span.width();
    $span.remove();
    return width;
}

$(document).ready(function() {

    handednesstypeahead($('.handednesstypeahead'));
    $('.handednesstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#handedness_machine_value').attr('value', suggestion.machine_value);
    });
    $('#handedness_lookahead').on("click", function() {
      // this erases the lookahead value shown as placeholder
      $(this).attr('value', "");
    });
    domhndshtypeahead($('.domhndshtypeahead'));
    $('.domhndshtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#domhndsh_machine_value').attr('value', suggestion.machine_value);
    });
    $('#domhndsh_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    subhndshtypeahead($('.subhndshtypeahead'));
    $('.subhndshtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          var width_of_new_value = suggestion.name.length * 10 + 30;
          $(this).css("width", width_of_new_value + "px");
          $('#subhndsh_machine_value').attr('value', suggestion.machine_value);
    });
    $('#subhndsh_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    handChtypeahead($('.handChtypeahead'));
    $('.handChtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#handCh_machine_value').attr('value', suggestion.machine_value);
    });
    $('#handCh_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    relatArtictypeahead($('.relatArtictypeahead'));
    $('.relatArtictypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#relatArtic_machine_value').attr('value', suggestion.machine_value);
    });
    $('#relatArtic_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    locprimtypeahead($('.locprimtypeahead'));
    $('.locprimtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#locprim_machine_value').attr('value', suggestion.machine_value);
    });
    $('#locprim_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    contTypetypeahead($('.contTypetypeahead'));
    $('.contTypetypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#contType_machine_value').attr('value', suggestion.machine_value);
    });
    $('#contType_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    movShtypeahead($('.movShtypeahead'));
    $('.movShtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#movSh_machine_value').attr('value', suggestion.machine_value);
    });
    $('#movSh_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    movDirtypeahead($('.movDirtypeahead'));
    $('.movDirtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#movDir_machine_value').attr('value', suggestion.machine_value);
    });
    $('#movDir_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    relOriMovtypeahead($('.relOriMovtypeahead'));
    $('.relOriMovtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#relOriMov_machine_value').attr('value', suggestion.machine_value);
    });
    $('#relOriMov_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    relOriLoctypeahead($('.relOriLoctypeahead'));
    $('.relOriLoctypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#relOriLoc_machine_value').attr('value', suggestion.machine_value);
    });
    $('#relOriLoc_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    oriChtypeahead($('.oriChtypeahead'));
    $('.oriChtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#oriCh_machine_value').attr('value', suggestion.machine_value);
    });
    $('#oriCh_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    namEnttypeahead($('.namEnttypeahead'));
    $('.namEnttypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#namEnt_machine_value').attr('value', suggestion.machine_value);
    });
    $('#namEnt_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    valencetypeahead($('.valencetypeahead'));
    $('.valencetypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#valence_machine_value').attr('value', suggestion.machine_value);
    });
    $('#valence_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    wordClasstypeahead($('.wordClasstypeahead'));
    $('.wordClasstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          busy_editing = true;
          $(this).attr('value', suggestion.name);
          $('#wordClass_machine_value').attr('value', suggestion.machine_value);
    });
    $('#wordClass_lookahead').on("click", function() {
      $(this).attr('value', "");
    });
    semFieldtypeahead($('.semFieldtypeahead'));
    $('.semFieldtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          if (!selected_semField.includes(suggestion)) {
                busy_editing = true;
                selected_semField.push(suggestion);
                renderSelectedSemField();
          }
          $(this).typeahead('val', '');
    });
    $('#semField_multiselect').on("click", function() {
      $(this).attr('value', "");
    });
    $('#semField_value').on("editSemField", function() {
        renderSelectedSemField();
    });
    derivHisttypeahead($('.derivHisttypeahead'));
    $('.derivHisttypeahead').bind('typeahead:selected', function(ev, suggestion) {
          if (!selected_derivHist.includes(suggestion)) {
                busy_editing = true;
                selected_derivHist.push(suggestion);
                renderSelectedDerivHist();
          }
          $(this).typeahead('val', '');
    });
    $('#derivHist_multiselect').on("click", function() {
      $(this).attr('value', "");
    });
    $('#derivHist_value').on("editDerivHistField", function() {
        renderSelectedDerivHist();
    });
    dialecttypeahead($('.dialecttypeahead'));
    $('.dialecttypeahead').bind('typeahead:selected', function(ev, suggestion) {
          if (!selected_dialect.includes(suggestion)) {
                busy_editing = true;
                selected_dialect.push(suggestion);
                renderSelectedDialect();
          }
          $(this).typeahead('val', '');
    });
    $('#dialect_multiselect').on("click", function() {
      $(this).attr('value', "");
    });
    $('#dialect_value').on("editDialectField", function() {
        renderSelectedDialect();
    });
    lemmatypeahead($('.lemmatypeahead'));
    $('.lemmatypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk);
          busy_editing = true;
          $('#new_lemma_pk').attr('value', suggestion.pk);
    });
    $('.lemmatypeahead').on("click", function() {
          $(this).parent().next().val("");
    });
    glosstypeahead($('.glosstypeahead'));
    $('.glosstypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk);
          var target_gloss_lookahead = $(this).attr("id");
          busy_editing = true;
          var width_of_new_value = suggestion.annotation_idgloss.length * 8 + 20;
          $(this).css("width", width_of_new_value + "px");
          $('#'+target_gloss_lookahead+'_id').attr('value', suggestion.pk);
    });
    $('.glosstypeahead').on("input", function() {
          $(this).parent().next().val("");
    });
    morphtypeahead($('.morphtypeahead'));
    $('.morphtypeahead').bind('typeahead:selected', function(ev, suggestion) {
          $(this).parent().next().val(suggestion.pk);
          var target_morph_lookahead = $(this).attr("id");
          busy_editing = true;
          var width_of_new_value = suggestion.annotation_idgloss.length * 8 + 20;
          $(this).css("width", width_of_new_value + "px");
          $('#'+target_morph_lookahead+'_id').attr('value', suggestion.pk);
    });
    $('.morphtypeahead').on("input", function() {
          $(this).parent().next().val("")
    });
    $('.select_weakdrop').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#weakdrop_value').text(selected_text);
    });

    $('.select_weakprop').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#weakprop_value').text(selected_text);
    });

    $('.select_domhndsh_letter_or_number_field').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#domhndsh_letter_or_number_field_value').text(selected_text);
    });

    $('.select_subhndsh_letter_or_number').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#subhndsh_letter_or_number_value').text(selected_text);
    });

    $('.select_repeat').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#repeat_value').text(selected_text);
    });
    $('.select_altern').on('change', function() {
          busy_editing = true;
          var selected_value = $(this).val();
          var selected_text = $(this).find('option:selected').text();
          $('#altern_value').text(selected_text);
    });
     $('.quick_save').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var update = { 'csrfmiddlewaretoken': csrf_token };
         for (var i=0; i < gloss_fields.length; i++) {
            var field = gloss_fields[i];
            if (['semField', 'derivHist', 'dialect'].includes(field)) {
                var field_values = [];
                var field_lookup = '#'+field+'_hidden_input_values';
                $(field_lookup).find('input[name="'+field+'"]').each(function() {
                    var this_value = $(this).val();
                    field_values.push(this_value);
                });
                update[field] = field_values;
            } else if (['weakdrop', 'weakprop'].includes(field)) {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (['domhndsh_letter_or_number', 'subhndsh_letter_or_number'].includes(field)) {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (['repeat', 'altern'].includes(field)) {
                var field_lookup = '#'+field+'_select_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else if (['release_information', 'useInstr', 'locVirtObj', 'phonOth', 'mouthG', 'mouthing', 'phonetVar', 'iconImg'].includes(field)) {
                var field_lookup = '#'+field+'_text';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            } else {
                var field_lookup = '#'+field+'_machine_value';
                var field_key = $(field_lookup).attr("name");
                var field_value = $(field_lookup).val();
                update[field_key] = field_value;
            }
         }
         $.ajax({
            url : url + "/dictionary/update/edit_gloss_save/" + glossid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_set_lemma').click(function(e)
	 {
         e.preventDefault();
	     var set_lemma_url = $('#set_lemma_form').attr("action");
	     var new_lemma_pk = $('#new_lemma_pk').attr('value');
	     var update = { 'csrfmiddlewaretoken': csrf_token };
	     update['new_lemma_pk'] = new_lemma_pk;
         $.ajax({
            url : set_lemma_url,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     $('.quick_set_annotation').click(function(e)
	 {
         e.preventDefault();
         var update = { 'csrfmiddlewaretoken': csrf_token };
         var button_id = $(this).attr('id');
         var glossid = $(this).attr('value');
         var language_field = '#'+button_id.slice('button_'.length);
	     var value = $(language_field).val();
         var language_code_2char = $(this).attr('data-language');
         update['language_code_2char'] = language_code_2char;
	     update['value'] = value;
         $.ajax({
            url : url + "/dictionary/update/update_gloss_annotation/" + glossid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : function(data) {
                if (data.success) {
                    setTimeout(function() {
                        location.reload(true);
                    }, 500);
                }
            },
            error: function (xhr, status, error) {
                alert("There was an error processing this change: " + xhr.responseText );
            }
         });
     });
     var lookahead_elements = $('[id*="_lookahead"]');
     lookahead_elements.each(function() {
         var this_id = $(this).attr("id");
         var cell_lookup = '#' + this_id.slice(0, -'_lookahead'.length) + '_cell';
         var width_of_new_value = $(this).attr("value").length * 10 + 30;
         $(cell_lookup).attr('data-width', width_of_new_value);
    });
    var cell_elements = $('[id*="_cell"]');
    cell_elements.each(function() {
        var this_width = $(this).attr("data-width") + "px";
        $(this).css('width', this_width);
        var tt_children = $(this).find('.tt-input');
        $(tt_children).each(function() {
            $(this).css('width', this_width);
        });
    });
    busy_editing = false;
    $('#enable_edit_general').on("click", function() {
        toggle_edit_general();
    });
    $('#enable_edit_phonology').on("click", function() {
        toggle_edit_phonology();
    });
    $('#enable_edit_semantics').on("click", function() {
        toggle_edit_semantics();
    });
    disable_edit_panel('general');
    disable_edit_panel('phonology');
    disable_edit_panel('semantics');
    disable_edit_relations();
    disable_edit_morphology();
    ajaxifyTagForm();
});
