from .models import Notification


def create_notification(
    user,
    title,
    message,
    notification_type="SYSTEM",
    reference_id=None,
):

    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        reference_id=reference_id,
    )

    return notification