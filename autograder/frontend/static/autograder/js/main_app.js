function load_view()
{
    console.log('load_view');
    // var pageName = getPageName();
    var current_path = window.location.pathname;
    // Offset the split and substring indices by one to ignore the leading
    // slash.
    var view_name = current_path.split('/')[1];
    var resource_url = current_path.substring(view_name.length + 1);

    $('#loading-bar').show();

    if (view_name === '')
    {
        load_landing_page();
    }
    else if (view_name === 'semester')
    {
        load_semester_view(resource_url);
    }
    else if (view_name === 'project')
    {
        load_and_display_project_view(resource_url);
    }
    else if (view_name === 'submission')
    {
        load_submission_view(resource_url);
    }
    else
    {
        history.replaceState(null, '', '/');
        load_landing_page();
    }
}

function load_landing_page()
{
    $.when(
        $.get('/courses/'), $.get('/semesters/')
    ).done(function(courses_result, semesters_result) {
        // console.log(courses_result[0]);
        // console.log(semesters_result[0]);
        var data = {
            'courses': courses_result[0],
            'semesters': semesters_result[0]
        };
        // console.log(data);
        render_and_fix_links('landing-page', data).done(function () {
            $('#loading-bar').hide();
        });
        // console.log($('#main-area'));
    });
}

function load_semester_view(semester_url)
{
    // console.log('load_semester_view');
    // console.log(semester_url);
    $.get(semester_url, function(data, status) {
        // console.log(status);
        render_and_fix_links('view-semester', data).done(function() {
            $('#loading-bar').hide();
        });
    });
}

function load_submission_view(submission_url)
{
    console.log('load_submission_view');
    $.get(submission_url).done(function(data, status) {
        // console.log(data);
        $.when(
            render_and_fix_links('view-submission', data)
        ).done(function() {
            $('#loading-bar').hide();
        });
    });
}

function render_and_fix_links(template_name, data, render_location, append)
{
    if (render_location === undefined)
    {
        render_location = $('#main-area');
    }

    if (append === undefined)
    {
        append = false;
    }

    var deferred = $.Deferred();
    $.when(lazy_get_template(template_name)).done(function() {
        var tmpl = $.templates[template_name];
        // console.log(tmpl);
        // console.log(tmpl.render(data));
        var rendered = tmpl.render(data);
        if (append)
        {
            render_location.append(rendered);
        }
        else
        {
            render_location.html(rendered);
        }

        // Adapted from: http://www.codemag.com/article/1301091
        // Date accessed: 2015-08-20
        $("a[data-role='ajax']").click(function (e) {
            e.preventDefault();
            var pageName = $(this).attr("href");
            window.history.pushState(null, "", pageName);
            load_view();
        });
        deferred.resolve();
    });
    return deferred.promise();
}

// Adapted from: http://www.jsviews.com/#samples/jsr/composition/remote-tmpl
function lazy_get_template(name)
{
    // If the named remote template is not yet loaded and compiled
    // as a named template, fetch it. In either case, return a promise
    // (already resolved, if the template has already been loaded)
    var deferred = $.Deferred();
    if ($.templates[name])
    {
        deferred.resolve();
    }
    else
    {
        var url = '/static/autograder/jsrender-templates/' + name + '.tmpl'
        $.get(url).done(function(data, status) {
            // console.log(data);
            $.templates(name, data);
            deferred.resolve();
        });
    }
    return deferred.promise();
}

// Adapted from: http://benjamin-schweizer.de/jquerypostjson.html
$.postJSON = function(url, data, callback) {
    return jQuery.ajax({
        'type': 'POST',
        'url': url,
        'contentType': 'application/json',
        'data': JSON.stringify(data),
        'dataType': 'json',
        'success': callback
    });
};
