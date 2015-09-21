function get_landing_page_widget()
{
    console.log('get_landing_page_widget');

    var loaded = $.Deferred();

    $.when(
        $.get('/courses/'), $.get('/semesters/'),
        lazy_get_template('landing-page')
    ).done(function(courses_ajax, semesters_ajax, template) {
        var widget = _render_landing_page_template(
            courses_ajax[0], semesters_ajax[0], template);
        loaded.resolve();
    }).fail(function() {
        console.log("Error loading landing page");
        loaded.reject('Error loading landing page.')
    });
    return loaded.promise();
}

function _render_landing_page_template(courses, semesters, template)
{
    var data = {
        'courses': courses,
        'semesters': semesters
    };

    $('#main-area').html(template.render(data));
    $("a[data-role='ajax']").click(ajax_link_click_handler);
}
