function load_semester_view(semester_url)
{
    console.log('load_semester_view');

    var loaded = $.Deferred();

    $.when(
        $.get(semester_url), lazy_get_template('view-semester')
    ).done(function(semester_ajax, template) {
        _render_semester_view(semester_ajax[0], template);
        loaded.resolve();
    });

    return loaded.promise();
}

function _render_semester_view(semester, template)
{
    var rendered = template.render(semester);

    $('#main-area').html(rendered);
    $("a[data-role='ajax']").click(ajax_link_click_handler);
}
