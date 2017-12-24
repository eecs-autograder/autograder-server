from django.conf.urls import url, include

from rest_framework_nested import routers

from autograder.rest_api import views
import autograder.handgrading.views as handgrading_views


user_router = routers.SimpleRouter()
user_router.register(r'users', views.UserViewSet, base_name='user')

course_router = routers.SimpleRouter()
course_router.register(r'courses', views.CourseViewSet, base_name='course')

admin_router = routers.NestedSimpleRouter(course_router, r'courses', lookup='course')
admin_router.register(r'admins',
                      views.CourseAdminViewSet,
                      base_name='course-admins')
staff_router = routers.NestedSimpleRouter(course_router, r'courses', lookup='course')
staff_router.register(r'staff',
                      views.CourseStaffViewSet,
                      base_name='course-staff')
enrolled_students_router = routers.NestedSimpleRouter(course_router,
                                                      r'courses',
                                                      lookup='course')
enrolled_students_router.register(r'enrolled_students',
                                  views.CourseEnrolledStudentsViewSet,
                                  base_name='course-enrolled-students')
course_projects_router = routers.NestedSimpleRouter(course_router, r'courses',
                                                    lookup='course')

project_router = routers.SimpleRouter()
project_router.register(r'projects', views.ProjectDetailViewSet, base_name='project')

project_downloads_router = routers.SimpleRouter()
project_downloads_router.register(r'download_tasks', views.DownloadTaskDetailViewSet,
                                  base_name='download_tasks')

expected_patterns_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
expected_patterns_router.register(
    r'expected_patterns', views.ExpectedStudentFilePatternsViewSet,
    base_name='project-expected-patterns')

uploaded_files_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
uploaded_files_router.register(
    r'uploaded_files', views.UploadedFilesViewSet,
    base_name='project-uploaded-files')

invitations_router = routers.NestedSimpleRouter(
    project_router, r'projects', lookup='project')
invitations_router.register(
    r'group_invitations', views.GroupInvitationsViewSet,
    base_name='project-group-invitations')

expected_pattern_router = routers.SimpleRouter()
expected_pattern_router.register(r'expected_patterns',
                                 views.ExpectedStudentFilePatternDetailViewSet,
                                 base_name='expected-pattern')

uploaded_file_router = routers.SimpleRouter()
uploaded_file_router.register(r'uploaded_files',
                              views.UploadedFileDetailViewSet,
                              base_name='uploaded-file')

group_invitation_router = routers.SimpleRouter()
group_invitation_router.register(r'group_invitations',
                                 views.GroupInvitationDetailViewSet,
                                 base_name='group-invitation')


group_router = routers.SimpleRouter()
group_router.register(r'groups', views.GroupDetailViewSet, base_name='group')

group_submissions_router = routers.NestedSimpleRouter(group_router, r'groups',
                                                      lookup='group')
group_submissions_router.register(r'submissions',
                                  views.SubmissionsViewSet,
                                  base_name='group-submissions')


submission_router = routers.SimpleRouter()
submission_router.register(r'submissions', views.SubmissionDetailViewSet,
                           base_name='submission')


ag_test_suite_detail_router = routers.SimpleRouter()
ag_test_suite_detail_router.register(r'ag_test_suites', views.AGTestSuiteDetailViewSet,
                                     base_name='ag-test-suite')

ag_test_case_detail_router = routers.SimpleRouter()
ag_test_case_detail_router.register(r'ag_test_cases', views.AGTestCaseDetailViewSet,
                                    base_name='ag-test-case')

ag_test_command_detail_router = routers.SimpleRouter()
ag_test_command_detail_router.register(r'ag_test_commands', views.AGTestCommandDetailViewSet,
                                       base_name='ag-test-command')

student_test_suite_detail_router = routers.SimpleRouter()
student_test_suite_detail_router.register(r'student_test_suites',
                                          views.StudentTestSuiteDetailViewSet,
                                          base_name='student-test-suite')

rerun_submissions_task_detail_router = routers.SimpleRouter()
rerun_submissions_task_detail_router.register(r'rerun_submissions_tasks',
                                              views.RerunSubmissionsTaskDetailVewSet,
                                              base_name='rerun-submissions-task')

annotation_detail_router = routers.SimpleRouter()
annotation_detail_router.register(r'annotations',
                                  handgrading_views.AnnotationDetailViewSet,
                                  base_name='annotation')

applied_annotation_detail_router = routers.SimpleRouter()
applied_annotation_detail_router.register(r'applied_annotations',
                                          handgrading_views.AppliedAnnotationDetailViewSet,
                                          base_name='applied-annotation')

comment_detail_router = routers.SimpleRouter()
comment_detail_router.register(r'comments',
                               handgrading_views.CommentDetailViewSet,
                               base_name='comment')

criterion_result_detail_router = routers.SimpleRouter()
criterion_result_detail_router.register(r'criterion_results',
                                        handgrading_views.CriterionResultDetailViewSet,
                                        base_name='criterion-result')

criterion_detail_router = routers.SimpleRouter()
criterion_detail_router.register(r'criteria',
                                 handgrading_views.CriterionDetailViewSet,
                                 base_name='criterion')

handgrading_rubric_detail_router = routers.SimpleRouter()
handgrading_rubric_detail_router.register(r'handgrading_rubrics',
                                          handgrading_views.HandgradingRubricDetailViewSet,
                                          base_name='handgrading-rubric')

