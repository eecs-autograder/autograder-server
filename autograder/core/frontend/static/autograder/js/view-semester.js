function get_semester_widget(semester_url)
{
    console.log('load_semester_view');

    var loaded = $.Deferred();

    $.when(
        $.get(semester_url), lazy_get_template('view-semester')
    ).done(function(semester_ajax, template) {
        var widget = _render_semester_view(semester_ajax[0], template);
        loaded.resolve();
    }).fail(function(data, status) {
        console.log('Error loading semester:');
        console.log(data);
        loaded.reject("Error loading semester", data.statusText);
    });

    return loaded.promise();
}

function _render_semester_view(semester, template)
{
    $('#main-area').html(template.render(semester));
    $("a[data-role='ajax']").click(ajax_link_click_handler);
}
