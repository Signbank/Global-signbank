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
});
