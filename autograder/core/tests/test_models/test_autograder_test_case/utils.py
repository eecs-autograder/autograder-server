import os

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

# from autograder.core.models import (
#     Project, Semester, Course,
#     AutograderTestCaseFactory, AutograderTestCaseBase)

import autograder.core.models as ag_models

from autograder.security.autograder_sandbox import AutograderSandbox

import autograder.core.tests.dummy_object_utils as obj_ut


class SharedSetUpTearDownForRunTestsWithCompilation(object):
    def setUp(self):
        super().setUp()

        self.original_dir = os.getcwd()
        self.new_dir = os.path.join(settings.MEDIA_ROOT, 'working_dir')
        os.mkdir(self.new_dir)
        os.chdir(self.new_dir)

        self.student_filename = 'student_file.cpp'
        self.project = obj_ut.build_project()
        ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='student_file.cpp',

        )

        # We'll be writing the file manually for these tests, so the
        # "real" file in the project directory doesn't really matter.
        ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile('main.cpp', b''))

        self.test_case_starter = ag_models.AutograderTestCaseFactory.validate_and_create(
            self.get_ag_test_type_str_for_factory(),
            name='test1', project=self.project,
            compiler='g++',
            compiler_flags=['-Wall', '-pedantic'],
            # test_resource_files=[self.cpp_filename],
            project_files_to_compile_together=[self.cpp_filename],
            # student_files_to_compile_together=[self.student_filename],
        )

        ag_models.


        # Reload the test case to make sure that the polymorphism is
        # set up correctly.
        self.test_case_starter.refresh_from_db()
        print('************', type(self.test_case_starter), '**************')

        self.sandbox = AutograderSandbox()
        self.sandbox.__enter__()

    def tearDown(self):
        super().tearDown()

        self.sandbox.__exit__()
        os.chdir(self.original_dir)

    def get_ag_test_type_str_for_factory(self):
        raise NotImplementedError(
            "get_ag_test_type_str_for_factory must "
            "be overridden in derived test fixtures")

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class CppProgramStrs(object):
    PRINT_TO_STDOUT_TEMPLATE = """#include <iostream>

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
