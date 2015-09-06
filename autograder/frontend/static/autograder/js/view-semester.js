function get_semester_widget(semester_url)
{
    console.log('load_semester_view');

    var loaded = $.Deferred();

    $.when(
        $.get(semester_url), lazy_get_template('view-semester')
    ).done(function(semester_ajax, template) {
        var widget = _render_semester_view(semester_ajax[0], template);
        loaded.resolve(widget);
    });

    return loaded.promise();
}

function _render_semester_view(semester, template)
{
    var rendered = $.parseHTML(template.render(semester));

    $("a[data-role='ajax']", rendered).click(ajax_link_click_handler);
    return rendered;
}
