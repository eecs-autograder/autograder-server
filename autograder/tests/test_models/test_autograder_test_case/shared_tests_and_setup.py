import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from autograder.models import (
    Project, Semester, Course,
    AutograderTestCaseBase, AutograderTestCaseFactory)


class SharedTestsAndSetupForTestsWithCompilation(object):
    def setUp(self):
        super().setUp()

        course = Course.objects.validate_and_create(name='eecs280')
        semester = Semester.objects.validate_and_create(
            name='f15', course=course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=semester,
            required_student_files=['file1.cpp', 'file2.cpp'],
            expected_student_file_patterns=[
                Project.FilePatternTuple('test_*.cpp', 1, 2)])

        self.project_files = [
            SimpleUploadedFile('spam.txt', b'hello there!'),
            SimpleUploadedFile('eggs.cpp', b'egg bacon spam and sausage'),
            SimpleUploadedFile('sausage.cpp', b'spam egg sausage and spam')
        ]

        for file_obj in self.project_files:
            self.project.add_project_file(file_obj)

        self.test_name = 'my_test'

        self.compiler = 'g++'
        self.compiler_flags = ['--foo_arg=bar', '-s']

        self.files_to_compile_together = [
            file_obj.name for file_obj in self.project_files
        ]
        self.files_to_compile_together.append('file1.cpp')  # required file
        self.files_to_compile_together.append('test_*.cpp')  # expected pattern

        self.executable_name = "sausage.exe"

        self.compiled_test_kwargs = {
            "compiler": self.compiler,
            "compiler_flags": self.compiler_flags,
            "files_to_compile_together": self.files_to_compile_together,
            "executable_name": self.executable_name,
        }

    # -------------------------------------------------------------------------

    def get_ag_test_type_str_for_factory(self):
        raise NotImplementedError(
            "This method must be overridden in derived test fixtures")

    # -------------------------------------------------------------------------

    def test_exception_on_empty_compiler(self):
        self.compiled_test_kwargs['compiler'] = ''

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_null_compiler(self):
        self.compiled_test_kwargs['compiler'] = None

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_unsupported_compiler(self):
        self.compiled_test_kwargs['compiler'] = 'spamcompiler++'

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler' in cm.exception.message_dict)

    def test_exception_on_invalid_compiler_flag_values(self):
        self.compiled_test_kwargs['compiler_flags'] = [
            '; echo "haxorz!#', '', '       ']

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue('compiler_flags' in cm.exception.message_dict)
        error_list = cm.exception.message_dict['compiler_flags']
        self.assertTrue(error_list[0])
        self.assertTrue(error_list[1])
        self.assertTrue(error_list[2])

    def test_compiler_flag_whitespace_stripped(self):
        self.compiled_test_kwargs['compiler_flags'] = [
            '     spam    ', '   egg  ']

        AutograderTestCaseFactory.validate_and_create(
            self.get_ag_test_type_str_for_factory(),
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        loaded_test = AutograderTestCaseBase.objects.get(
            name=self.test_name, project=self.project)
        self.assertEqual(loaded_test.compiler_flags, ['spam', 'egg'])

    # -------------------------------------------------------------------------

    def test_exception_on_empty_files_to_compile_together(self):
        self.compiled_test_kwargs['files_to_compile_together'] = []

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_null_files_to_compile_together(self):
        self.compiled_test_kwargs['files_to_compile_together'] = None

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

    def test_exception_on_nonexistant_files_to_compile_together(self):
        self.compiled_test_kwargs['files_to_compile_together'].append('')

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

        self.compiled_test_kwargs['files_to_compile_together'][-1] = None

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

        self.compiled_test_kwargs['files_to_compile_together'][-1] = (
            'nonexistant_file.txt')

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                **self.compiled_test_kwargs)

        self.assertTrue(
            'files_to_compile_together' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_validation_error_contains_base_and_derived_error_messages(self):
        self.compiled_test_kwargs['compiler'] = 'unsupported_compiler'

        with self.assertRaises(ValidationError) as cm:
            AutograderTestCaseFactory.validate_and_create(
                self.get_ag_test_type_str_for_factory(),
                name=self.test_name, project=self.project,
                time_limit='spam',
                **self.compiled_test_kwargs)

        self.assertTrue('time_limit' in cm.exception.message_dict)
        self.assertTrue('compiler' in cm.exception.message_dict)

    # -------------------------------------------------------------------------

    def test_test_checks_compilation(self):
        test = AutograderTestCaseFactory.validate_and_create(
            self.get_ag_test_type_str_for_factory(),
            name=self.test_name, project=self.project,
            **self.compiled_test_kwargs)

        self.assertTrue(test.test_checks_compilation())

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class SharedSetUpTearDownForRunTestsWithCompilation(object):
    def setUp(self):
        super().setUp()

        self.original_dir = os.getcwd()
        self.new_dir = os.path.join(settings.MEDIA_ROOT, 'working_dir')
        os.mkdir(self.new_dir)
        os.chdir(self.new_dir)

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester)

        self.cpp_filename = 'main.cpp'
        self.executable_name = 'program.exe'

        # We'll be writing the file manually for these tests, so the
        # "real" file in the project directory doesn't really matter.
        self.project.add_project_file(
            SimpleUploadedFile(self.cpp_filename, b''))

        self.test_case_starter = AutograderTestCaseFactory.new_instance(
            self.get_ag_test_type_str_for_factory(),
            name='test1', project=self.project,
            compiler='g++',
            compiler_flags=['-Wall', '-pedantic'],
            files_to_compile_together=[self.cpp_filename],
            executable_name=self.executable_name
        )

    def tearDown(self):
        super().tearDown()

        os.chdir(self.original_dir)

    def get_ag_test_type_str_for_factory(self):
        raise NotImplementedError(
            "This method must be overridden in derived test fixtures")

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class CppProgramStrs(object):
    PRINT_TO_STDOUT_TEMPLATE = r"""#include <iostream>

using namespace std;

int main()
{{
    cout << "{}" << flush;
    return 0;
}}
"""

    PRINT_TO_STDERR_TEMPLATE = """#include <iostream>

using namespace std;

int main()
{{
    cerr << "{}" << flush;
    return 0;
}}
"""

    RETURN_ONLY_TEMPLATE = """
int main()
{{
    return {};
}}
"""

    PRINT_CMD_ARGS = """#include <iostream>

using namespace std;

int main(int argc, char** argv)
{{
    for (int i = 1; i < argc - 1; ++i)
    {{
        cout << argv[i] << " ";
    }}
    cout << argv[argc - 1] << flush;

    return 0;
}}
"""

    PRINT_STDIN_CONTENT = """#include <iostream>
#include <string>

using namespace std;

int main()
{{
    string spam;
    while (cin >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    return 0;
}}
"""

    PRINT_FILE_CONTENT = """#include <iostream>
#include <fstream>
#include <string>

using namespace std;

int main()
{{
    string spam;
    ifstream ifs("input.in");
    while (ifs >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    return 0;
}}
"""

    INFINITE_LOOP = """int main()
{{
    while (true);
    return 0;
}}
"""

    MEMORY_LEAK = """int main()
{{
    new int(42);
    return 0;
}}
"""

    COMPILE_ERROR = """int main()
{{
    spameggsausagespam
}}
"""

    DO_EVERYTHING = """#include <iostream>
#include <fstream>
#include <string>

using namespace std;

int main(int argc, char** argv)
{{
    for (int i = 1; i < argc - 1; ++i)
    {{
        cout << argv[i] << " ";
    }}
    cout << argv[argc - 1] << flush;

    string spam;
    ifstream ifs("input.in");
    while (ifs >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    while (cin >> spam)
    {{
        cout << spam << ' ' << flush;
    }}

    cout << "{stdout_str}" << flush;
    cerr << "{stderr_str}" << flush;

    return {return_code};
}}
"""
