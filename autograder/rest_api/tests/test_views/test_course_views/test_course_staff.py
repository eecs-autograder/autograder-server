import autograder.core.tests.dummy_object_utils as obj_ut


class _StaffSetUp:
    def setUp(self):
        super().setUp()

        self.course = obj_ut.build_course()

        self.admin = obj_ut.create_dummy_user()
        self.course.administrators.add(self.admin)

        self.staff = obj_ut.create_dummy_user()
        self.course.staff.add(self.staff)

        self.enrolled = obj_ut.create_dummy_user()
        self.course.enrolled_students.add(self.enrolled)

        self.nobody = obj_ut.create_dummy_user()


class ListStaffTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        _common_setup(self)

        self.staff_names = list(sorted(set(
            itertools.chain(
                (user.username for user in self.staff),
                (self.admin.username,)
            )
        )))

    def test_course_admin_list_staff(self):
        expected_content = {
            'staff': self.staff_names
        }

        client = MockClient(self.admin)
        response = client.get(self.staff_url)
        self.assertEqual(200, response.status_code)
        actual_content = json_load_bytes(response.content)
        actual_content['staff'].sort()
        self.assertEqual(expected_content, actual_content)

    def test_other_list_staff_permission_denied(self):
        for user in self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.get(self.staff_url)

            self.assertEqual(403, response.status_code)

    # -------------------------------------------------------------------------

class AddStaffTestCase(TemporaryFilesystemTestCase):
    def test_course_admin_add_staff(self):
        new_staff_names = ['staffy1', 'staffy2']
        self.staff_names += new_staff_names
        self.staff_names.sort()

        client = MockClient(self.admin)
        response = client.post(self.staff_url, {'staff': new_staff_names})
        self.assertEqual(201, response.status_code)

        expected_content = {
            'staff': self.staff_names
        }

        actual_content = json_load_bytes(response.content)
        actual_content['staff'].sort()
        self.assertEqual(expected_content, actual_content)

        self.assertCountEqual(
            self.staff_names, self.semester.semester_staff_names)

    def test_other_add_staff_permission_denied(self):
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.post(
                self.staff_url, {'staff': ['spam', 'steve']})

            self.assertEqual(403, response.status_code)

            self.assertCountEqual(
                self.staff_names, self.semester.semester_staff_names)

    # -------------------------------------------------------------------------

class RemoveStaffTestCase(_StaffSetUp, TemporaryFilesystemTestCase):
    def test_course_admin_remove_staff(self):
        client = MockClient(self.admin)
        to_remove = copy.copy(self.staff_names)
        to_remove.remove(self.admin.username)
        remaining = [self.admin.username]

        response = client.delete(self.staff_url, {'staff': to_remove})

        self.assertEqual(200, response.status_code)

        expected_content = {
            'staff': remaining
        }

        actual_content = json_load_bytes(response.content)
        actual_content['staff'].sort()
        self.assertEqual(expected_content, actual_content)

        self.assertCountEqual(
            remaining, self.semester.semester_staff_names)

    def test_other_remove_staff_permission_denied(self):
        for user in self.staff[0], self.enrolled[0], self.nobody:
            client = MockClient(user)
            response = client.delete(
                self.staff_url,
                {'staff': [user.username for user in self.staff]})
            self.assertEqual(403, response.status_code)

            self.assertCountEqual(
                self.staff_names, self.semester.semester_staff_names)
