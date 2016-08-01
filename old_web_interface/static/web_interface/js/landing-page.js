function get_landing_page_widget()
{
    console.log('get_landing_page_widget');

    var loaded = $.Deferred();

    $.get(
        '/user/'
    ).then(function(user_json) {
        console.log(user_json);        
        return $.when(
            $.get(user_json.urls.courses_is_admin_for),
            $.get(user_json.urls.semesters_is_staff_for),
            $.get(user_json.urls.semesters_is_enrolled_in),
            lazy_get_template('landing-page'));
    }).then(function(courses_ajax, enrolled_ajax, staff_ajax, template) {
        var widget = _render_landing_page_template(
            courses_ajax[0], enrolled_ajax[0], staff_ajax[0], template);
        loaded.resolve();
    }).fail(function() {
        console.log("Error loading landing page");
        loaded.reject('Error loading landing page.')
    });
    return loaded.promise();
}

function _render_landing_page_template(
    courses, staff_semesters, enrolled_semesters, template)
{
    console.log(courses);
    console.log(staff_semesters);
    var data = {
        'courses': courses,
        'staff_semesters': staff_semesters,
        'enrolled_semesters': enrolled_semesters,
    };

    $('#main-area').html(template.render(data));
    $("a[data-role='ajax']").click(ajax_link_click_handler);
}
