from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import process_chat_message
from core.exceptions import ValidationError


class AssistantChatView(APIView):
    def post(self, request):
        data = request.data
        if not isinstance(data, dict):
            raise ValidationError("Request body must be a JSON object.")

        session_id = data.get("session_id")
        if not session_id or not str(session_id).strip():
            raise ValidationError("Field 'session_id' is required.")

        dealer_id = data.get("dealer_id")
        if dealer_id is None:
            raise ValidationError("Field 'dealer_id' is required.")
        try:
            dealer_id = int(dealer_id)
        except (ValueError, TypeError):
            raise ValidationError("Field 'dealer_id' must be an integer.")

        message = data.get("message")
        if message is None or not str(message).strip():
            raise ValidationError("Field 'message' is required.")

        result = process_chat_message(
            session_id=str(session_id).strip(),
            dealer_id=dealer_id,
            message=str(message).strip(),
        )

        return Response(result, status=status.HTTP_200_OK)
