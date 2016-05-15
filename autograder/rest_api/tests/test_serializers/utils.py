class SerializerTestCase:
    def do_basic_serialize_test(self, ag_model_instance, serializer_class):
        serializer = serializer_class(ag_model_instance)
        self.assertEqual(ag_model_instance.to_dict(), serializer.data)
