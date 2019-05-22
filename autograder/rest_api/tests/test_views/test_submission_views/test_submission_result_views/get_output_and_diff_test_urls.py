from django.http import QueryDict
from django.urls import reverse

import autograder.core.models as ag_models


def get_output_and_diff_test_urls(submission: ag_models.Submission,
                                  cmd_result: ag_models.AGTestCommandResult,
                                  fdbk_category: ag_models.FeedbackCategory):
    """
    Returns a list of urls that can be used to request stdout,
    stderr, stdout diff, and stderr diff for the specified
    AGTestCommandResult with the given feedback category.
    """
    result = []
    for field_name, url_lookup in _OUTPUT_AND_DIFF_FIELDS_TO_URL_LOOKUPS.items():
        query_params = QueryDict(mutable=True)
        query_params.update({
            'feedback_category': fdbk_category.value
        })
        url = (reverse(url_lookup,
                       kwargs={'pk': submission.pk, 'result_pk': cmd_result.pk})
               + '?' + query_params.urlencode())
        result.append((url, field_name))

    return result


_OUTPUT_AND_DIFF_FIELDS_TO_URL_LOOKUPS = {
    'stdout': 'ag-test-cmd-result-stdout',
    'stderr': 'ag-test-cmd-result-stderr',
    'stdout_diff': 'ag-test-cmd-result-stdout-diff',
    'stderr_diff': 'ag-test-cmd-result-stderr-diff',
}
