from autograder.rest_api.views.ag_model_views import AGModelAPIView
import autograder.rest_api.permissions as ag_permissions
import autograder.core.models as ag_models
from autograder.rest_api.views.schema_generation import APITags


class AllUltimateSubmissionResults(AGModelAPIView):
    permission_classes = (ag_permissions.is_admin(),)
    model_manager = ag_models.Project

    api_tags = (APITags.submissions,)


    pass
