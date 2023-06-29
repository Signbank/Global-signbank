// javascript for template admin_keyword_list.html
// this code uses json ajax calls

function update_gloss_senses(data) {
    // this success function is called for a specific language
    // it updates all relevant html for the specific gloss
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var changed_language = data.language;
    var keywords = data.keywords;
    var senses_groups = data.senses_groups;
    if ($.isEmptyObject(senses_groups)) {
        return;
    };
    var regrouped_keywords = data.regrouped_keywords;
    var dataset_languages = data.dataset_languages;
    var deleted_sense_numbers = data.deleted_sense_numbers;

    var keywords_glossid = '#tbody_keywords_' + glossid + '_' + changed_language;
    var keywordsCell = $(keywords_glossid);
    $(keywordsCell).empty();
    var row = $("<tr/>");
    var num_commas = keywords.length - 1;
    for (var key in keywords) {
        if (num_commas > 0 && key < num_commas) {
            row.append("<span>"+keywords[key]+"</span>, ");
        } else {
            row.append("<span>"+keywords[key]+"</span>");
        }
    }
    row.append("</td>");
    keywordsCell.append(row);

    var senses_glossid = '#tbody_senses_' + glossid + '_' + changed_language;
    var sensesCell = $(senses_glossid);
    $(sensesCell).empty();
    for (var key in senses_groups) {
        var senses_row_id = 'senses_' + glossid  + '_' + changed_language + '_row_' + key;
        var row = $('<tr id="'+ senses_row_id + '"/>');
        row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (num_commas > 0 && inx < num_commas) {
                row.append("<span>"+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        sensesCell.append(row);
    }
    sensesCell.append("</tr>");

    var modal_senses_glossid = '#tbody_modal_senses_' + glossid + '_' + changed_language;
    var modalSensesCell = $(modal_senses_glossid);
    $(modalSensesCell).empty();
    for (var key in senses_groups) {
        var senses_row_id = 'modal_senses_' + glossid +'_' + changed_language +'_row_' + key;
        var cell_id = 'modal_senses_order_language_cell_' + glossid +'_' + changed_language + '_' + key;
        var row = $('<tr id="'+ senses_row_id + '"/>');
        row.append("<td>"+key+'.</td><td id="'+ cell_id + '"/>');
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            var span_id = 'sensegroup_' + glossid + '_' + key + '_' + changed_language + '_' + group_keywords[inx][0];
            if (num_commas > 0 && inx < num_commas) {
                row.append('<span id="'+ span_id + '">'+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append('<span id="'+ span_id + '">'+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        modalSensesCell.append(row);
    }
    modalSensesCell.append("</tr>");

    var modal_senses_groups_glossid = '#tbody_senses_table_' + glossid + '_' + changed_language;
    var modalSensesGroupsCell = $(modal_senses_groups_glossid);
    $(modalSensesGroupsCell).empty();
    var last_index = keywords.length - 1;
    for (var key in senses_groups) {
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            var sense_keyword = group_keywords[inx];
            var keywords_update_row_id = 'keywords_regroup_row_' + glossid + '_' + changed_language + '_' + sense_keyword[0];
            var row = $('<tr id="' + keywords_update_row_id + '"/>');
            // the new row gets as id the max index of the keywords
            row.append('<td id="keyword_sense_index_'+glossid+'_'+changed_language+'_'+sense_keyword[0]+'" >'+sense_keyword[1]);
            row.append('<input type="hidden" id="sense_id_'+sense_keyword[0]+
                            '" name="group_index" value="'+sense_keyword[0]+'" data-group_index="'+sense_keyword[0]+'">');
            row.append("</td>");
            row.append('<td><input type="number" id="regroup_'+key+
                                    '" name="regroup" size="5" value="'+key+
                                    '" data-regroup="'+key+'" >');
            row.append("</td>");
            row.append("</tr>");
            modalSensesGroupsCell.append(row);
        }
    }
    modalSensesGroupsCell.append("</tr>");

    var modal_edit_keywords_glossid = '#edit_keywords_table_' + glossid + '_' + changed_language;
    var modalEditKeywordsCell = $(modal_edit_keywords_glossid);
    $(modalEditKeywordsCell).empty();
    var last_index = keywords.length - 1;
    for (var key in senses_groups) {
        var group_keywords = senses_groups[key];
        for (var inx in group_keywords) {
            var sense_keyword = group_keywords[inx];
            // update text in senses matrix
            var input_text_element_id = '#sense_translation_text_' + glossid + '_' + changed_language + '_' + sense_keyword[0];
            $(input_text_element_id).attr('value', sense_keyword[1]);
            $(input_text_element_id).attr('data-translation', sense_keyword[1]);
            // add new row to update text panel of language modal
            var keywords_row = 'edit_keywords_row_' + glossid + '_' + changed_language + '_' + sense_keyword[0];
            var row = $('<tr id="' + keywords_row + '"/>');
            row.append('<td><input type="text" id="edit_keyword_text_' + glossid + '_' + changed_language + '_' + sense_keyword[0] +
                                    '" name="translation" size="40" value="'+sense_keyword[1]+
                                    '" data-translation="'+sense_keyword[1]+'">');
            row.append('<input type="hidden" id="keyword_index_'+sense_keyword[0]+
                            '" name="keyword_index" value="'+sense_keyword[0]+'" data-index="'+sense_keyword[0]+'">');
            row.append("</td>");
            row.append("</tr>");
            modalEditKeywordsCell.append(row);
        }
        modalEditKeywordsCell.append("</tr>");
    }

    var tbody_modal_senses = '#tbody_modal_sensetranslations_' + glossid;
    var modalSensesTable = $(tbody_modal_senses);

    for (var i=0; i < regrouped_keywords.length; i++) {
        var originalIndex = regrouped_keywords[i]['originalIndex'];
        var orderIndex = regrouped_keywords[i]['orderIndex'];
        var langid = regrouped_keywords[i]['language'];
        var sense_id = regrouped_keywords[i]['sense_id'];
        var span_id = '#span_cell_' + glossid + '_' + langid + '_' + sense_id;
        // this is the cell for the sense keyword
        var spanTDParent = $(span_id).parent();
        var spanCell = $(span_id).detach();
        var spanCellOrderInput = spanCell.find('input[name="order_index"]').first();
        spanCellOrderInput.attr('data-order_index', orderIndex).attr('value', orderIndex);
        // replace with an empty cell
        var span = $('<span class="span-cell"/>');
        span.append('<input type="text" size="40" data-order_index="'+orderIndex + '" data-language="'+
                    langid+'" name="new_translation">');
        span.append('<input type="hidden" name="new_order_index" value="'+orderIndex+'" data-new_order_index="'+orderIndex+'">');
        span.append('<input type="hidden" name="new_language" value="'+langid+'" data-new_language="'+
                            langid+'">');
        span.append("</span>");
        spanTDParent.append(span);
        // this is the TD for the language of the original sense order index
        var order_index_row = 'modal_sensetranslations_' + glossid + '_row_' + orderIndex;

        if (!$('#'+order_index_row).length) {
            // no row for sense order index
            var row = $('<tr id="'+ order_index_row + '"/>');
            row.append("<td>"+orderIndex+'.</td>');
            for (var inx in dataset_languages) {
                var cell_lang = 'sense_translations_' + glossid + '_' + dataset_languages[inx] + '_' + orderIndex;
                var cellTD = $('<td id="'+ cell_lang + '"/>');
                if (changed_language == dataset_languages[inx]) {
                    cellTD.append(spanCell);
                } else {
                    var span = $('<span class="span-cell"/>');
                    span.append('<input type="text" size="40" data-order_index="'+orderIndex + '" data-language="'+
                                dataset_languages[inx]+'" name="new_translation">');
                    span.append('<input type="hidden" name="new_order_index" value="'+orderIndex+'" data-new_order_index="'+orderIndex+'">');
                    span.append('<input type="hidden" name="new_language" value="'+dataset_languages[inx]+'" data-new_language="'+
                                        dataset_languages[inx]+'">');
                    span.append("</span>");
                    cellTD.append(span);
                }
                cellTD.append("</td>");
                row.append(cellTD);
            row.append("</tr>");
            modalSensesTable.append(row);
            }
        } else {
            for (var inx in dataset_languages) {
                var cell_lang = 'sense_translations_' + glossid +'_' + dataset_languages[inx] + '_' + orderIndex;
                var senseLangCell = $('#'+cell_lang);
                if (changed_language == dataset_languages[inx]) {
                    senseLangCell.append(spanCell);
                } else {
                    var span = $('<span class="span-cell"/>');
                    span.append('<input type="text" size="40" data-order_index="'+orderIndex + '" data-language="'+
                                dataset_languages[inx]+'" name="new_translation">');
                    span.append('<input type="hidden" name="new_order_index" value="'+orderIndex+'" data-new_order_index="'+orderIndex+'">');
                    span.append('<input type="hidden" name="new_language" value="'+dataset_languages[inx]+'" data-new_language="'+
                                        dataset_languages[inx]+'">');
                    span.append("</span>");
                    senseLangCell.append(span);
                }
            }
        }
    }
    // remove table rows with empty senses
    for (var order in deleted_sense_numbers) {
        var empty_row_id = '#modal_sensetranslations_' + glossid + '_row_'
                                    + deleted_sense_numbers[order];
        var empty_row = $(empty_row_id);
        if (empty_row.length) {
            empty_row.remove();
        }
    }
    for (var inx in dataset_languages) {
        for (var order in deleted_sense_numbers) {
            var tbody = $('#tbody_senses_' + glossid  + '_' + dataset_languages[inx]);
            var outer_senses_row_id = '#senses_' + glossid  + '_'
                                    + dataset_languages[inx] + '_row_' + deleted_sense_numbers[order];
            var outer_senses_row = $(outer_senses_row_id);
            if (outer_senses_row) {
                outer_senses_row.empty();
                outer_senses_row.remove();
            }
            var tbody = $('#tbody_modal_senses_' + glossid  + '_' + dataset_languages[inx]);
            var sense_row_id = '#modal_senses_' + glossid + '_'
                                    + dataset_languages[inx] + '_row_' + deleted_sense_numbers[order];
            var sense_row = $(sense_row_id);
            if (sense_row) {
                sense_row.empty();
                sense_row.remove();
            }
        }
    }
}

// the following function expects more fields from the ajax call json data
// it adds new rows to tables
function add_gloss_keywords(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var keywords = data.keywords;
    var senses_groups = data.senses_groups;
    if ($.isEmptyObject(senses_groups)) {
        return;
    };
    var new_sense_keywords = data.new_translations;
    var translations_row = data.translations_row;
    var new_sense_number = data.new_sense;
    var dataset_languages = data.dataset_languages;

    for (var language in keywords) {
        var keywords_glossid = '#tbody_keywords_' + glossid + '_' + language;
        var keywordsCell = $(keywords_glossid);
        $(keywordsCell).empty();
        var language_keywords = keywords[language];
        num_commas = language_keywords.length - 1;
        var row = $("<tr/>");
        row.append("<td/>");
        for (var inx in language_keywords) {
            if (num_commas > 0 && inx < num_commas) {
                row.append("<span>"+language_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+language_keywords[inx]+"</span>");
            }
        }
        row.append("</td></tr>");
        keywordsCell.append(row);
    }
    for (var language in senses_groups) {
        var senses_glossid = '#tbody_senses_' + glossid + '_' + language;
        var sensesCell = $(senses_glossid);
        $(sensesCell).empty();
        var language_senses = senses_groups[language];
        for (var key in language_senses) {
            var senses_row_id = 'senses_' + glossid  + '_' + language + '_row_' + key;
            var row = $('<tr id="'+ senses_row_id + '"/>');
            row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
            var group_keywords = language_senses[key];
            num_commas = group_keywords.length - 1;
            for (var inx in group_keywords) {
                if (num_commas > 0 && inx < num_commas) {
                    row.append("<span>"+group_keywords[inx][1]+"</span>, ");
                } else {
                    row.append("<span>"+group_keywords[inx][1]+"</span>");
                }
            };
            row.append("</td></tr>");
            sensesCell.append(row);
        }
    }

    for (var language in senses_groups) {
        var modal_senses_glossid = '#tbody_modal_senses_' + glossid + '_' + language;
        var modalSensesCell = $(modal_senses_glossid);
        $(modalSensesCell).empty();
        var language_senses = senses_groups[language];
        for (var key in language_senses) {
            var senses_row_id = 'modal_senses_' + glossid +'_' + language +'_row_' + key;
            var cell_id = 'modal_senses_order_language_cell_' + glossid +'_' + language + '_' + key;
            var row = $('<tr id="'+ senses_row_id + '"/>');
            row.append("<td>"+key+'.</td><td id="'+ cell_id + '"/>');
            var group_keywords = language_senses[key];
            var num_commas = group_keywords.length - 1;
            for (var inx in group_keywords) {
                var span_id = 'sensegroup_' + glossid + '_' + key + '_' + language + '_' + group_keywords[inx][0];
                if (num_commas > 0 && inx < num_commas) {
                    row.append('<span id="'+span_id+'">'+group_keywords[inx][1]+"</span>, ");
                } else {
                    row.append('<span id="'+span_id+'">'+group_keywords[inx][1]+"</span>");
                }
            };
            row.append("</td>");
            modalSensesCell.append(row);
        }
        modalSensesCell.append("</tr>");
    }
    // this updates both language modals as the languages are both stored in the list if non-empty
    for (var i=0; i < new_sense_keywords.length; i++) {
        var new_trans_id = new_sense_keywords[i]['new_trans_id'];
        var language = new_sense_keywords[i]['new_language'];
        var new_text = new_sense_keywords[i]['new_text'];
        var modal_senses_groups_glossid = '#tbody_senses_table_' + glossid + '_' + language;
        var modalSensesGroupsCell = $(modal_senses_groups_glossid);

        var keywords_update_row_id = 'keywords_regroup_row_' + glossid + '_' + language + '_' + new_trans_id;
        var row = $('<tr id="' + keywords_update_row_id + '"/>');
        // the new row gets as id the max index of the keywords
        row.append('<td id="keyword_sense_index_'+glossid+'_'+language+'_'+new_trans_id+'" />'+new_text);
        row.append("</td>");
        row.append('<td><input type="number" id="regroup_'+new_sense_number+
                                '" name="regroup" size="5" value="'+new_sense_number+
                                '" data-regroup="'+new_sense_number+'" >');
        row.append('<input type="hidden" id="sense_id_'+new_trans_id+
                        '" name="group_index" value="'+new_trans_id+'" data-group_index="'+new_trans_id+'">');
        row.append("</td>");
        row.append("</tr>");
        modalSensesGroupsCell.append(row);
        modalSensesGroupsCell.append("</tr>");

        var modal_edit_keywords_glossid = '#edit_keywords_table_' + glossid + '_' + language;
        var modalEditKeywordsCell = $(modal_edit_keywords_glossid);

        var row = $("<tr/>");
        row.append('<td><input type="text" id="edit_keyword_text_' + glossid + '_' + language + '_' +new_trans_id+
                                '" name="translation" size="40" value="'+new_text+
                                '" data-translation="'+new_text+'">');
        row.append('<input type="hidden" id="keyword_index_'+new_trans_id+
                        '" name="keyword_index" value="'+new_trans_id+'" data-index="'+new_trans_id+'">');
        row.append("</td>");
        row.append("</tr>");
        modalEditKeywordsCell.append(row);
        modalEditKeywordsCell.append("</tr>");
    }
    // new_sense_number is orderIndex of new sense
    // new_sense_id is id of new translation
    // new text is keywords[last_index]
    var tbody_modal_senses = '#tbody_modal_sensetranslations_' + glossid;
    var modalSensesTable = $(tbody_modal_senses);
    var order_index_row = 'modal_sensetranslations_' + glossid + '_row_' + new_sense_number;
    // no row for sense order index
    var row = $('<tr id="'+ order_index_row + '"/>');
    row.append("<td>"+new_sense_number+'.</td>');
    for (var langid in translations_row) {
        var new_trans_id = translations_row[langid]['new_trans_id']
        var new_text = translations_row[langid]['new_text']
        var cell_lang = 'sense_translations_' + glossid + '_' + langid + '_' + new_sense_number;
        var cellTD = '<td id="'+ cell_lang + '"/>';
        if (new_text) {
            var span_id = 'span_cell_' + glossid + '_' + langid + '_' + new_trans_id;
            var span = $(cellTD + '<span class="span-cell" id="'+span_id+'"/>');
            span.append('<input type="text" id="sense_translation_text_' + glossid + '_' + langid + '_' + new_trans_id +
                        '" name="translation" size="40" value="'+new_text+
                        '" data-translation="'+new_text+'">');
            span.append('<input type="hidden" name="sense_id" value="'+new_trans_id+'" data-sense_id="'+new_trans_id+'">');
            span.append('<input type="hidden" name="order_index" value="'+new_sense_number+'" data-order_index="'+new_sense_number+'">');
            span.append('<input type="hidden" name="language" value="'+langid+'" data-language="'+langid+'">');
            span.append("</span>").append("</td>");
            row.append(span);
        } else {
            var span = $(cellTD + '<span class="span-cell"/>');
            span.append('<input type="text" size="40" data-order_index="'+new_sense_number + '" data-language="'+
                        langid+'" name="new_translation">');
            span.append('<input type="hidden" name="new_order_index" value="'+new_sense_number+'" data-new_order_index="'+new_sense_number+'">');
            span.append('<input type="hidden" name="new_language" value="'+langid+'" data-new_language="'+
                                langid+'">');
            span.append("</span>").append("</td>");
            row.append(span);
        }
    }
    modalSensesTable.append(row).append("</tr>");
}

function toggle_sense_tag(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var tags_list = data.tags_list;
    var tagsCell = $("#tags_cell_"+glossid);
    $(tagsCell).empty();
    var cell = "";
    var num_spaces = tags_list.length - 1;
    for (var key in tags_list) {
        if (key < num_spaces) {
            cell = cell + "<span class='tag'>"+tags_list[key]+"</span> ";
        } else {
            cell = cell + "<span class='tag'>"+tags_list[key]+"</span>";
        }
    }
    tagsCell.html(cell);
}

function update_matrix(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var keywords = data.keywords;
    var senses_groups = data.senses_groups;
    if ($.isEmptyObject(senses_groups)) {
        return;
    };
    var updated_translations = data.updated_translations;
    var new_translations = data.new_translations;
    var deleted_translations = data.deleted_translations;

    for (var i=0; i < new_translations.length; i++) {
        var inputEltIndex = new_translations[i]['inputEltIndex'];
        var orderIndex = new_translations[i]['orderIndex'];
        var sense_id = new_translations[i]['sense_id'];
        var language = new_translations[i]['language'];
        var new_text = new_translations[i]['text'];
        var new_id = 'sense_translation_text_' + glossid + '_' + language + '_' + sense_id;
        var form_id = '#form_edit_sense_matrix_' + glossid;
        var new_translation = [];
        $(form_id).find('input[name="new_translation"]').each(function( index ) {
            if (index != inputEltIndex) { return; }
            if ($(this).attr('data-language') != language || $(this).attr('data-order_index') != orderIndex) { return; }
            $(this).attr('id', new_id);
            $(this).attr('data-translation', new_text);
            $(this).attr('value', new_text);
            // add temporary attribute in order to identify this input element
            $(this).attr('data-updated', new_text);
        });

        var modal_senses_glossid = '#tbody_modal_senses_' + glossid + '_' + language;
        var modalSensesCell = $(modal_senses_glossid);
        var senses_row = '#modal_senses_' + glossid +'_' + language +'_row_' + orderIndex;
        var span_id = 'sensegroup_' + glossid + '_' + orderIndex + '_' + language + '_' + sense_id;
        if (!$(senses_row).length) {
            // no senses for this language
            var senses_row_id = 'modal_senses_' + glossid +'_' + language +'_row_' + orderIndex;
            var cell_id = 'modal_senses_order_language_cell_' + glossid +'_' + language + '_' + orderIndex;
            var row = $('<tr id="'+ senses_row_id + '"/>');
            row.append("<td>"+orderIndex+'.</td>');
            cellTD = '<td id="'+ cell_id + '"/>';
            var span = $(cellTD + '<span id="'+span_id+'">'+new_text+"</span>");
            row.append(span).append("</td>");
            modalSensesCell.append(row).append("</tr>");
        } else {
            // add the new keyword to the end of the sense
            var cell = '#modal_senses_order_language_cell_' + glossid +'_' + language + '_' + orderIndex;
            var span = $('<span id="'+span_id+'">'+new_text+"</span>");
            $(cell).append(' ').append(span);
        }

        // add row to regroup panel of language modal
        var modal_senses_groups_glossid = '#tbody_senses_table_' + glossid + '_' + language;
        var modalSensesGroupsCell = $(modal_senses_groups_glossid);
        var keywords_update_row_id = 'keywords_regroup_row_' + glossid + '_' + language + '_' + sense_id;
        var row = $('<tr id="' + keywords_update_row_id + '"/>');
        row.append('<td id="keyword_sense_index_'+glossid+'_'+language+'_'+sense_id+'" >'+new_text);
        row.append('<input type="hidden" id="sense_id_'+sense_id+
                        '" name="group_index" value="'+sense_id+'" data-group_index="'+sense_id+'">');
        row.append("</td>");
        row.append('<td><input type="number" id="regroup_'+orderIndex+
                                '" name="regroup" size="5" value="'+orderIndex+
                                '" data-regroup="'+orderIndex+'" >');
        row.append("</td>");
        row.append("</tr>");
        modalSensesGroupsCell.append(row);
        modalSensesGroupsCell.append("</tr>");

        // add row to Update Text
        var modal_edit_keywords_glossid = '#edit_keywords_table_' + glossid + '_' + language;
        var modalEditKeywordsCell = $(modal_edit_keywords_glossid);
        var keywords_row = 'edit_keywords_row_' + glossid + '_' + language + '_' + sense_id;
        var row = $('<tr id="' + keywords_row + '"/>');
        row.append('<td><input type="text" id="edit_keyword_text_' + glossid + '_' + language + '_' + sense_id +
                                '" name="translation" size="40" value="'+new_text+
                                '" data-translation="'+new_text+'">');
        row.append('<input type="hidden" id="keyword_index_'+sense_id+
                        '" name="keyword_index" value="'+sense_id+'" data-index="'+sense_id+'">');
        row.append("</td>");
        row.append("</tr>");
        modalEditKeywordsCell.append(row);
    }
    var elementsUpdated = [];
    var form_id = '#form_edit_sense_matrix_' + glossid;
    $(form_id).find('input[name="new_translation"]').each(function() {
        if ($(this).attr('data-updated')) {
            elementsUpdated.push($(this));
        }
    });
    $.each(elementsUpdated, function(index, elt) {
        $(elt).attr('name', 'translation');
        $(elt).removeAttr("'data-updated'");
    });

    for (var i=0; i < updated_translations.length; i++) {
        var orderIndex = updated_translations[i]['orderIndex'];
        var sense_id = updated_translations[i]['sense_id'];
        var language = updated_translations[i]['language'];
        var new_text = updated_translations[i]['text'];
        // update field on senses matrix
        var input_text_element_id = '#sense_translation_text_' + glossid + '_' + language + '_' + sense_id;
        $(input_text_element_id).attr('value', new_text);
        $(input_text_element_id).attr('data-translation', new_text);
        // update field of language matrix
        var input_text_element_id = '#edit_keyword_text_' + glossid + '_' + language + '_' + sense_id;
        $(input_text_element_id).attr('value', new_text);
        $(input_text_element_id).attr('data-translation', new_text);
        // update sense index toggle in language modal
        var input_text_element_id = '#keyword_sense_index_' + glossid + '_' + language + '_' + sense_id;
        $(input_text_element_id).text(new_text);
        // update senses summary in language modal
        var span_id = '#sensegroup_' + glossid + '_' + orderIndex + '_' + language + '_' + sense_id;
        $(span_id).text(new_text);
    }

    for (var i=0; i < deleted_translations.length; i++) {
        var orderIndex = deleted_translations[i]['orderIndex'];
        var sense_id = deleted_translations[i]['sense_id'];
        var language = deleted_translations[i]['language'];
        var span_id = '#span_cell_' + glossid + '_' + language + '_' + sense_id;
        var spanTDParent = $(span_id).parent();
        var spanCell = $(span_id).remove();
        // replace with an empty cell
        var span = $('<span class="span-cell"/>');
        span.append('<input type="text" size="40" data-order_index="'+orderIndex + '" data-language="'+
                    language+'" name="new_translation">');
        span.append('<input type="hidden" name="new_order_index" value="'+orderIndex+'" data-new_order_index="'+orderIndex+'">');
        span.append('<input type="hidden" name="new_language" value="'+language+'" data-new_language="'+
                            language+'">');
        span.append("</span>");
        spanTDParent.append(span);
        // remove row of regroup table
        var keywords_regroup_row_id = '#keywords_regroup_row_' + glossid + '_' + language + '_' + sense_id;
        var keywordsRegroupRow = $(keywords_regroup_row_id).detach();
        // remove row of Update Text in language modal
        var keywords_update_row_id = '#edit_keywords_row_' + glossid + '_' + language + '_' + sense_id;
        var keywordsUpdateRow = $(keywords_update_row_id).detach();

        var keywords_language = senses_groups[language];
        var group_keywords = keywords_language[parseInt(orderIndex)];
        if (group_keywords === undefined) {
            // after deleting the keyword, the sense index has no keywords for this language
            group_keywords = [];
        }
        if (!group_keywords.length) {
            var group_row_id = '#modal_senses_' + glossid +'_' + language + '_row_' + orderIndex;
            var group_row = $(group_row_id).detach();
        } else {
            var group_cell = '#modal_senses_order_language_cell_' + glossid +'_' + language + '_' + orderIndex;
            var groupCell = $(group_cell);
            groupCell.empty();
            var num_commas = group_keywords.length - 1;
            for (var inx in group_keywords) {
                var span_id = 'sensegroup_' + glossid + '_' + key + '_' + language + '_' + group_keywords[inx][0];
                if (num_commas > 0 && inx < num_commas) {
                    groupCell.append('<span id="'+ span_id + '">'+group_keywords[inx][1]+"</span>, ");
                } else {
                    groupCell.append('<span id="'+ span_id + '">'+group_keywords[inx][1]+"</span>");
                }
            };
            groupCell.append("</td>");
        }
    }

    for (var language in keywords) {
        var keywords_glossid = '#tbody_keywords_' + glossid + '_' + language;
        var keywordsCell = $(keywords_glossid);
        $(keywordsCell).empty();
        var language_keywords = keywords[language];
        num_commas = language_keywords.length - 1;
        var row = $("<tr/>");
        row.append("<td/>");
        for (var inx in language_keywords) {
            if (num_commas > 0 && inx < num_commas) {
                row.append("<span>"+language_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+language_keywords[inx]+"</span>");
            }
        }
        row.append("</td></tr>");
        keywordsCell.append(row);
    }

    for (var language in senses_groups) {
        var senses_glossid = '#tbody_senses_' + glossid + '_' + language;
        var sensesCell = $(senses_glossid);
        $(sensesCell).empty();
        var language_senses = senses_groups[language];
        for (var key in language_senses) {
            var senses_row_id = 'senses_' + glossid  + '_' + language + '_row_' + key;
            var row = $('<tr id="'+ senses_row_id + '"/>');
            row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
            var group_keywords = language_senses[key];
            num_commas = group_keywords.length - 1;
            for (var inx in group_keywords) {
                if (num_commas > 0 && inx < num_commas) {
                    row.append("<span>"+group_keywords[inx][1]+"</span>, ");
                } else {
                    row.append("<span>"+group_keywords[inx][1]+"</span>");
                }
            };
            row.append("</td></tr>");
            sensesCell.append(row);
        }
    }
}

$(document).ready(function() {

    // setup required for Ajax POST
    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    $.ajaxSetup({
        crossDomain: false, // obviates need for sameOrigin test
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken", csrf_token);
            }
        }
    });

     $('.regroup_keywords').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         var language = $(this).attr("data-language");
         var form_id = '#form_regroup_keywords_' + glossid + '_' + language;
         var regroup = [];
         $(form_id).find('input[name="regroup"]').each(function() {
            regroup.push(this.value);
         });
         var group_index = [];
         $(form_id).find('input[name="group_index"]').each(function() {
            group_index.push(this.value);
         });
         $.ajax({
            url : url + "/dictionary/update/group_keywords/" + glossid,
            type: 'POST',
            data: { 'language': language,
                    'regroup': JSON.stringify(regroup),
                    'group_index': JSON.stringify(group_index),
                    'csrfmiddlewaretoken': csrf_token},
            datatype: "json",
            success : update_gloss_senses
         });
     });

     $('.edit_keywords').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         var language = $(this).attr("data-language");
         var form_id = '#form_edit_keywords_' + glossid + '_' + language;
         var keyword_index = [];
         $(form_id).find('input[name="keyword_index"]').each(function() {
            keyword_index.push(this.value);
         });
         var translation = [];
         $(form_id).find('input[name="translation"]').each(function() {
            translation.push(this.value);
         });
         $.ajax({
            url : url + "/dictionary/update/edit_keywords/" + glossid,
            type: 'POST',
            data: { 'language': language,
                    'keyword_index': JSON.stringify(keyword_index),
                    'translation': JSON.stringify(translation),
                    'csrfmiddlewaretoken': csrf_token},
            datatype: "json",
            success : update_gloss_senses
         });
     });

     $('.add_keyword').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         var form_id = '#add_keyword_form_' + glossid;
         var keywords = [];
         $(form_id).find('input[name="keyword"]').each(function() {
            keywords.push(this.value);
         });
         var language = [];
         $(form_id).find('input[name="language"]').each(function() {
            language.push(this.value);
         });
         $.ajax({
            url : url + "/dictionary/update/add_keyword/" + glossid,
            type: 'POST',
            data: { 'keywords': JSON.stringify(keywords),
                    'language': JSON.stringify(language),
                    'csrfmiddlewaretoken': csrf_token},
            datatype: "json",
            success : add_gloss_keywords
         });
     });

     $('.quick_tag').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         $.ajax({
            url : url + "/dictionary/update/toggle_sense_tag/" + glossid,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_sense_tag
         });
     });

     $('.update_translations').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         var form_id = '#form_edit_sense_matrix_' + glossid;
         var new_translation = [];
         $(form_id).find('input[name="new_translation"]').each(function() {
            new_translation.push(this.value);
         });
         var new_language = [];
         $(form_id).find('input[name="new_language"]').each(function() {
            new_language.push(this.value);
         });
         var new_order_index = [];
         $(form_id).find('input[name="new_order_index"]').each(function() {
            new_order_index.push(this.value);
         });
         var translation = [];
         $(form_id).find('input[name="translation"]').each(function() {
            translation.push(this.value);
         });
         var language = [];
         $(form_id).find('input[name="language"]').each(function() {
            language.push(this.value);
         });
         var sense_id = [];
         $(form_id).find('input[name="sense_id"]').each(function() {
            sense_id.push(this.value);
         });
         var order_index = [];
         $(form_id).find('input[name="order_index"]').each(function() {
            order_index.push(this.value);
         });
         $.ajax({
            url : url + "/dictionary/update/edit_senses_matrix/" + glossid,
            type: 'POST',
            data: { 'new_translation': JSON.stringify(new_translation),
                    'new_language': JSON.stringify(new_language),
                    'new_order_index': JSON.stringify(new_order_index),
                    'translation': JSON.stringify(translation),
                    'language': JSON.stringify(language),
                    'sense_id': JSON.stringify(sense_id),
                    'order_index': JSON.stringify(order_index),
                    'csrfmiddlewaretoken': csrf_token},
            datatype: "json",
            success : update_matrix
         });
     });
});
