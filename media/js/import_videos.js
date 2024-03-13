// javascript for template dataset_media_manager.html
// this code uses json ajax calls

function update_video_file_display(data) {
    // this success function is called for a specific language
    // it updates all relevant html for the specific gloss
    if ($.isEmptyObject(data)) {
        return;
    };
    var videopath = data.videopath;
    var glossid = data.gloss;
    var annotation = data.annotation;
    var videofile = data.videofile;
    var imagelink = data.imagelink;
    var uploadstatus = data.uploadstatus;
    var videolink = data.videolink;
    var errors = data.errors;
    if (!glossid) {
        return;
    }
    if (!videolink) {
        return;
    }
    if (!imagelink) {
        return;
    }
    var lookup = '#importstatus_' + glossid;
    $(lookup).attr('data-imported', "True");
    $(lookup).html(uploadstatus);
    var import_table = $('#imported_videos');
    var row = $("<tr/>");
    row.append("<td><a href='"+gloss_dictionary_url+glossid+"'>"+annotation+"</a></td>");
    var column_elt = $("<td/>");
    var video_container_html = "<div class='thumbnail_container'>";
    video_container = $(video_container_html);
    var video_elt_html = "<div id='glossvideo_"+glossid+"'>";
    video_elt_html += "<img class='thumbnail' src='"+imagelink+"'>";
    video_elt_html += "<video id='videoplayer' class='thumbnail-video hover-shows-video' src='"
                    +videolink+"' type='video/mp4' muted='muted'></video>";
    video_elt_html += "</div>";
    var video_elt = $(video_elt_html);
    video_container.append(video_elt);
    video_container.append("</div>");
    column_elt.append(video_container);
    column_elt.append("</td>");
    row.append(column_elt);
    row.append("</tr>");
    $(import_table).append(row);
    ready_videos(video_elt);
}

function import_videos() {
    var import_table_header = $('#imported_videos_header');
    if (!import_table_header.html()) {
        var row = $("<tr/>");
        row.append("<th style='width:300px;'>"+gloss_column_header+"</th>");
        row.append("<th style='width:600px;'>"+video_column_header+"</th>");
        row.append("</tr>");
        $(import_table_header).append(row);
    }
    var count_imported = 10;
    $('.video_path').each(function() {
        var already_imported = $(this).attr('data-imported');
        if (already_imported == "True") {
            return;
        }
        if (!count_imported) {
            return;
        }
        count_imported = count_imported - 1;
        var videofile = $(this).attr('data-path');
        $.ajax({
            url : url + "/dictionary/import_video_to_gloss_json/",
            datatype: "json",
            async: false,
            type: 'POST',
            timeout: 30000,
            data: { 'videofile': videofile,
                    'dataset': datasetid,
                    'csrfmiddlewaretoken': csrf_token },
            success : update_video_file_display
        });
    });
};
