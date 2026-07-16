import json
import logging
from django.forms.models import model_to_dict
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import FieldFile
from django.db.models import Model

audit_logger = logging.getLogger("audit_logger")

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

def audit_log(
    action,
    request,
    status,
    request_data=None,
    response_data=None,
    extra_data=None,
):
    # if request_data is None:
    #     request_data = request.data if hasattr(request, "data") else None

    payload = {
        "action": action,
        "user_id": request.user.id,
        "phone_number": getattr(
            request.user,
            "phone_number",
            None,
        ),
        # "method": request.method,
        # "path": request.path,
        # "ip": request.META.get("REMOTE_ADDR"),
        "status": status,
        "request": request_data,
        "response": response_data,
        "extra": extra_data,
    }

    audit_logger.info(
        json.dumps(payload, default=str)
    )