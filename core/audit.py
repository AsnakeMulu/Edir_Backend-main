import json
from django.forms.models import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile


def model_to_json(instance, exclude=None):
    data = model_to_dict(instance, exclude=exclude or [])

    for field in instance._meta.fields:
        value = getattr(instance, field.name, None)

        # ✅ handle ImageField/FileField safely
        if isinstance(value, FieldFile):
            if value and value.name:
                try:
                    data[field.name] = value.url
                except Exception:
                    data[field.name] = value.name
            else:
                data[field.name] = None
    return json.loads(json.dumps(data, cls=DjangoJSONEncoder))
