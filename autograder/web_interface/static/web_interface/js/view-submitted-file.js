function load_submitted_file_view(resource_url)
{
	var loaded = $.Deferred();
	$.when(
		$.get(resource_url),
		lazy_get_template('view-submitted-file')
	).done(function(file_json, template) {
		// console.log(file_json);
        var rendered = template.render(file_json);
        // console.log(rendered);
        $('#main-area').html(rendered);

        loaded.resolve();
    }).fail(function(error_message, data) {
        loaded.reject(error_message, data.statusText);
    });

    return loaded.promise();
}
