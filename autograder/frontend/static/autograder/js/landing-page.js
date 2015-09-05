function load_landing_page()
{
    console.log('load_landing_page');

    var loaded = $.Deferred();

    $.when(
        $.get('/courses/'), $.get('/semesters/'),
        lazy_get_template('landing-page')
    ).done(function(courses_ajax, semesters_ajax, template) {
        _render_landing_page(courses_ajax[0], semesters_ajax[0], template);
        loaded.resolve();
    });
    return loaded.promise();
}

function _render_landing_page(courses, semesters, template)
{
    var data = {
        'courses': courses,
        'semesters': semesters
    };

    var rendered = template.render(data);

    $('#main-area').html(rendered);
    $("a[data-role='ajax']").click(ajax_link_click_handler);
}
