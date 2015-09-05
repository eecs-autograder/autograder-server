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

    var loaded = null;

    if (view_name === '')
    {
        loaded = load_landing_page();
    }
    else if (view_name === 'semester')
    {
        loaded = load_semester_view(resource_url);
    }
    else if (view_name === 'project')
    {
        loaded = load_and_display_project_view(resource_url);
    }
    else if (view_name === 'submission')
    {
        loaded = load_submission_view(resource_url);
    }
    else
    {
        history.replaceState(null, '', '/');
        loaded = load_landing_page();
    }

    loaded.done(function() { $('#loading-bar').hide(); });
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
        $("a[data-role='ajax']").click(ajax_link_click_handler);
        deferred.resolve();
    });
    return deferred.promise();
}
