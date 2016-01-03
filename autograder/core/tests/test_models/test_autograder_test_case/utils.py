import os
import uuid

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from autograder.core.models import (
    Project, Semester, Course,
    AutograderTestCaseFactory, AutograderTestCaseBase)

from autograder.security.autograder_sandbox import AutograderSandbox


class SharedSetUpTearDownForRunTestsWithCompilation(object):
    @classmethod
    def setUpClass(class_):
        name = 'unit-test-sandbox-{}'.format(uuid.uuid4().hex)

        class_.sandbox = AutograderSandbox(name=name)  # , linux_user_id=2001)
        class_.sandbox.start()

    @classmethod
    def tearDownClass(class_):
        class_.sandbox.stop()

    def setUp(self):
        super().setUp()

        self.original_dir = os.getcwd()
        self.new_dir = os.path.join(settings.MEDIA_ROOT, 'working_dir')
        os.mkdir(self.new_dir)
        os.chdir(self.new_dir)

        self.course = Course.objects.validate_and_create(name='eecs280')
        self.semester = Semester.objects.validate_and_create(
            name='f15', course=self.course)

        self.student_filename = 'student_file.cpp'
        self.project = Project.objects.validate_and_create(
            name='my_project', semester=self.semester)

        self.cpp_filename = 'main.cpp'
        self.executable_name = 'program.exe'

        # We'll be writing the file manually for these tests, so the
        # "real" file in the project directory doesn't really matter.
        self.project.add_project_file(
            SimpleUploadedFile(self.cpp_filename, b''))

        self.test_case_starter = AutograderTestCaseFactory.validate_and_create(
            self.get_ag_test_type_str_for_factory(),
            name='test1', project=self.project,
            compiler='g++',
            compiler_flags=['-Wall', '-pedantic'],
            test_resource_files=[self.cpp_filename],
            project_files_to_compile_together=[self.cpp_filename],
            # student_files_to_compile_together=[self.student_filename],
            executable_name=self.executable_name
        )

        # Reload the test case to make sure that the polymorphism is
        # set up correctly.
        self.test_case_starter = AutograderTestCaseBase.objects.get(
            pk=self.test_case_starter.pk)
        print('************', type(self.test_case_starter), '**************')

    def tearDown(self):
        super().tearDown()

        os.chdir(self.original_dir)

        self.sandbox.clear_working_dir()
        print('verifying working dir was cleared')
        ls_result = self.sandbox.run_cmd_with_redirected_io(['ls'])
        self.assertEqual(ls_result.stdout, '')

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
