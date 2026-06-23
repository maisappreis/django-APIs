from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .emails import notify_contact_safely
from .serializers import ContactMessageSerializer


class ContactAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact_message = serializer.save(source="axis")
        notify_contact_safely(contact_message)

        return Response(
            {
                "detail": "Mensagem recebida com sucesso."
            },
            status=status.HTTP_201_CREATED,
        )
