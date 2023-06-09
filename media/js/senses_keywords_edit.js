// javascript for template admin_keyword_list.html
// this code uses json ajax calls

function update_gloss_senses(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var language = data.language;
    var keywords = data.keywords;
    var senses_groups = data.senses_groups;
    if ($.isEmptyObject(senses_groups)) {
        return;
    };
    var keywords_glossid = '#tbody_keywords_' + glossid + '_' + language;
    var modal_keywords_glossid = '#tbody_modal_keywords_' + glossid + '_' + language;
    var keywordsCell = $(keywords_glossid);
    var modalKeywordsCell = $(modal_keywords_glossid);
    $(keywordsCell).empty();
    $(modalKeywordsCell).empty();
    var row = $("<tr/>");
    var num_commas = keywords.length - 1;
    for (var key in keywords) {
        if (key < num_commas) {
            row.append("<span>"+keywords[key]+"</span>, ");
        } else {
            row.append("<span>"+keywords[key]+"</span>");
        }
    }
    row.append("</td>");
    keywordsCell.append(row);

    for (var key in senses_groups) {
        var row = $("<tr/>");
        row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        modalKeywordsCell.append(row);
    }
    modalKeywordsCell.append("</tr>");

    var senses_glossid = '#tbody_senses_' + glossid + '_' + language;
    var sensesCell = $(senses_glossid);
    $(sensesCell).empty();
    for (var key in senses_groups) {
        var row = $("<tr/>");
                row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        sensesCell.append(row);
    }
    sensesCell.append("</tr>");

    var modal_senses_glossid = '#tbody_modal_senses_' + glossid + '_' + language;
    var modalSensesCell = $(modal_senses_glossid);
    $(modalSensesCell).empty();
    for (var key in senses_groups) {
        var row = $("<tr/>");
        row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        modalSensesCell.append(row);
    }
    modalSensesCell.append("</tr>");

    var modal_senses_groups_glossid = '#tbody_senses_table_' + glossid + '_' + language;
    var modalSensesGroupsCell = $(modal_senses_groups_glossid);
    $(modalSensesGroupsCell).empty();
    var last_index = keywords.length - 1;
    var max_index = keywords.length;
    for (var key in senses_groups) {
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            var sense_keyword = group_keywords[inx];

            var keywordCellId = '#keyword_sense_index_'+glossid+'_'+language+'_'+sense_keyword[0];

            var row = $("<tr/>");
            // the new row gets as id the max index of the keywords
            row.append('<td id="keyword_sense_index_'+glossid+'_'+language+'_'+sense_keyword[0]+'" >'+sense_keyword[1]+'</td>');
            row.append('<input type="hidden" id="sense_id_'+sense_keyword[0]+
                            '" name="group_index" value="'+sense_keyword[0]+'" data-group_index="'+sense_keyword[0]+'">');
            row.append("<td>");
            row.append('<input type="number" id="regroup_'+key+
                                    '" name="regroup" value="'+key+
                                    '" data-regroup="'+key+'" >');
            row.append("</td>");
            row.append("</tr>");
            modalSensesGroupsCell.append(row);
        }
    }
    modalSensesGroupsCell.append("</tr>");
}

// the following function expects more fields from the ajax call json data
// it adds new rows to tables
function add_gloss_keywords(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var language = data.language;
    var keywords = data.keywords;
    var senses_groups = data.senses_groups;
    if ($.isEmptyObject(senses_groups)) {
        return;
    };
    var new_translation = data.new_translation;
    if ($.isEmptyObject(new_translation)) {
        return;
    };
    var new_sense = data.new_sense;
    if ($.isEmptyObject(new_sense)) {
        return;
    };
    var keywords_glossid = '#tbody_keywords_' + glossid + '_' + language;
    var modal_keywords_glossid = '#tbody_modal_keywords_' + glossid + '_' + language;
    var keywordsCell = $(keywords_glossid);
    var modalKeywordsCell = $(modal_keywords_glossid);
    $(keywordsCell).empty();
    $(modalKeywordsCell).empty();
    var row = $("<tr/>");
    var num_commas = keywords.length - 1;
    for (var key in keywords) {
        if (key < num_commas) {
            row.append("<span>"+keywords[key]+"</span>, ");
        } else {
            row.append("<span>"+keywords[key]+"</span>");
        }
    }
    row.append("</td>");
    keywordsCell.append(row);
    for (var key in senses_groups) {
        var row = $("<tr/>");
        row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        modalKeywordsCell.append(row);
    }
    modalKeywordsCell.append("</tr>");

    var senses_glossid = '#tbody_senses_' + glossid + '_' + language;
    var sensesCell = $(senses_glossid);
    $(sensesCell).empty();
    for (var key in senses_groups) {
        var row = $("<tr/>");
                row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        sensesCell.append(row);
    }
    sensesCell.append("</tr>");

    var modal_senses_glossid = '#tbody_modal_senses_' + glossid + '_' + language;
    var modalSensesCell = $(modal_senses_glossid);
    $(modalSensesCell).empty();
    for (var key in senses_groups) {
        var row = $("<tr/>");
        row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx][1]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx][1]+"</span>");
            }
        };
        row.append("</td>");
        modalSensesCell.append(row);
    }
    modalSensesCell.append("</tr>");
    var modal_senses_groups_glossid = '#tbody_senses_table_' + glossid + '_' + language;
    var modalSensesGroupsCell = $(modal_senses_groups_glossid);
    var last_index = keywords.length - 1;
    var max_index = keywords.length;
    var row = $("<tr/>");
    // the new row gets as id the max index of the keywords
    row.append('<td id="keyword_sense_index_'+glossid+'_'+language+'_'+max_index+'" >'+keywords[last_index]+'</td>');
    row.append('<input type="hidden" id="sense_id_'+new_translation+
                    '" name="group_index" value="'+new_translation+'" data-group_index="'+new_translation+'">');
    row.append("<td>");
    row.append('<input type="number" id="regroup_'+new_sense+
                            '" name="regroup" value="'+new_sense+
                            '" data-regroup="'+new_sense+'" >');
    row.append("</td>");
    row.append("</tr>");
    modalSensesGroupsCell.append(row);
    modalSensesGroupsCell.append("</tr>");

    var modal_edit_keywords_glossid = '#edit_keywords_table_' + glossid + '_' + language;
    var modalEditKeywordsCell = $(modal_edit_keywords_glossid);
    var last_index = keywords.length - 1;

    var row = $("<tr/>");
    row.append('<td>'+keywords[last_index]+'</td>');
    row.append('<input type="hidden" id="keyword_index_'+new_translation+
                    '" name="keyword_index" value="'+new_translation+'" data-index="'+new_translation+'">');
    row.append("<td>");
    row.append('<input type="text" id="edit_keyword_text_'+new_translation+
                            '" name="translation" value="'+keywords[last_index]+
                            '" data-translation="'+new_translation+'">');
    row.append("</td>");
    row.append("</tr>");
    modalEditKeywordsCell.append(row);
    modalEditKeywordsCell.append("</tr>");
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
         var language = $(this).attr("data-language");
         var form_id = '#add_keyword_form_' + glossid + '_' + language;
         var keywords = [];
         $(form_id).find('input[name="keyword"]').each(function() {
            keywords.push(this.value);
         });
         $.ajax({
            url : url + "/dictionary/update/add_keyword/" + glossid,
            type: 'POST',
            data: { 'language': language,
                    'keywords': JSON.stringify(keywords),
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
});
