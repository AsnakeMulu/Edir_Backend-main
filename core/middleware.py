import json
import time
import traceback
import logging

error_logger = logging.getLogger("error_logger")


class ErrorLoggingMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        start_time = time.time()

        try:
            response = self.get_response(request)

            response_time = round(
                (time.time() - start_time) * 1000,
                2
            )

            if response.status_code >= 400:

                error_logger.error(
                    json.dumps(
                        {
                            "url": request.path,
                            "method": request.method,
                            "user_id": (
                                request.user.id
                                if request.user.is_authenticated
                                else None
                            ),
                            "status_code": response.status_code,
                            "response_time_ms": response_time,
                        },
                        default=str,
                    )
                )

            return response

        except Exception as e:

            response_time = round(
                (time.time() - start_time) * 1000,
                2
            )

            error_logger.error(
                json.dumps(
                    {
                        "url": request.path,
                        "method": request.method,
                        "user_id": (
                            request.user.id
                            if request.user.is_authenticated
                            else None
                        ),
                        "status_code": 500,
                        "response_time_ms": response_time,
                        "error": str(e),
                        "traceback": traceback.format_exc(),
                    },
                    default=str,
                )
            )

            raise