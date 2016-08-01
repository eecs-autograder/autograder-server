import autograder.core.models as ag_models
import autograder.rest_api.serializers as ag_serializers

from autograder.utils.testing import UnitTestBase
import autograder.rest_api.tests.test_views.common_generic_data as test_data
import autograder.rest_api.tests.test_views.common_test_impls as test_impls


class _AGTestsSetUp(test_data.Client, test_data.Project):
    pass


class ListAGTestsTestCase(_AGTestsSetUp,
                          test_impls.ListObjectsTest,
                          test_impls.PermissionDeniedGetTest,
                          UnitTestBase):
    def test_admin_list_ag_tests(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.admin,
                self.get_ag_tests_url(project), self.build_ag_tests(project))

    def test_staff_list_ag_tests(self):
        for project in self.all_projects:
            self.do_list_objects_test(
                self.client, self.staff,
                self.get_ag_tests_url(project), self.build_ag_tests(project))

    def test_enrolled_list_ag_tests(self):
        for project in self.all_projects:
            self.build_ag_tests(project)
            self.do_permission_denied_get_test(
                self.client, self.enrolled, self.get_ag_tests_url(project))

    def test_other_list_ag_tests(self):
        for project in self.all_projects:
            self.build_ag_tests(project)
            self.do_permission_denied_get_test(
                self.client, self.nobody, self.get_ag_tests_url(project))

    def build_ag_tests(self, project):
        compiled_and_run = ag_models.AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case', name='compilyrunny', project=project,
            compiler='g++')
        compiled_only = ag_models.AutograderTestCaseFactory.validate_and_create(
            'compilation_only_test_case', name='compily', project=project,
            compiler='g++')
        interpreted = ag_models.AutograderTestCaseFactory.validate_and_create(
            'interpreted_test_case', name='interprety', project=project,
            interpreter='python', entry_point_filename='spam')

        return ag_serializers.AGTestCaseSerializer(
            [compiled_and_run, compiled_only, interpreted], many=True).data


class CreateAGTestTestCase(_AGTestsSetUp,
                           test_impls.CreateObjectTest,
                           test_impls.CreateObjectInvalidArgsTest,
                           test_impls.PermissionDeniedCreateTest,
                           UnitTestBase):
    def setUp(self):
        super().setUp()
        self.url = self.get_ag_tests_url(self.project)

    def test_admin_create_interpreted_ag_test(self):
        self.do_create_object_test(
            self.project.autograder_test_cases,
            self.client, self.admin, self.url, self.valid_interpreted_args)

    def test_admin_create_compiled_ag_test(self):
        self.do_create_object_test(
            self.project.autograder_test_cases,
            self.client, self.admin, self.url, self.valid_compiled_args)

    def test_admin_create_ag_test_invalid_type(self):
        args = {
            'type_str': 'not_a_type',
            'name': 'waluigi',
            'compiler': 'g++',
            'executable_name': 'spammy'
        }
        response = self.do_invalid_create_object_test(
            self.project.autograder_test_cases,
            self.client, self.admin, self.url, args)

        self.assertIn('type_str', response.data)

    def test_admin_create_ag_test_invalid_args(self):
        args = {
            'type_str': 'interpreted_test_case',
            'name': 'waluigi',
            'compiler': 'not_a_compiler',
            'executable_name': 'spammy'
        }
        response = self.do_invalid_create_object_test(
            self.project.autograder_test_cases,
            self.client, self.admin, self.url, args)

        self.assertIn('compiler', response.data)

    def other_create_ag_test_permission_denied(self):
        for user in self.staff, self.enrolled, self.nobody:
            self.do_permission_denied_create_test(
                self.project.autograder_test_cases,
                self.client, user, self.url, self.valid_compiled_args)

    @property
    def valid_compiled_args(self):
        return {
            'type_str': 'compiled_and_run_test_case',
            'name': 'waluigi',
            'compiler': 'g++',
            'executable_name': 'spammy'
        }

    @property
    def valid_interpreted_args(self):
        return {
            'type_str': 'interpreted_test_case',
            'name': 'waluigi',
            'interpreter': 'python',
            'entry_point_filename': 'spammy'
        }
