import os
import tempfile
import math
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from stl import mesh


class EstimateView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]

    """
    Estimates STL file dimensions to determine 3D printing prices.

    To test:

    curl.exe -X POST http://127.0.0.1:8000/api/print3d/estimate/ `
    -F "file=@C:/Users/maisa/Documents/Apps/django-APIs/print3d/3d_files/Dog_support.stl" `
    -F "altura_cm=3"
    """

    def arredondar_preco(self, valor):
        inteiro = math.floor(valor)
        decimal = valor - inteiro

        if decimal <= 0.1:
            return float(inteiro)
        elif decimal <= 0.6:
            return float(inteiro + 0.5)
        else:
            return float(inteiro + 1.0)

    def post(self, request, *args, **kwargs):
        stl_file = request.FILES.get("file")
        altura_cm = request.data.get("altura_cm")

        if not stl_file:
            return Response({"error": "Arquivo STL é obrigatório"}, status=400)

        # Se a altura foi informada, tenta converter; caso contrário, define como None
        try:
            altura_cm = float(altura_cm) if altura_cm not in [None, "", "0"] else None
        except ValueError:
            altura_cm = None

        # Salva o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".stl") as tmp:
            for chunk in stl_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            modelo = mesh.Mesh.from_file(tmp_path)

            # Bounding box original (em mm)
            min_x, max_x = modelo.x.min(), modelo.x.max()
            min_y, max_y = modelo.y.min(), modelo.y.max()
            min_z, max_z = modelo.z.min(), modelo.z.max()

            largura_atual_mm = max_x - min_x
            comprimento_atual_mm = max_y - min_y
            altura_atual_mm = max_z - min_z

            # Se altura não foi fornecida, usar escala 1 (modelo original)
            if altura_cm:
                altura_desejada_mm = altura_cm * 10  # cm → mm
                fator_escala = altura_desejada_mm / altura_atual_mm
            else:
                altura_desejada_mm = altura_atual_mm
                fator_escala = 1.0

            # Volume original e ajustado
            volume_mm3, _, _ = modelo.get_mass_properties()
            volume_escalado_mm3 = volume_mm3 * (fator_escala ** 3)

            # Dimensões ajustadas
            largura_final_mm = largura_atual_mm * fator_escala
            comprimento_final_mm = comprimento_atual_mm * fator_escala
            altura_final_mm = altura_desejada_mm  # já ajustada

            # Peso (PLA 1.24 g/cm³)
            densidade = 1.24  # g/cm³
            volume_cm3 = volume_escalado_mm3 / 1000  # mm³ → cm³
            peso_g = volume_cm3 * densidade  # g

            # Estimativa de preço (R$1.50 por g)
            preco = peso_g * 1.5
            preco_rounded = self.arredondar_preco(preco)

            return Response({
                "altura_desejada_cm": round(altura_desejada_mm / 10, 2),
                "fator_escala": round(fator_escala, 3),
                "dimensoes_mm": {
                    "largura": round(largura_final_mm, 2),
                    "comprimento": round(comprimento_final_mm, 2),
                    "altura": round(altura_final_mm, 2)
                },
                "volume_mm3": round(volume_escalado_mm3, 2),
                "peso_g": round(peso_g, 2),
                "preco_estimado": preco_rounded
            })

        finally:
            os.remove(tmp_path)

