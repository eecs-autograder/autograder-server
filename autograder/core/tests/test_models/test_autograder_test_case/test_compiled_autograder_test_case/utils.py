from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models

from autograder.security.autograder_sandbox import AutograderSandbox

import autograder.core.tests.dummy_object_utils as obj_ut


class SharedSetUpTearDownForRunTestsWithCompilation(object):
    def setUp(self):
        super().setUp()

        self.group = obj_ut.build_submission_group()
        self.project = self.group.project

        self.main_prog_filename = 'main.cpp'
        self.student_filename = 'student_file.h'

        self.header_file = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern=self.student_filename,
            project=self.project
        )

        # We'll be writing the file manually for these tests, so the
        # "real" file in the project directory doesn't really matter.
        self.main_file = ag_models.UploadedFile.objects.validate_and_create(
            project=self.project,
            file_obj=SimpleUploadedFile(self.main_prog_filename, b'weeeee'))

        self.test_case_starter = ag_models.AutograderTestCaseFactory.validate_and_create(
            self.get_ag_test_type_str_for_factory(),
            name='test1', project=self.project,
            compiler='g++',
            compiler_flags=['-Wall', '-pedantic'],
        )
        self.test_case_starter.project_files_to_compile_together.add(
            self.main_file)
        self.test_case_starter.student_resource_files.add(
            self.header_file)

        self.submission = ag_models.Submission.objects.validate_and_create(
            submission_group=self.group,
            submitted_files=[
                SimpleUploadedFile(self.student_filename, b'')])

        # Reload the test case to make sure that the polymorphism is
        # set up correctly.
        self.test_case_starter.refresh_from_db()
        print('************', type(self.test_case_starter), '**************')

        self.sandbox = AutograderSandbox()
        self.sandbox.__enter__()

    def tearDown(self):
        super().tearDown()

        self.sandbox.__exit__()

    def get_ag_test_type_str_for_factory(self):
        raise NotImplementedError(
            "get_ag_test_type_str_for_factory must "
            "be overridden in derived test fixtures")

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------


class CppProgramStrs:
    PRINT_TO_STDOUT_TEMPLATE = """#include <iostream>
#include "student_file.h"

using namespace std;

int main()
{{
    cout << "{}" << flush;
    return 0;
}}
"""

    PRINT_TO_STDERR_TEMPLATE = """#include <iostream>
#include "student_file.h"

using namespace std;

int main()
{{
    cerr << "{}" << flush;
    return 0;
}}
"""

    RETURN_ONLY_TEMPLATE = """
#include "student_file.h"
int main()
{{
    return {};
}}
"""

    PRINT_CMD_ARGS = """#include <iostream>
#include "student_file.h"

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
#include "student_file.h"
#include <string>

using namespace std;

int main()
{
    string spam;
    while (cin >> spam)
    {
        cout << spam << ' ' << flush;
    }

    return 0;
}
"""

    PRINT_FILE_CONTENT = """#include <iostream>
#include "student_file.h"
#include <fstream>
#include <string>

using namespace std;

int main()
{
    string spam;
    ifstream ifs("input.in");
    while (ifs >> spam)
    {
        cout << spam << ' ' << flush;
    }

    return 0;
}
"""

    INFINITE_LOOP = """int main()
#include "student_file.h"
{{
    while (true);
    return 0;
}}
"""

    MEMORY_LEAK = """int main()
#include "student_file.h"
{{
    new int(42);
    return 0;
}}
"""

    COMPILE_ERROR = """int main()
#include "student_file.h"
{{
    spameggsausagespam
}}
"""

    DO_EVERYTHING = """#include <iostream>
#include "student_file.h"
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
