function get_semester_widget(semester_url)
{
    console.log('load_semester_view');

    var loaded = $.Deferred();
    var semester_json_ = null;

    $.when(
        $.get(semester_url)
    ).then(function(semester_json) {
        semester_json_ = semester_json;
        return $.when(
            $.get(semester_json.urls.projects),
            lazy_get_template('view-semester')
        );
    }).done(function(projects_ajax, template) {
        var widget = _render_semester_view(
            semester_json_, projects_ajax[0], template);
        loaded.resolve();
    }).fail(function(data, status) {
        console.log('Error loading semester:');
        console.log(data);
        loaded.reject("Error loading semester", data.statusText);
    });

    return loaded.promise();
}

function _render_semester_view(semester, projects, template)
{
    projects.semester = semester;
    $('#main-area').html(template.render(projects));
    $("a[data-role='ajax']").click(ajax_link_click_handler);
}
