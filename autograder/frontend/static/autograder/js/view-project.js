function load_and_display_project_view(project_url)
{
    console.log('load_project_view');
    // console.log(project_url);
    var project_loaded = $.get(project_url).promise();
    $.get(project_url).done(function(project_data) {
        $.when(get_or_register_group(project_data)).done(
            function(group_data, project_data) {
                show_project(group_data, project_data);
        });
    });
    // var group_loaded = project_loaded.done(get_or_register_group).promise();
    // group_loaded.done(show_project);
}

function get_or_register_group(project_data)
{
    console.log('get_or_register_group');
    var deferred = $.Deferred();
    var url = get_submission_group_url(
        project_data.data.id, project_data.meta.username);
    console.log(url);
    $.ajax(url,
    {
        statusCode: {
            404: function() {
                var group_registered = register_group(project_data);
                group_registered.done(function(group_data, project_data) {
                    console.log('resolving');
                    deferred.resolve(group_data, project_data);
                });
            }
        }
    }).done(function(group_data, status) {
        console.log('resolving');
        deferred.resolve(group_data, project_data);
    });
    return deferred.promise();
}

function register_group(project_data)
{
    console.log('register_group');
    if (project_data.data.attributes.max_group_size === 1)
    {
        var group_registered = $.Deferred();
        submit_group_request(
            [project_data.meta.username], project_data, group_registered);
        return group_registered.promise();
    }
    var group_registered = process_group_registration(project_data);
    return group_registered;
}

function show_project(group_data, project_data)
{
    console.log('show_project');
    // console.log(group_data);
    // console.log(project_data);
    var project_render_data = {
        'project': project_data,
        'group': group_data
    };
    $.when(
        render_and_fix_links('view-project', project_render_data)
    ).done(function() {
        console.log('project rendered');
        console.log($('#fileupload'));
        $('#fileupload').fileupload({
            'url': "/submissions/submission/",
            'singleFileUploads': false,
            'done': function(event, response) {
                on_submit_success(event, response, group_data.data.id);
            }
        });
        // console.log(group_data);
        render_and_fix_links(
            'submission-list', group_data, $('#own-submissions')
        ).done(function() { setup_collapsibles($('.collapse')) });
        $('#load-student-submissions-button').click(function(event){
            event.preventDefault();
            $('#student-submission-view .error').remove();
            var email = $('#requested-email').val();
            if (!is_umich_email(email))
            {
                $('#requested-email').after(
                    '<span class="error">Please enter a valid umich.edu email address</span>');
                return;
            }
            var url = get_submission_group_url(
                project_data.data.id, email);
            $.get(
                url
            ).done(function (data, status) {
                $.when(render_and_fix_links('submission-list', data, $('#student-submissions'))).done(
                    setup_collapsibles($('#student-submissions .collapse'))
                );
            });
        });
        $('#requested-email').keypress(function(event) {
            if (event.which === 13) // enter key pressed
            {
                $('#load-student-submissions-button').click();
            }
        });
    });
}

function setup_collapsibles(selector)
{
    selector.on('show.bs.collapse', function() {
        var url = $('a', this).attr('href');
        var context = $('.panel-body', this);
        load_submission(url, context);
    });
}

function load_submission(url, context)
{
    $.get(url).done(function(data, status) {
        // console.log(data);
        // console.log(context);
        render_and_fix_links('view-submission', data, context);
        var status = data.data.attributes.status;
        if (status === 'being_graded' || status === 'received' ||
            status === 'queued')
        {
            console.log('will try again a few seconds');
            setTimeout(function() {load_submission(url, context);}, 5000);
        }
    });
}

function on_submit_success(event, response, group_id)
{
    console.log(response);
    var json = response.result;
    console.log('doneeee');

    $('#upload-progress').empty();

    var node_id = "submission-" + String(json.data.id) + "-" + String(group_id)

    var html = (
        "<div class='panel-heading'>"
    +       "<h4 class='panel-title'>"
    +           "<a data-toggle='collapse' class='collapsible-link' href='#" + node_id + "'>"
    +               new Date(json.data.attributes.timestamp).toLocaleString()
    +           "</a>"
    +       "</h4>"
    +   "</div>"
    +   "<div id='" + node_id + "' class='panel-collapse collapse'>"
    +       "<a href='" + json.data.links.self + "' style='display:none'></a>"
    +       "<div class='panel-body'></div>"
    +   "</div>")

    console.log(html);

    $('#submission-list .panel').prepend(html);
    setup_collapsibles($('#' + node_id));

    $('#' + node_id).collapse();
}

function submit_widgit_init()
{

}

function view_own_submissions_widget_init()
{

}

function view_student_submissions_widget_init()
{

}

function get_submission_group_url(project_id, username)
{
    return "/submission-groups/submission-group/?" + $.param(
        {'project_id': project_id,
         'username': username});
}

