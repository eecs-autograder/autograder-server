function load_submission_view(url)
{
    var loaded = $.Deferred();
    var submission = null;
    $.get(url).then(function(submission_json){
        submission = submission_json;
        return $.when(
            $.get(submission.urls.submitted_files),
            $.get(submission.urls.autograder_test_case_results),
            $.get(submission.urls.student_test_suite_results),
            lazy_get_template('view-submission'))
    }).done(function(submitted_files_ajax, test_results_ajax,
                     suite_results_ajax, template) {
        var render_data = {
            'submission': submission,
            'submitted_files': submitted_files_ajax[0],
            'test_results': test_results_ajax[0],
            'suite_results': suite_results_ajax[0]
        };
        console.log(render_data);

        var rendered = template.render(render_data);
        $('#main-area').html(rendered);
        $('#test-result-list .collapse').on('show.bs.collapse', _load_result);

        if (submission.status === 'being_graded' || submission.status === 'received' ||
            submission.status === 'queued')
        {
            var old_url = window.location.pathname;
            console.log('will try again a few seconds');
            setTimeout(function() {
                var current_url = window.location.pathname;
                if (current_url === old_url)
                {
                    load_submission_view(url);
                }
            }, 5000);
        }

        _init_remove_button(submission);
        loaded.resolve();
    }).fail(function(data, status) {
        console.log('error loading project');
        loaded.reject("Error loading submission", data.statusText);
    });
    return loaded.promise();
}

function _load_result(event, url, render_location)
{
    console.log('_load_result');

    if (url === undefined)
    {
        // console.log('waluiiiigi');
        // console.log($('a', this)[0]);
        url = $('a', this).attr('href');
    }

    if (render_location === undefined)
    {
        render_location = $('.panel-body', this);
    }

    console.log(url);

    $.when(
        $.get(url),
        lazy_get_template('ag-test-result')
    ).done(function(result_ajax, template) {
        console.log(result_ajax[0]);
        render_location.html(template.render(result_ajax[0]));
    });
}

function _init_remove_button(submission_json)
{
    $('#remove-from-queue-button').click(function(event) {
        event.preventDefault();
        var confirmed = window.confirm("Are you sure you want to remove your submission from the queue?\nClick OK to REMOVE, CANCEL to keep it in the queue");
        if (!confirmed)
        {
            return false;
        }
        _remove_from_queue(submission_json);
    });
}

function _remove_from_queue(submission_json)
{
    console.log(submission_json);
    $.post(submission_json.urls.remove_from_queue).done(function() {
        $('#remove-from-queue-button').hide();
        $('#remove-from-queue-error').hide();
        $('#status-header').text('Status: removed_from_queue');
    }).fail(function(response) {
        console.log(response);
        $('#remove-from-queue-error').text(response);
    });
}

// function _load_submission(event, url, render_location)
// {
//     console.log(url);
//     if (url === undefined)
//     {
//         url = $('a', this).attr('href');
//     }
//     if (render_location === undefined)
//     {
//         render_location = $('.panel-body', this);
//     }

//     $.get(
//         url
//     ).then(function(submission) {
//         console.log(submission);
//         return _render_submission(submission, render_location)
//     }).then(function(submission) {
//         var status = submission.status;
//         if (status === 'being_graded' || status === 'received' ||
//             status === 'queued')
//         {
//             var old_url = window.location.pathname;
//             console.log('will try again a few seconds');
//             setTimeout(function() {
//                 var current_url = window.location.pathname;
//                 if (current_url === old_url)
//                 {
//                     _load_submission(event, url, render_location);
//                 }
//             }, 5000);
//         }
//     });
// }

// function _render_submission(submission, render_location)
// {
//     var finished_rendering = $.Deferred();

//     lazy_get_template('view-submission').done(function(template) {
//         render_location.html(template.render(submission));
//         finished_rendering.resolve(submission);
//     });

//     return finished_rendering.promise();
// }
