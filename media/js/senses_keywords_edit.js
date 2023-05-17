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
    var senses_glossid = '#tbody_senses_' + glossid + '_' + language;
    var modal_senses_glossid = '#tbody_modal_senses_' + glossid + '_' + language;
    var sensesCell = $(senses_glossid);
    var modalSensesCell = $(modal_senses_glossid);
    $(sensesCell).empty();
    $(modalSensesCell).empty();
    for (var key in senses_groups) {
        var row = $("<tr/>");
        row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        var num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx]+"</span>");
            }
        };
        row.append("</td>");
        modalSensesCell.append(row);
    }
    modalSensesCell.append("</tr>");
    for (var key in senses_groups) {
        var row = $("<tr/>");
                row.append("<td>"+key+".</td><td>&nbsp;&nbsp;</td><td/>");
        var group_keywords = senses_groups[key];
        num_commas = group_keywords.length - 1;
        for (var inx in group_keywords) {
            if (inx < num_commas) {
                row.append("<span>"+group_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx]+"</span>");
            }
        };
        row.append("</td>");
        sensesCell.append(row);
    }
    sensesCell.append("</tr>");
}

function update_gloss_keywords(data) {
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
                row.append("<span>"+group_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx]+"</span>");
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
                row.append("<span>"+group_keywords[inx]+"</span>, ");
            } else {
                row.append("<span>"+group_keywords[inx]+"</span>");
            }
        };
        row.append("</td>");
        sensesCell.append(row);
    }
    sensesCell.append("</tr>");
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
            success : update_gloss_keywords
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
         var keyword = keywords.pop();
         $.ajax({
            url : url + "/dictionary/update/add_keyword/" + glossid,
            type: 'POST',
            data: { 'language': language,
                    'keyword': JSON.stringify(keyword),
                    'csrfmiddlewaretoken': csrf_token},
            datatype: "json",
            success : update_gloss_keywords
         });
     });
});
