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
    var videofile = data.videofile;
    var uploadstatus = data.uploadstatus;
    var videolink = data.videolink;
    var errors = data.errors;
    var lookup = '#importstatus_' + glossid;
    $(lookup).html(uploadstatus);
    var import_table = $('#imported_videos');
    var row = $("<tr/>");
    row.append("<td>"+glossid+"</td>");
    row.append("<td>"+videolink+"</td>");
    row.append("</tr>");
    $(import_table).append(row);
}

async function import_videos() {
    var import_table_header = $('#imported_videos_header');
    var row = $("<tr/>");
    row.append("<th style='width:300px;'>"+gloss_column_header+"</th>");
    row.append("<th style='width:600px;'>"+video_column_header+"</th>");
    row.append("</tr>");
    $(import_table_header).append(row);
    $('.video_path').each(function() {
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
