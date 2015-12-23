from autograder.core import models


class SerializerBase:
    MODEL_TYPES_TO_JSON_TYPES = {
        models.Course: "course"
    }

    MODEL_TYPES_TO_ATTRIBUTE_NAMES = {
        models.Course: [
            "name"
        ]
    }

    def get_json_object_type_str(self):
        raise NotImplementedError()

    def get_default_attribute_names(self):
        raise NotImplementedError()

    def get_default_relationships_to_include(self):
        raise NotImplementedError()

    def get_default_callable_attributes_to_include(self):
        raise NotImplementedError()


    @classmethod
    def serialize(class_, model_object, attributes_to_include=None,
                  relationships_to_include=None,
                  callable_attributes_to_include=None):
        """
        Parameters:
            model_object -- The object to be serialized. Must be registered
                 in MODEL_TYPES_TO_JSON_TYPES and
                 MODEL_TYPES_TO_ATTRIBUTE_NAMES.

            attributes_to_include -- The names of non-relational data
                attributes to be included in the serialized model_object.
                If this value is None, then ALL attributes registered
                for model_object's type in MODEL_TYPES_TO_ATTRIBUTE_NAMES
                will be included.
                If this value is an empty dictionary, then the "attributes"
                key will not be included in the result.

            relationships_to_include -- A dictionary of relationship names
                mapped to lists of attribute names that should be included in
                a given relationship.
                For example, if this value is {'course': None}, then
                the 'course' relationship will be included in the
                serialized model_object without its own nested "attributes"
                field. If this value is {"course": ["name"]},
                then the 'course' relationship will be included in the
                serialized model and contain the 'name' field in addition
                to the other relevant information.

            callable_attributes_to_include -- A dictionary of names of
                callable attributes of model_object mapped to dictionaries
                of the following form:
                    {
                        // The name to use for this attribute in the
                        // serialized model_object.
                        "attribute_alias": <string>,
                        // positional arguments to pass to the callable
                        "args": [<arg>, ...],
                        // keyword arguments to pass to the callable
                        "kwargs": {<key>: <value>}
                    }
                For each key-value pair in this parameter, an attribute
                named <attribute_alias> with the value from calling
                the callable will be added to the "attributes" field
                of the serialized model_object.


            The names of related fields to be
                included in the serialized model_object.

            relationship_attributes_to_include -- The names of attributes
        """
        result = {
            'type': class_.MODEL_TYPES_TO_JSON_TYPES[type(model_object)],
            'id': model_object.pk,
            'links':
        }

        result.update(class_._get_attributes(attributes_to_include))

    @classmethod
    def _get_attributes(class_, model_object, attribute_names=None):
        if attribute_names is None:
            attribute_names = (
                class_.MODEL_TYPES_TO_ATTRIBUTE_NAMES[type(model_object)])

        if attribute_names == {}:
            return {}

        return {
            'attributes': {
                attr_name: getattr(model_object, attr_name)
                for attr_name in attribute_names
            }
        }




