import copy
import datetime
from typing import List, Optional

from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_composable_permissions.p import P
from rest_framework import decorators, exceptions, mixins, response, status

import autograder.core.models as ag_models
import autograder.rest_api.permissions as ag_permissions
import autograder.utils.testing as test_ut
from autograder.core.submission_feedback import (AGTestPreLoader, StudentTestSuitePreLoader,
                                                 SubmissionResultFeedback)
from autograder.rest_api.schema import (AGDetailViewSchemaGenerator,
                                        AGListCreateViewSchemaGenerator, AGListViewSchemaMixin,
                                        APITags, CustomViewDict, CustomViewSchema, as_content_obj,
                                        as_schema_ref)
from autograder.rest_api.serialize_ultimate_submission_results import \
    get_submission_data_with_results
from autograder.rest_api.size_file_response import SizeFileResponse
from autograder.rest_api.views.ag_model_views import (AGModelAPIView, AGModelDetailView,
                                                      NestedModelView,
                                                      convert_django_validation_error,
                                                      require_query_params)

from .common import make_fdbk_category_param_docs, validate_fdbk_category

can_view_group = (
    P(ag_permissions.IsReadOnly)
    & P(ag_permissions.can_view_project())
    & P(ag_permissions.is_staff_or_group_member())
)


can_submit = (
    ~P(ag_permissions.IsReadOnly)
    & P(ag_permissions.can_view_project())
    & P(ag_permissions.is_group_member())
)


class _ListCreateSubmissionSchema(AGListViewSchemaMixin, CustomViewSchema):
    def __init__(self, data: CustomViewDict):
        super().__init__([APITags.submissions], api_class=ag_models.Submission, data=data)


