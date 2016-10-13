import autograder.rest_api.serializers as ag_serializers

from .serializer_test_case import SerializerTestCase
import autograder.utils.testing.model_obj_builders as obj_build


_TYPE_STRS_TO_FDBK_METHOD_NAMES = {
    'normal': 'get_normal_feedback',
    'ultimate_submission': 'get_ultimate_submission_feedback',
    'staff_viewer': 'get_staff_viewer_feedback',
    'past_submission_limit': 'get_past_submission_limit_feedback',
    'max': 'get_max_feedback',
}


class AGTestResultSerializerTestCase(SerializerTestCase):
    def test_serialize_with_specified_fdbk_type(self):
        result = obj_build.build_compiled_ag_test_result()
        result.test_case.staff_viewer_fdbk = obj_build.random_fdbk()
        for fdbk_type, fdbk_method_name in _TYPE_STRS_TO_FDBK_METHOD_NAMES.items():
            actual_data = ag_serializers.AGTestResultSerializer(
                result, feedback_type=fdbk_type).data

            self.assertEqual(getattr(result, fdbk_method_name)().to_dict(),
                             actual_data)
