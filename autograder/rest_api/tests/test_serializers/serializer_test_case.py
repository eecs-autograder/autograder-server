from autograder.utils.testing import UnitTestBase


class SerializerTestCase(UnitTestBase):
    def do_basic_serialize_test(self, ag_model_instance, serializer_class):
        serializer = serializer_class(ag_model_instance)
        self.assertDictContentsEqual(ag_model_instance.to_dict(), serializer.data)
        return serializer.data