class ListCreateSubmissionView(NestedModelView):
    schema = _ListCreateSubmissionSchema({
        'POST': {
            'operation_id': 'createSubmission',
            'request': {
                'content': {
                    'multipart/form-data': {
                        'schema': {
                            'properties': {
                                'submitted_files': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'string',
                                        'format': 'binary'
                                    }
                                }
                            }
                        }
                    }
                },
                'description': 'The files being submitted, as multipart/form-data.',
            },
            'responses': {
                '201': {
                    'content': as_content_obj(ag_models.Submission)
                }
            }
        }
    })

    permission_classes = [can_view_group | can_submit]

    model_manager = ag_models.Group.objects.select_related('project__course')
    nested_field_name = 'submissions'
    parent_obj_field_name = 'group'

    def get(self, *args, **kwargs):
        return self.do_list()

    @convert_django_validation_error
    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        # NOTE: The way that submitted_files gets encoded in requests,
        # sending no files (which is valid) will cause the key 'submitted_files'
        # to not show up in the request body. Therefore, we will NOT require
        # the presence of a 'submitted_files' key in the request.
        invalid_fields = []
        for key in request.data:
            if key != 'submitted_files':
                invalid_fields.append(key)

        if invalid_fields:
            raise exceptions.ValidationError({'invalid_fields': invalid_fields})

        timestamp = timezone.now()
        group: ag_models.Group = self.get_object()
        # Keep this mocking hook just after we call get_object()
        test_ut.mocking_hook()

        return self._create_submission_if_allowed(request, group, timestamp)

    def _create_submission_if_allowed(self, request, group: ag_models.Group,
                                      timestamp: datetime.datetime):
        has_active_submission = group.submissions.filter(
            status__in=ag_models.Submission.GradingStatus.active_statuses
        ).exists()
        if has_active_submission:
            raise exceptions.ValidationError(
                {'submission': 'Unable to resubmit while current submission is being processed'})

        # We still track this information for staff submissions even though
        # staff can submit unlimited times with full feedback.
        is_past_daily_limit = False
        if group.project.submission_limit_per_day is not None:
            submission_limit = group.project.submission_limit_per_day
            if group.project.groups_combine_daily_submissions:
                submission_limit *= len(group.member_names)

            is_past_daily_limit = group.num_submits_towards_limit >= submission_limit

        is_bonus_submission = False
        if is_past_daily_limit and group.bonus_submissions_remaining > 0:
            group.bonus_submissions_used += 1
            group.save()
            is_bonus_submission = True
            is_past_daily_limit = False

        # Provided they don't have a submission being processed, staff
        # should always be able to submit.
        if (group.project.course.is_staff(request.user)
                and group.members.filter(pk=request.user.pk).exists()):
            return self._create_submission(
                group, timestamp,
                is_past_daily_limit=is_past_daily_limit,
                is_bonus_submission=is_bonus_submission,
                does_not_count_for=[]
            )

        if group.project.disallow_student_submissions:
            raise exceptions.ValidationError(
                {'submission': 'Submitting has been temporarily disabled for this project'})

        group_deadline = self._get_deadline_for_group(group)
        group_deadline_past = group_deadline is not None and timestamp > group_deadline

        does_not_count_for = []
        if group_deadline_past:
            course = group.project.course
            if course.num_late_days != 0 and group.project.allow_late_days:
                for user in group.members.all():
                    user_deadline = self._get_deadline_for_user(group, user)
                    assert user_deadline >= group_deadline

                    if user_deadline > timestamp:
                        continue

                    remaining = ag_models.LateDaysRemaining.objects.get_or_create(
                        user=user, course=course)[0]
                    late_days_needed = (timestamp - user_deadline).days + 1

                    if remaining.late_days_remaining >= late_days_needed:
                        remaining.late_days_used += late_days_needed
                        remaining.save()
                        group.late_days_used.setdefault(user.username, 0)
                        group.late_days_used[user.username] += late_days_needed
                        group.save()
                    else:
                        does_not_count_for.append(user.username)

                if request.user.username in does_not_count_for:
                    raise exceptions.ValidationError(
                        {'submission': 'The closing time for this project has passed, '
                                       'and you are out of late days.'})
            else:
                raise exceptions.ValidationError(
                    {'submission': 'The closing time for this project has passed'})

        if is_past_daily_limit and not group.project.allow_submissions_past_limit:
            raise exceptions.ValidationError(
                {'submission': 'Submissions past the daily limit are '
                               'not allowed for this project'})

        if group.project.total_submission_limit is not None:
            submits_toward_total_limit = group.submissions.filter(
                count_towards_total_limit=True
            ).count()
            # Use >= in case of user error (if they forgot to set the submission
            # limit and some users already used up their submissions.
            if submits_toward_total_limit >= group.project.total_submission_limit:
                raise exceptions.ValidationError(
                    {'submission': 'This project does not allow more than '
                                   f'{group.project.total_submission_limit} submissions'}
                )

        return self._create_submission(group, timestamp,
                                       is_past_daily_limit=is_past_daily_limit,
                                       is_bonus_submission=is_bonus_submission,
                                       does_not_count_for=does_not_count_for)

    def _get_deadline_for_group(self, group: ag_models.Group):
        project = group.project
        if project.closing_time is None:
            return None

        return (group.extended_due_date if group.extended_due_date is not None
                else project.closing_time)

    def _get_deadline_for_user(self, group: ag_models.Group,
                               user: User) -> Optional[datetime.datetime]:
        deadline = self._get_deadline_for_group(group)
        return deadline + datetime.timedelta(days=group.late_days_used.get(user.username, 0))

    def _create_submission(self, group: ag_models.Group,
                           timestamp: datetime.datetime,
                           *, is_past_daily_limit: bool,
                           is_bonus_submission: bool,
                           does_not_count_for: List[str]):
        submission: ag_models.Submission = ag_models.Submission.objects.validate_and_create(
            self.request.data.getlist('submitted_files'),
            group,
            timestamp,
            self.request.user.username
        )

        # Some fields can't be set through Submission.objects.validate_and_create
        # for security reasons. Instead, we set those fields now.
        submission.is_past_daily_limit = is_past_daily_limit
        submission.is_bonus_submission = is_bonus_submission
        submission.does_not_count_for = does_not_count_for
        submission.save()

        return response.Response(data=submission.to_dict(), status=status.HTTP_201_CREATED)


