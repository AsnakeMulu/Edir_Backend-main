import json
from django.forms.models import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile
from django.db.models import Model


def model_to_json(instance, exclude=None):
    data = model_to_dict(instance, exclude=exclude or [])

    for field in instance._meta.fields:
        value = getattr(instance, field.name, None)

        # Handle File/Image fields
        if isinstance(value, FieldFile):
            if value and value.name:
                try:
                    data[field.name] = value.url
                except Exception:
                    data[field.name] = value.name
            else:
                data[field.name] = None

        # Handle ForeignKey / Model instances
        elif isinstance(value, Model):
            data[field.name] = value.pk

        # Handle datetime safely
        else:
            data[field.name] = value

    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))