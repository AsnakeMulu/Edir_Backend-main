import json
import time
import traceback
import logging

error_logger = logging.getLogger("error_logger")


class ErrorLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def get_request_data(self, request):
        """
        Safely get request data without causing RawPostDataException.
        """

        # DRF Request
        if hasattr(request, "data"):
            try:
                return request.data
            except Exception:
                pass

        # Form data
        try:
            if request.POST:
                return request.POST.dict()
        except Exception:
            pass

        # Query parameters
        try:
            if request.GET:
                return request.GET.dict()
        except Exception:
            pass

        return None

    def get_response_data(self, response):
        """
        Safely extract response body.
        """
        try:
            if hasattr(response, "data"):
                return response.data

            if hasattr(response, "content"):
                content = response.content.decode("utf-8")

                try:
                    return json.loads(content)
                except Exception:
                    return content

        except Exception:
            pass

        return None

    def get_user_id(self, request):
        try:
            if (
                hasattr(request, "user")
                and request.user.is_authenticated
            ):
                return request.user.id
        except Exception:
            pass

        return None

    def log_error(
        self,
        request,
        response=None,
        exception=None,
        response_time=None,
    ):
        payload = {
            "url": request.path,
            "method": request.method,
            "query_params": dict(request.GET),
            "request": self.get_request_data(request),
            "response": self.get_response_data(response)
            if response
            else None,
            "user_id": self.get_user_id(request),
            "status_code": (
                response.status_code
                if response
                else 500
            ),
            "response_time_ms": response_time,
        }

        if exception:
            payload.update(
                {
                    "error_type": type(exception).__name__,
                    "error": str(exception),
                    "traceback": traceback.format_exc(),
                }
            )

        error_logger.error(
            json.dumps(payload, default=str)
        )

    def __call__(self, request):
        start_time = time.time()

        try:
            response = self.get_response(request)

            response_time = round(
                (time.time() - start_time) * 1000,
                2,
            )

            if response.status_code >= 400:
                self.log_error(
                    request=request,
                    response=response,
                    response_time=response_time,
                )

            return response

        except Exception as e:
            response_time = round(
                (time.time() - start_time) * 1000,
                2,
            )

            self.log_error(
                request=request,
                exception=e,
                response_time=response_time,
            )

            raise