class ListSubmissionsWithResults(AGModelAPIView):
    schema = CustomViewSchema([APITags.submissions], {
        'GET': {
            'operation_id': 'listSubmissionsWithResults',
            'parameters': [{'$ref': '#/components/parameters/feedbackCategory'}],
            'responses': {
                '200': {
                    'content': {
                        'application/json': {
                            'schema': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/SubmissionWithResults'}
                            }
                        }
                    }
                }
            }
        }
    })

    permission_classes = [
        P(ag_permissions.can_view_project()) & P(ag_permissions.is_staff_or_group_member())
    ]

    model_manager = ag_models.Group.objects.select_related('project__course')

    def get(self, *args, **kwargs):
        group = self.get_object()

        user_roles = group.project.course.get_user_roles(self.request.user)
        is_group_member = self.request.user.username in group.member_names
        feedback_category = None

        if 'feedback_category' in self.request.query_params:
            feedback_category = validate_fdbk_category(
                self.request.query_params.get('feedback_category'))
            if not user_roles['is_admin']:
                return response.Response(status=status.HTTP_403_FORBIDDEN,
                                         data='Only admins can override feedback_category')

        submissions_queryset = ag_models.get_submissions_with_results_queryset(
            base_manager=group.submissions)

        ag_test_preloader = AGTestPreLoader(group.project)
        student_test_suite_preloader = StudentTestSuitePreLoader(group.project)

        submissions = []
        for submission in submissions_queryset:
            if feedback_category is not None:
                fdbk_category = feedback_category
            elif user_roles['is_staff']:
                fdbk_category = (ag_models.FeedbackCategory.max if is_group_member
                                 else ag_models.FeedbackCategory.staff_viewer)
            elif submission.is_past_daily_limit:
                fdbk_category = ag_models.FeedbackCategory.past_limit_submission
            else:
                fdbk_category = ag_models.FeedbackCategory.normal

            serialized = get_submission_data_with_results(
                SubmissionResultFeedback(
                    submission,
                    fdbk_category,
                    ag_test_preloader,
                    student_test_suite_preloader
                ),
                full_results=True
            )
            submissions.append(serialized)

        return response.Response(status=status.HTTP_200_OK, data=submissions)


class SubmissionDetailView(AGModelDetailView):
    schema = AGDetailViewSchemaGenerator([APITags.submissions])

    model_manager = ag_models.Submission.objects.select_related('group__project__course')

    permission_classes = [
        P(ag_permissions.is_admin()) | P(ag_permissions.IsReadOnly),
        ag_permissions.can_view_project(),
        ag_permissions.is_staff_or_group_member()
    ]

    def get(self, *args, **kwargs):
        return self.do_get()

    def patch(self, *args, **kwargs):
        return self.do_patch()


class GetSubmittedFileView(AGModelAPIView):
    schema = CustomViewSchema([APITags.submissions], {
        'GET': {
            'operation_id': 'getSubmittedFile',
            'parameters': [
                {
                    'name': 'filename',
                    'in': 'query',
                    'description': 'The name of the file to return.',
                    'required': True,
                    'schema': {'type': 'string'}
                }
            ],
            'responses': {
                '200': {
                    'content': {
                        'application/octet-stream': {
                            'schema': {'type': 'string', 'format': 'binary'}
                        }
                    }
                }
            }
        }
    })

    model_manager = ag_models.Submission.objects.select_related('group__project__course')

    permission_classes = [
        ag_permissions.can_view_project(),
        ag_permissions.is_staff_or_group_member()
    ]

    @method_decorator(require_query_params('filename'))
    @transaction.atomic
    def get(self, request, *args, **kwargs):
        submission = self.get_object()
        filename = request.query_params['filename']
        try:
            return SizeFileResponse(submission.get_file(filename))
        except ObjectDoesNotExist:
            return response.Response('File "{}" not found'.format(filename),
                                     status=status.HTTP_404_NOT_FOUND)


class RemoveSubmissionFromQueueView(AGModelAPIView):
    schema = CustomViewSchema([APITags.submissions], {
        'POST': {
            'operation_id': 'removeSubmissionFromQueue',
            'responses': {
                '200': {
                    'content': as_content_obj(ag_models.Submission)
                }
            }
        }
    })

    permission_classes = [ag_permissions.can_view_project(), ag_permissions.is_group_member()]

    model_manager = ag_models.Submission.objects.select_related('group__project__course')

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        """
        Remove this submission from the grading queue.
        """
        submission: ag_models.Submission = self.get_object()
        removeable_statuses = [ag_models.Submission.GradingStatus.received,
                               ag_models.Submission.GradingStatus.queued]
        if submission.status not in removeable_statuses:
            return response.Response('This submission is not currently queued',
                                     status=status.HTTP_400_BAD_REQUEST)

        refund_bonus_submission = submission.is_bonus_submission
        if refund_bonus_submission:
            ag_models.Group.objects.select_for_update().filter(
                pk=submission.group_id
            ).update(bonus_submissions_used=F('bonus_submissions_used') - 1)

        submission.status = (
            ag_models.Submission.GradingStatus.removed_from_queue)
        submission.is_bonus_submission = False
        submission.save()

        return response.Response(submission.to_dict(), status.HTTP_200_OK)