urlpatterns = [
    url(r'^oauth2callback/$', views.oauth2_callback, name='oauth2callback'),

    url(r'', include(user_router.urls)),

    url(r'', include(course_router.urls)),
    url(r'', include(admin_router.urls)),
    url(r'', include(staff_router.urls)),
    url(r'', include(enrolled_students_router.urls)),
    url(r'', include(course_projects_router.urls)),

    url(r'', include(project_router.urls)),
    url(r'', include(project_downloads_router.urls)),
    url(r'', include(expected_patterns_router.urls)),
    url(r'', include(uploaded_files_router.urls)),
    url(r'', include(invitations_router.urls)),

    url(r'', include(expected_pattern_router.urls)),
    url(r'', include(uploaded_file_router.urls)),
    url(r'', include(group_invitation_router.urls)),

    url(r'', include(group_router.urls)),
    url(r'', include(group_submissions_router.urls)),

    url(r'', include(submission_router.urls)),

    url(r'^courses/(?P<pk>[0-9]+)/projects/$',
        views.ListCreateProjectView.as_view(), name='project-list-create'),

    url(r'^projects/(?P<project_pk>[0-9]+)/ag_test_suites/$',
        views.AGTestSuiteListCreateView.as_view(), name='ag_test_suites'),
    url(r'^projects/(?P<project_pk>[0-9]+)/ag_test_suites/order/$',
        views.AGTestSuiteOrderView.as_view(), name='ag_test_suite_order'),
    url(r'', include(ag_test_suite_detail_router.urls)),

    url(r'^ag_test_suites/(?P<ag_test_suite_pk>[0-9]+)/ag_test_cases/$',
        views.AGTestCaseListCreateView.as_view(), name='ag_test_cases'),
    url(r'^ag_test_suites/(?P<ag_test_suite_pk>[0-9]+)/ag_test_cases/order/$',
        views.AGTestCaseOrderView.as_view(), name='ag_test_case_order'),
    url(r'', include(ag_test_case_detail_router.urls)),

    url(r'^ag_test_cases/(?P<ag_test_case_pk>[0-9]+)/ag_test_commands/$',
        views.AGTestCommandListCreateView.as_view(), name='ag_test_commands'),
    url(r'^ag_test_cases/(?P<ag_test_case_pk>[0-9]+)/ag_test_commands/order/$',
        views.AGTestCommandOrderView.as_view(), name='ag_test_command_order'),
    url(r'', include(ag_test_command_detail_router.urls)),

    url(r'^projects/(?P<project_pk>[0-9]+)/student_test_suites/$',
        views.StudentTestSuiteListCreateView.as_view(), name='student_test_suites'),
    url(r'^projects/(?P<project_pk>[0-9]+)/student_test_suites/order/$',
        views.StudentTestSuiteOrderView.as_view(), name='student_test_suite_order'),
    url(r'', include(student_test_suite_detail_router.urls)),

    url(r'^projects/(?P<project_pk>[0-9]+)/rerun_submissions_tasks/$',
        views.RerunSubmissionsTaskListCreateView.as_view(), name='rerun_submissions_tasks'),

    url(r'', include(rerun_submissions_task_detail_router.urls)),

    url(r'^handgrading_rubrics/(?P<handgrading_rubric_pk>[0-9]+)/annotations/$',
        handgrading_views.AnnotationListCreateView.as_view(), name='annotations'),
    url(r'', include(annotation_detail_router.urls)),

    url(r'^handgrading_results/(?P<handgrading_result_pk>[0-9]+)/applied_annotations/$',
        handgrading_views.AppliedAnnotationListCreateView.as_view(), name='applied_annotations'),
    url(r'', include(applied_annotation_detail_router.urls)),

    url(r'^handgrading_results/(?P<handgrading_result_pk>[0-9]+)/comments/$',
        handgrading_views.CommentListCreateView.as_view(), name='comments'),
    url(r'', include(comment_detail_router.urls)),

    url(r'^handgrading_results/(?P<handgrading_result_pk>[0-9]+)/criterion_results/$',
        handgrading_views.CriterionResultListCreateView.as_view(), name='criterion_results'),
    url(r'', include(criterion_result_detail_router.urls)),

    url(r'^handgrading_rubrics/(?P<handgrading_rubric_pk>[0-9]+)/criteria/$',
        handgrading_views.CriterionListCreateView.as_view(), name='criteria'),
    url(r'', include(criterion_detail_router.urls)),

    url(r'^projects/(?P<project_pk>[0-9]+)/handgrading_rubric/$',
        handgrading_views.HandgradingRubricRetrieveCreateView.as_view(), name='handgrading_rubric'),
    url(r'', include(handgrading_rubric_detail_router.urls)),

    url(r'^submission_groups/(?P<group_pk>[0-9]+)/handgrading_result/$',
        handgrading_views.HandgradingResultView.as_view(), name='handgrading_result'),

    url(r'^projects/(?P<project_pk>[0-9]+)/submission_groups/$',
        views.GroupsViewSet.as_view(), name='submission_groups'),
    url(r'^projects/(?P<project_pk>[0-9]+)/submission_groups/solo_group/$',
        views.CreateSoloGroupView.as_view(), name='solo_group'),
]
