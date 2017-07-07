import os
import tempfile
import zipfile

import io
from django.http import FileResponse
from rest_framework import viewsets, mixins, permissions, decorators, response

import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers
from autograder.rest_api import transaction_mixins
import autograder.rest_api.permissions as ag_permissions
import autograder.core.utils as core_ut
from autograder import utils

from .permissions import ProjectPermissions
from ..load_object_mixin import build_load_object_mixin


class ProjectDetailViewSet(build_load_object_mixin(ag_models.Project),  # type: ignore
                           mixins.RetrieveModelMixin,
                           transaction_mixins.TransactionUpdateMixin,
                           viewsets.GenericViewSet):
    serializer_class = ag_serializers.ProjectSerializer
    permission_classes = (permissions.IsAuthenticated, ProjectPermissions)

    @decorators.detail_route()
    def num_queued_submissions(self, *args, **kwargs):
        project = self.get_object()
        num_queued_submissions = ag_models.Submission.objects.filter(
            status=ag_models.Submission.GradingStatus.queued,
            submission_group__project=project).count()

        return response.Response(data=num_queued_submissions)

    @decorators.detail_route(permission_classes=[
        permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def all_submission_files(self, *args, **kwargs):
        include_staff = self.request.query_params.get('include_staff', None) == 'true'

        project = self.get_object()  # type: ag_models.Project
        course = project.course

        groups = project.submission_groups.all()
        groups = filter(lambda group: group.submissions.count(), groups)
        if not include_staff:
            groups = filter(lambda group: not course.is_course_staff(group.members.first()),
                            groups)
        groups = list(groups)
        submissions = ag_models.Submission.objects.filter(submission_group__in=groups)

        archive = io.BytesIO()
        with zipfile.ZipFile(archive, 'w') as z:
            for s in submissions:
                archive_dirname = '_'.join(
                    sorted(s.submission_group.member_names)) + '-' + s.timestamp.isoformat()
                with utils.ChangeDirectory(core_ut.get_submission_dir(s)):
                    for filename in s.submitted_filenames:
                        # print('filename', filename)
                        target_name = os.path.join(
                            '{}_{}'.format(course.name, project.name),
                            archive_dirname, filename)
                        # print('target name', target_name)
                        z.write(filename, arcname=target_name)

        archive.seek(0)
        return FileResponse(archive)

    @decorators.detail_route(permission_classes=[
        permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def ultimate_submission_files(self, *args, **kwargs):
        pass

    @decorators.detail_route(permission_classes=[
        permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def all_submission_scores(self, *args, **kwargs):
        pass

    @decorators.detail_route(permission_classes=[
        permissions.IsAuthenticated, ag_permissions.is_admin(lambda project: project.course)])
    def ultimate_submission_scores(self, *args, **kwargs):
        pass
