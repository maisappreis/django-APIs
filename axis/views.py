from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import ContactMessageSerializer


class ContactAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(source="axis")

        return Response(
            {
                "detail": "Mensagem recebida com sucesso."
            },
            status=status.HTTP_201_CREATED,
        )
