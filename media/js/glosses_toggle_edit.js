// javascript for template admin_toggle_view.html
// this code uses json ajax calls

function toggle_tags(data) {
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

function toggle_semantic_fields(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var sf_list = data.semantic_fields_list;
    var sfCell = $("#semantics_cell_"+glossid);
    $(sfCell).empty();
    var cell = "";
    var num_spaces = sf_list.length - 1;
    for (var key in sf_list) {
        if (key < num_spaces) {
            cell = cell + "<span class='semanticfield'>"+sf_list[key]+"</span>, ";
        } else {
            cell = cell + "<span class='semanticfield'>"+sf_list[key]+"</span>";
        }
    }
    sfCell.html(cell);
}

function toggle_wordclass(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var wordclass = data.wordclass;
    var wcCell = $("#wordclass_cell_"+glossid);
    $(wcCell).empty();
    var cell = "<span class='wordclass'>"+wordclass+"</span>";
    wcCell.html(cell);
}

function toggle_namedentity(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var namedentity = data.namedentity;
    var neCell = $("#namedentity_cell_"+glossid);
    $(neCell).empty();
    var cell = "<span class='namedentity'>"+namedentity+"</span>";
    neCell.html(cell);
}

function toggle_handedness(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var handedness = data.handedness;
    var hCell = $("#handedness_cell_"+glossid);
    $(hCell).empty();
    var cell = "<span class='handedness'>"+handedness+"</span>";
    hCell.html(cell);

    var button_lookup = '#button_' + glossid + '_handedness';
    var buttonCell = $(button_lookup);
    var button_contents = similar_gloss_fields_labels['handedness'] + ': ' + handedness;
    buttonCell.attr('value', button_contents);
}

function toggle_domhndsh(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var domhndsh = data.domhndsh;
    var hCell = $("#domhndsh_cell_"+glossid);
    $(hCell).empty();
    var cell = "<span class='domhndsh'>"+domhndsh+"</span>";
    hCell.html(cell);

    var button_lookup = '#button_' + glossid + '_domhndsh';
    var buttonCell = $(button_lookup);
    var button_contents = similar_gloss_fields_labels['domhndsh'] + ': ' + domhndsh;
    buttonCell.attr('value', button_contents);
}

function toggle_subhndsh(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var subhndsh = data.subhndsh;
    var hCell = $("#subhndsh_cell_"+glossid);
    $(hCell).empty();
    var cell = "<span class='subhndsh'>"+subhndsh+"</span>";
    hCell.html(cell);

    var button_lookup = '#button_' + glossid + '_subhndsh';
    var buttonCell = $(button_lookup);
    var button_contents = similar_gloss_fields_labels['subhndsh'] + ': ' + subhndsh;
    buttonCell.attr('value', button_contents);
}

function toggle_locprim(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var locprim = data.locprim;
    var hCell = $("#locprim_cell_"+glossid);
    $(hCell).empty();
    var cell = "<span class='locprim'>"+locprim+"</span>";
    hCell.html(cell);

    var button_lookup = '#button_' + glossid + '_locprim';
    var buttonCell = $(button_lookup);
    var button_contents = similar_gloss_fields_labels['locprim'] + ': ' + locprim;
    buttonCell.attr('value', button_contents);
}

function toggle_movSh(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var movSh = data.movSh;
    var hCell = $("#movSh_cell_"+glossid);
    $(hCell).empty();
    var cell = "<span class='movSh'>"+movSh+"</span>";
    hCell.html(cell);

    var button_lookup = '#button_' + glossid + '_movSh';
    var buttonCell = $(button_lookup);
    var button_contents = similar_gloss_fields_labels['movSh'] + ': ' + movSh;
    buttonCell.attr('value', button_contents);
}

function toggle_repeat(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var repeat = data.repeat;
    var hCell = $("#repeat_cell_"+glossid);
    $(hCell).empty();
    var cell = "<span class='repeat'>"+repeat+"</span>";
    hCell.html(cell);

    var button_lookup = '#button_' + glossid + '_repeat';
    var buttonCell = $(button_lookup);
    var button_contents = similar_gloss_fields_labels['repeat'] + ': ' + repeat;
    buttonCell.attr('value', button_contents);
}

function toggle_altern(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var altern = data.altern;
    var hCell = $("#altern_cell_"+glossid);
    $(hCell).empty();
    var cell = "<span class='altern'>"+altern+"</span>";
    hCell.html(cell);

    var button_lookup = '#button_' + glossid + '_altern';
    var buttonCell = $(button_lookup);
    var button_contents = similar_gloss_fields_labels['altern'] + ': ' + altern;
    buttonCell.attr('value', button_contents);
}

function toggle_create_sense(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var order = data.order;
    var languages_fields_table = $("#gloss_language_fields_"+glossid);
    var row = $('<tr style="height:52px;"/>');
    for (var i=0; i < language_2chars.length; i++) {
        var lang2char = language_2chars[i];
        var cellID = 'edit_gloss_sense_value_' + glossid + '_' + order + '_' + lang2char;
        var cellTD = $('<td id="' + cellID + '"/>');
        var spanCell = '<span>' + order + '.</span>';
        cellTD.append(spanCell);
        var textareaID = 'sense_' + glossid + '_' + order + '_' + lang2char;
        var textareaName = 'sense_' + glossid + '_' + lang2char;
        var textareaCell = '<textarea id="' + textareaID + '" name = "' + textareaName + '" maxlength="30" ' +
                           '"type="textarea" data-order="' + order + '" cols="45" rows="1"></textarea>';
        cellTD.append(textareaCell);
        cellTD.append('</td>');
        row.append(cellTD);
    }
    row.append("</tr>");
    languages_fields_table.append(row);
}

function toggle_language_fields(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var default_annotation = data.default_annotation;
    var errors = data.errors;
    var updatestatus = data.updatestatus;
    if (errors) {
        var errors_lookup = '#errors_' + glossid;
        var errorsElt = $(errors_lookup);
        var glossCell = "<ul>";
        for (var err in errors) {
            glossCell = glossCell + "<li>"+errors[err]+"</li>";
        }
        glossCell = glossCell + "</ul>";
        errorsElt.html(glossCell);
    }
    var default_annotation_lookup = '#gloss_default_annotation_link_' + glossid;
    var annotationElt = $(default_annotation_lookup);
    var annotationCell = '<a href="'+url+'/dictionary/gloss/'+glossid+'/">'+default_annotation+'</a>';
    annotationElt.html(annotationCell);

    var status_lookup = '#status_' + glossid;
    var statusElt = $(status_lookup);
    var statusCell = "<span>"+updatestatus+"</span>";
    statusElt.html(statusCell);
}

function show_similar_glosses(data) {
    if ($.isEmptyObject(data)) {
        return;
    };
    var glossid = data.glossid;
    var number_of_matches = data.number_of_matches;
    var similar_glosses = data.similar_glosses;

    var number_of_matches_lookup = '#number_of_matches_' + glossid;
    var number_of_matchesElt = $(number_of_matches_lookup);
    var number_of_matchesCell = "<span>"+number_of_matches_found+' '+number_of_matches+"</span>";
    number_of_matchesElt.html(number_of_matchesCell);

    if (similar_glosses) {
        var similar_glosses_lookup = '#similar_gloss_videos_' + glossid;
        var similar_glossesElt = $(similar_glosses_lookup);
        for (var inx in similar_glosses) {
            var similar = similar_glosses[inx];
            var annotation = similar['annotation_idgloss'];
            var imagelink = similar['imagelink'];
            var videolink = similar['videolink'];
            var pk = similar['pk'];
            var annotationCell = '<span><a href="'+url+'/dictionary/gloss/'+pk+'/">'+annotation+'</a></span>';
            var annotationElt = $(annotationCell);
            if (videolink) {
                var video_container_html = "<div class='thumbnail_container'/>";
                video_container = $(video_container_html);
                video_container.append(annotationElt);
                var video_elt_html = "<div id='glossvideo_"+glossid+'_'+pk+"'>";
                video_elt_html += "<video id='videoplayer' class='thumbnail-video' src='"
                                +videolink+"' type='video/mp4' controls muted autoplay></video>";
                video_elt_html += "</div>";
                var video_elt = $(video_elt_html);
                video_container.append(video_elt);
                video_container.append("</div>");
                similar_glossesElt.append(video_container);
            } else {
                var video_container_html = "<div class='thumbnail_container'/>";
                video_container = $(video_container_html);
                video_container.append(annotationElt);
                var video_elt_html = "<div id='glossvideo_"+glossid+'_'+pk+"'>";
                video_elt_html += "<img class='thumbnail' src='"+imagelink+"'>";
                video_elt_html += "</div>";
                var video_elt = $(video_elt_html);
                video_container.append(video_elt);
                video_container.append("</div>");
                similar_glossesElt.append(video_container);
            }
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

     $('.quick_tag').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var tagname = $(this).attr("data-tagname");
         $.ajax({
            url : url + "/dictionary/update/toggle_tag/" + glossid + "/" + tagname,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_tags
         });
     });

     $('.quick_semantics').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var semanticfield = $(this).attr("data-semanticfield");
         $.ajax({
            url : url + "/dictionary/update/toggle_semantics/" + glossid + "/" + semanticfield,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_semantic_fields
         });
     });

     $('.quick_wordclass').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var wordclass = $(this).attr("data-wordclass");
         $.ajax({
            url : url + "/dictionary/update/toggle_wordclass/" + glossid + "/" + wordclass,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_wordclass
         });
     });

     $('.quick_namedentity').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var namedentity = $(this).attr("data-namedentity");
         $.ajax({
            url : url + "/dictionary/update/toggle_namedentity/" + glossid + "/" + namedentity,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_namedentity
         });
     });
     $('.quick_handedness').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var handedness = $(this).attr("data-handedness");
         $.ajax({
            url : url + "/dictionary/update/toggle_handedness/" + glossid + "/" + handedness,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_handedness
         });
     });
     $('.quick_domhndsh').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var domhndsh = $(this).attr("data-domhndsh");
         $.ajax({
            url : url + "/dictionary/update/toggle_domhndsh/" + glossid + "/" + domhndsh,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_domhndsh
         });
     });
     $('.quick_subhndsh').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var subhndsh = $(this).attr("data-subhndsh");
         $.ajax({
            url : url + "/dictionary/update/toggle_subhndsh/" + glossid + "/" + subhndsh,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_subhndsh
         });
     });
     $('.quick_locprim').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var locprim = $(this).attr("data-locprim");
         $.ajax({
            url : url + "/dictionary/update/toggle_locprim/" + glossid + "/" + locprim,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_locprim
         });
     });

     $('.quick_movSh').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var movSh = $(this).attr("data-movSh");
         $.ajax({
            url : url + "/dictionary/update/toggle_movSh/" + glossid + "/" + movSh,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_movSh
         });
     });

     $('.quick_repeat').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var repeat = $(this).attr("data-repeat");
         $.ajax({
            url : url + "/dictionary/update/toggle_repeat/" + glossid + "/" + repeat,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_repeat
         });
     });

     $('.quick_altern').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
	     var altern = $(this).attr("data-altern");
         $.ajax({
            url : url + "/dictionary/update/toggle_altern/" + glossid + "/" + altern,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_altern
         });
     });

     $('.quick_create_sense').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         $.ajax({
            url : url + "/dictionary/update/quick_create_sense/" + glossid,
            type: 'POST',
            data: { 'csrfmiddlewaretoken': csrf_token },
            datatype: "json",
            success : toggle_create_sense
         });
     });

     $('.quick_language_fields').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('value');
         var errors_lookup = '#errors_' + glossid;
         $(errors_lookup).empty()
	     var update = { 'csrfmiddlewaretoken': csrf_token };
         for (var i=0; i < language_2chars.length; i++) {
            var lang2char = language_2chars[i];
            var lemma_field_key = 'lemma_' + glossid + '_'+ lang2char;
            var lemma_field_lookup = '#'+lemma_field_key;
            var lemma_field_value = $(lemma_field_lookup).val();
            if (lemma_field_value != '') {
                update[lemma_field_key] = lemma_field_value;
            }
            var annotation_field_key = 'annotation_' + glossid + '_'+ lang2char;
            var annotation_field_lookup = '#'+annotation_field_key;
            var annotation_field_value = $(annotation_field_lookup).val();
            if (annotation_field_value != '') {
                update[annotation_field_key] = annotation_field_value;
            }
            var table_id = '#gloss_language_fields_' + glossid;
            var sense_field_name = 'sense_' + glossid + '_'+ lang2char;
            $(table_id).find('textarea[name="'+sense_field_name+'"]').each(function() {
               var this_order = $(this).attr('data-order');
               var sense_field_key = 'sense_' + glossid + '_' + this_order + '_'+ lang2char;
               var sense_field_value = $(this).val();
               update[sense_field_key] = sense_field_value;
            });
         }
         $.ajax({
            url : url + "/dictionary/update/toggle_language_fields/" + glossid,
            type: 'POST',
            data: update,
            datatype: "json",
            success : toggle_language_fields
         });
     });
     $('.quick_similarglosses').click(function(e)
	 {
         e.preventDefault();
	     var glossid = $(this).attr('data-glossid');
         var similar_glosses_lookup = '#similar_gloss_videos_' + glossid;
         var similar_glossesElt = $(similar_glosses_lookup);
         similar_glossesElt.empty();
	     var query = { 'csrfmiddlewaretoken': csrf_token };
         for (var i=0; i < similar_gloss_fields.length; i++) {
            var fieldname = similar_gloss_fields[i];
            var similar_field_key = 'button_' + glossid + '_'+ fieldname;
            var similar_field_lookup = '#'+similar_field_key;
            var similar_field_value = $(similar_field_lookup).attr('data-value');
            if ($(similar_field_lookup).hasClass('similar')) {
                query[similar_field_value] = similar_field_value;
            }
         }
         $.ajax({
            url : url + "/dictionary/ajax/similarglosses/" + glossid,
            type: 'POST',
            data: query,
            datatype: "json",
            success : show_similar_glosses
         });
     });
});
